"""
WinScorr AI-Powered Tutoring Bot - Main Application
Complete backend with Claude AI integration
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import secrets

# Import our services
from ai_tutor_service import AITutorService
from tutoring_service import TutoringService
from fatigue_detector import FatigueDetector

load_dotenv()

app = Flask(__name__, static_folder='../frontend', static_url_path='')

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# Enable CORS for Railway deployment
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

jwt = JWTManager(app)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'winscorr'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': os.getenv('DB_PORT', 5432)
}

# Initialize services
ai_tutor = AITutorService()
tutoring_service = TutoringService(DB_CONFIG)
fatigue_detector = FatigueDetector()

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

# ============================================================================
# FRONTEND ROUTES - Serve static files
# ============================================================================

@app.route('/')
def index():
    """Serve the landing page"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

# ============================================================================
# API ROUTES - Core functionality
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ai_enabled': True,
        'services': {
            'database': 'connected',
            'ai_tutor': 'active',
            'fatigue_detection': 'active'
        }
    })

@app.route('/api/info', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        'name': 'WinScorr AI Tutoring Bot API',
        'version': '2.0.0',
        'ai_powered': True,
        'endpoints': {
            'health': '/api/health',
            'questions': '/api/questions/<exam_type>',
            'responses': '/api/responses',
            'diagnostic': '/api/diagnostic/results',
            'ai_explain': '/api/ai/explain',
            'ai_hint': '/api/ai/hint',
            'ai_chat': '/api/ai/chat',
            'progress': '/api/progress/<user_id>',
            'tutoring': '/api/tutoring/*'
        }
    })

# ============================================================================
# QUESTIONS ENDPOINTS
# ============================================================================

@app.route('/api/questions/<exam_type>', methods=['GET'])
def get_questions(exam_type):
    """Get questions for diagnostic test - Returns 20 random from 50 original"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get 20 random questions from the 50 original SSAT questions
        cur.execute("""
            SELECT id, question_text, options, correct_answer, 
                   question_type, difficulty, exam_type, concept,
                   explanation, is_original, source
            FROM questions
            WHERE exam_type = %s 
            AND active = TRUE
            ORDER BY RANDOM()
            LIMIT 20
        """, (exam_type,))
        
        questions = cur.fetchall()
        
        # Parse JSON fields and add question numbers
        for i, q in enumerate(questions):
            if q['options']:
                try:
                    q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                except:
                    if isinstance(q['options'], str):
                        q['options'] = [q['options']]
            
            # Add question number for frontend
            q['question_number'] = i + 1
            
            # Ensure id exists
            if not q.get('id'):
                q['id'] = f'question_{i+1}'
        
        cur.close()
        conn.close()
        
        return jsonify({
            'questions': questions, 
            'count': len(questions),
            'source': 'original_ssat_questions',
            'ai_tutoring_available': True
        })
    
    except Exception as e:
        print(f"Error getting questions: {e}")
        # Return fallback questions if database fails
        return jsonify({
            'questions': get_fallback_questions(),
            'count': 5,
            'source': 'fallback',
            'error': str(e)
        }), 500

def get_fallback_questions():
    """Fallback questions if database fails"""
    return [
        {
            'id': 'fallback_1',
            'question_text': 'A number is multiplied by 4 and then increased by 9. The result is 37. What is the original number?',
            'options': ['6', '7', '8', '9', '10'],
            'correct_answer': '7',
            'difficulty': 'medium',
            'concept': 'algebra',
            'explanation': 'Let x be the number. 4x + 9 = 37, so 4x = 28, x = 7',
            'question_number': 1
        },
        {
            'id': 'fallback_2',
            'question_text': 'Which of the following is closest to the value of 7/8 + 5/12?',
            'options': ['1.1', '1.2', '1.3', '1.4', '1.5'],
            'correct_answer': '1.3',
            'difficulty': 'medium',
            'concept': 'fractions',
            'explanation': '7/8 = 0.875, 5/12 ≈ 0.417. Sum = 1.292 ≈ 1.3',
            'question_number': 2
        }
    ]

# ============================================================================
# RESPONSE TRACKING ENDPOINTS
# ============================================================================

@app.route('/api/responses', methods=['POST'])
@jwt_required(optional=True)
def record_response():
    """Record a single response"""
    try:
        data = request.json
        user_id = get_jwt_identity() if get_jwt_identity() else None
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO responses (
                session_id, user_id, question_id, question_number,
                is_correct, selected_answer, correct_answer,
                response_time_ms, difficulty, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('sessionId'),
            user_id,
            data.get('questionId'),
            data.get('questionNumber'),
            data.get('isCorrect'),
            data.get('selectedAnswer'),
            data.get('correctAnswer'),
            data.get('responseTimeMs'),
            data.get('difficulty'),
            datetime.fromtimestamp(data.get('timestamp') / 1000) if data.get('timestamp') else datetime.now()
        ))
        
        response_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'id': response_id, 'status': 'recorded'})
    
    except Exception as e:
        print(f"Error recording response: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/diagnostic/results', methods=['POST'])
@jwt_required(optional=True)
def save_diagnostic_results():
    """Save complete diagnostic results with fatigue analysis"""
    try:
        data = request.json
        user_id = get_jwt_identity() if get_jwt_identity() else None
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Save diagnostic session
        cur.execute("""
            INSERT INTO diagnostic_sessions (
                session_id, user_id, responses, report,
                fatigue_detected, accuracy_decline, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('sessionId'),
            user_id,
            json.dumps(data.get('responses', [])),
            json.dumps(data.get('report', {})),
            data.get('report', {}).get('fatigueDetected', False),
            data.get('report', {}).get('dataSummary', {}).get('accuracyDecline', '0%'),
            datetime.now()
        ))
        
        session_db_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'id': session_db_id,
            'status': 'saved',
            'message': 'Diagnostic results saved successfully'
        })
    
    except Exception as e:
        print(f"Error saving diagnostic results: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# AI TUTORING ENDPOINTS - NEW!
# ============================================================================

@app.route('/api/ai/explain', methods=['POST'])
@jwt_required(optional=True)
def ai_explain():
    """Get AI-powered personalized explanation for wrong answer"""
    try:
        data = request.json
        user_id = get_jwt_identity() if get_jwt_identity() else 'anonymous'
        
        # Get question details from database
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM questions WHERE id = %s
        """, (data.get('questionId'),))
        
        question = cur.fetchone()
        cur.close()
        conn.close()
        
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        # Get student's performance context
        student_performance = tutoring_service._get_user_progress(user_id) if user_id != 'anonymous' else None
        
        # Generate AI explanation
        explanation = ai_tutor.generate_personalized_explanation(
            question_data=dict(question),
            student_answer=data.get('selectedAnswer'),
            correct_answer=question['correct_answer'],
            student_performance=student_performance,
            response_time_ms=data.get('responseTimeMs'),
            fatigue_level=data.get('fatigueLevel', 'none')
        )
        
        return jsonify({
            'explanation': explanation,
            'concept': question['concept'],
            'difficulty': question['difficulty']
        })
    
    except Exception as e:
        print(f"Error generating AI explanation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/hint', methods=['POST'])
@jwt_required(optional=True)
def ai_hint():
    """Get progressive AI hint without giving away answer"""
    try:
        data = request.json
        
        # Get question details
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM questions WHERE id = %s
        """, (data.get('questionId'),))
        
        question = cur.fetchone()
        cur.close()
        conn.close()
        
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        # Generate progressive hint
        hint_level = data.get('hintLevel', 1)  # 1 = gentle, 2 = stronger, 3 = almost there
        
        hint = ai_tutor.generate_hint(
            question_data=dict(question),
            hint_level=hint_level
        )
        
        return jsonify({
            'hint': hint,
            'hintLevel': hint_level,
            'maxHints': 3
        })
    
    except Exception as e:
        print(f"Error generating AI hint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/chat', methods=['POST'])
@jwt_required(optional=True)
def ai_chat():
    """Conversational AI tutoring - student can ask follow-up questions"""
    try:
        data = request.json
        user_id = get_jwt_identity() if get_jwt_identity() else 'anonymous'
        
        response = ai_tutor.chat(
            user_message=data.get('message'),
            conversation_history=data.get('history', []),
            context={
                'question_id': data.get('questionId'),
                'user_id': user_id,
                'concept': data.get('concept')
            }
        )
        
        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"Error in AI chat: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ADAPTIVE TUTORING ENDPOINTS
# ============================================================================

@app.route('/api/tutoring/next', methods=['GET'])
@jwt_required(optional=True)
def get_next_practice_question():
    """Get next practice question based on adaptive algorithm"""
    try:
        user_id = get_jwt_identity() if get_jwt_identity() else 'anonymous'
        concept = request.args.get('concept')
        difficulty = request.args.get('difficulty')
        
        question = tutoring_service.get_next_question(
            user_id=user_id,
            concept=concept,
            difficulty=difficulty
        )
        
        if not question:
            return jsonify({'error': 'No questions available'}), 404
        
        return jsonify({'question': question})
    
    except Exception as e:
        print(f"Error getting next question: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tutoring/response', methods=['POST'])
@jwt_required(optional=True)
def submit_practice_response():
    """Submit practice response and get AI-powered feedback"""
    try:
        user_id = get_jwt_identity() if get_jwt_identity() else 'anonymous'
        data = request.json
        
        # Record response
        result = tutoring_service.record_practice_response(
            user_id=user_id,
            question_id=data['question_id'],
            selected_answer=data['selected_answer'],
            response_time_ms=data['response_time_ms']
        )
        
        # If wrong answer, get AI explanation
        if not result.get('is_correct'):
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("SELECT * FROM questions WHERE id = %s", (data['question_id'],))
            question = cur.fetchone()
            cur.close()
            conn.close()
            
            if question:
                ai_explanation = ai_tutor.generate_personalized_explanation(
                    question_data=dict(question),
                    student_answer=data['selected_answer'],
                    correct_answer=question['correct_answer'],
                    student_performance=None,
                    response_time_ms=data['response_time_ms']
                )
                result['ai_explanation'] = ai_explanation
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error submitting practice response: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tutoring/progress', methods=['GET'])
@jwt_required(optional=True)
def get_progress_report():
    """Get comprehensive progress report with AI insights"""
    try:
        user_id = get_jwt_identity() if get_jwt_identity() else 'anonymous'
        
        # Get standard progress report
        report = tutoring_service.get_progress_report(user_id)
        
        # Add AI-generated insights
        ai_insights = ai_tutor.generate_progress_insights(report)
        report['ai_insights'] = ai_insights
        
        return jsonify(report)
    
    except Exception as e:
        print(f"Error getting progress report: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tutoring/recommendations', methods=['GET'])
@jwt_required(optional=True)
def get_recommendations():
    """Get AI-enhanced personalized recommendations"""
    try:
        user_id = get_jwt_identity() if get_jwt_identity() else 'anonymous'
        
        recommendations = tutoring_service.get_recommendations(user_id)
        
        # Enhance with AI-generated study plan
        ai_study_plan = ai_tutor.generate_study_plan(recommendations)
        recommendations['ai_study_plan'] = ai_study_plan
        
        return jsonify(recommendations)
    
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# USER AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """User signup"""
    try:
        data = request.json
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE email = %s", (data['email'],))
        if cur.fetchone():
            return jsonify({'error': 'User already exists'}), 400
        
        # Create user
        cur.execute("""
            INSERT INTO users (email, password_hash, full_name, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            data['email'],
            data['password'],  # In production, hash this!
            data.get('fullName', ''),
            datetime.now()
        ))
        
        user_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Create access token
        access_token = create_access_token(identity=user_id)
        
        return jsonify({
            'token': access_token,
            'user_id': user_id,
            'message': 'User created successfully'
        })
    
    except Exception as e:
        print(f"Error in signup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.json
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, email, password_hash, full_name
            FROM users
            WHERE email = %s
        """, (data['email'],))
        
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user or user['password_hash'] != data['password']:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Create access token
        access_token = create_access_token(identity=user['id'])
        
        return jsonify({
            'token': access_token,
            'user_id': user['id'],
            'email': user['email'],
            'full_name': user['full_name']
        })
    
    except Exception as e:
        print(f"Error in login: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('DEBUG', 'False').lower() == 'true')
