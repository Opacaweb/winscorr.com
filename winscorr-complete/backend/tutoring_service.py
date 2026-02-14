"""
Tutoring Service for Adaptive Question Selection and Progress Tracking
"""
from typing import Dict, List, Optional, Any
import random
import statistics
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

class TutoringService:
    def __init__(self, db_config=None):
        self.db_config = db_config or {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'winscorr'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'port': os.getenv('DB_PORT', 5432)
        }
        
        # Learning parameters
        self.mastery_threshold = 0.8  # 80% correct to master a concept
        self.confidence_threshold = 0.7  # 70% confidence for next level
        self.max_questions_per_session = 10
    
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def get_next_question(self, user_id: int, concept: str = None, 
                         difficulty: str = None) -> Dict[str, Any]:
        """
        Get next practice question based on user's progress
        
        Args:
            user_id: User ID
            concept: Optional specific concept to focus on
            difficulty: Optional difficulty level
            
        Returns:
            Question dictionary
        """
        conn = self.get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get user's progress to inform question selection
            user_progress = self._get_user_progress(user_id)
            
            # Determine which concept to focus on
            if not concept:
                concept = self._select_concept(user_progress)
            
            # Determine appropriate difficulty
            if not difficulty:
                difficulty = self._select_difficulty(user_id, concept, user_progress)
            
            # Get questions for this concept and difficulty
            # Exclude questions user has already seen recently
            cur.execute("""
                SELECT q.*
                FROM questions q
                WHERE q.exam_type = 'ssat-middle'
                AND q.question_type = 'math'
                AND q.concept = %s
                AND q.difficulty = %s
                AND q.active = TRUE
                AND q.id NOT IN (
                    SELECT question_id 
                    FROM responses 
                    WHERE user_id = %s 
                    AND timestamp > NOW() - INTERVAL '7 days'
                )
                ORDER BY RANDOM()
                LIMIT 1
            """, (concept, difficulty, user_id))
            
            question = cur.fetchone()
            
            # If no questions found with these criteria, broaden search
            if not question:
                cur.execute("""
                    SELECT q.*
                    FROM questions q
                    WHERE q.exam_type = 'ssat-middle'
                    AND q.question_type = 'math'
                    AND q.concept = %s
                    AND q.active = TRUE
                    AND q.id NOT IN (
                        SELECT question_id 
                        FROM responses 
                        WHERE user_id = %s 
                        AND timestamp > NOW() - INTERVAL '1 day'
                    )
                    ORDER BY RANDOM()
                    LIMIT 1
                """, (concept, user_id))
                
                question = cur.fetchone()
            
            # If still no questions, get any math question
            if not question:
                cur.execute("""
                    SELECT q.*
                    FROM questions q
                    WHERE q.exam_type = 'ssat-middle'
                    AND q.question_type = 'math'
                    AND q.active = TRUE
                    ORDER BY RANDOM()
                    LIMIT 1
                """)
                
                question = cur.fetchone()
            
            if question and 'options' in question:
                question['options'] = self._parse_options(question['options'])
            
            return question
            
        finally:
            cur.close()
            conn.close()
    
    def _get_user_progress(self, user_id: int) -> Dict[str, Any]:
        """Get user's progress across all concepts"""
        conn = self.get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get accuracy by concept for last 30 days
            cur.execute("""
                SELECT 
                    q.concept,
                    COUNT(*) as total_questions,
                    SUM(CASE WHEN r.is_correct THEN 1 ELSE 0 END) as correct_answers,
                    AVG(CASE WHEN r.is_correct THEN 1.0 ELSE 0.0 END) as accuracy,
                    AVG(r.response_time_ms) as avg_response_time
                FROM responses r
                JOIN questions q ON r.question_id = q.id
                WHERE r.user_id = %s
                AND r.timestamp > NOW() - INTERVAL '30 days'
                AND q.question_type = 'math'
                GROUP BY q.concept
                ORDER BY accuracy ASC
            """, (user_id,))
            
            progress_by_concept = cur.fetchall()
            
            # Get overall statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_questions,
                    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as total_correct,
                    AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END) as overall_accuracy,
                    AVG(response_time_ms) as overall_response_time
                FROM responses
                WHERE user_id = %s
                AND timestamp > NOW() - INTERVAL '30 days'
            """, (user_id,))
            
            overall_stats = cur.fetchone()
            
            return {
                'by_concept': progress_by_concept,
                'overall': overall_stats,
                'weakest_concepts': self._identify_weak_concepts(progress_by_concept),
                'strongest_concepts': self._identify_strong_concepts(progress_by_concept)
            }
            
        finally:
            cur.close()
            conn.close()
    
    def _identify_weak_concepts(self, progress_data: List[Dict]) -> List[str]:
        """Identify concepts where accuracy is below threshold"""
        weak_concepts = []
        for concept_data in progress_data:
            if concept_data['accuracy'] < self.mastery_threshold:
                weak_concepts.append({
                    'concept': concept_data['concept'],
                    'accuracy': concept_data['accuracy'],
                    'sample_size': concept_data['total_questions']
                })
        
        # Sort by accuracy (lowest first)
        weak_concepts.sort(key=lambda x: x['accuracy'])
        return [c['concept'] for c in weak_concepts[:3]]  # Top 3 weakest
    
    def _identify_strong_concepts(self, progress_data: List[Dict]) -> List[str]:
        """Identify concepts where accuracy is above threshold"""
        strong_concepts = []
        for concept_data in progress_data:
            if concept_data['accuracy'] >= self.mastery_threshold:
                strong_concepts.append({
                    'concept': concept_data['concept'],
                    'accuracy': concept_data['accuracy'],
                    'sample_size': concept_data['total_questions']
                })
        
        # Sort by accuracy (highest first)
        strong_concepts.sort(key=lambda x: x['accuracy'], reverse=True)
        return [c['concept'] for c in strong_concepts[:3]]  # Top 3 strongest
    
    def _select_concept(self, user_progress: Dict[str, Any]) -> str:
        """
        Select which concept to focus on next
        
        Strategy:
        1. Focus on weakest concepts (60% probability)
        2. Review strong concepts (30% probability)
        3. Introduce new concept (10% probability)
        """
        import random
        
        rand = random.random()
        
        if rand < 0.6 and user_progress['weakest_concepts']:
            # Focus on weakest concept
            return random.choice(user_progress['weakest_concepts'])
        elif rand < 0.9 and user_progress['strongest_concepts']:
            # Review strong concept to maintain mastery
            return random.choice(user_progress['strongest_concepts'])
        else:
            # Get all available concepts
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT DISTINCT concept 
                FROM questions 
                WHERE exam_type = 'ssat-middle' 
                AND question_type = 'math'
                AND active = TRUE
            """)
            
            all_concepts = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
            
            # Exclude concepts user has worked on recently
            practiced_concepts = [c['concept'] for c in user_progress['by_concept']]
            new_concepts = [c for c in all_concepts if c not in practiced_concepts]
            
            if new_concepts:
                return random.choice(new_concepts)
            else:
                # All concepts have been practiced, return random
                return random.choice(all_concepts)
    
    def _select_difficulty(self, user_id: int, concept: str, 
                          user_progress: Dict[str, Any]) -> str:
        """
        Select appropriate difficulty level based on user's performance
        
        Returns: 'easy', 'medium', or 'hard'
        """
        # Find user's accuracy for this concept
        concept_accuracy = None
        for concept_data in user_progress['by_concept']:
            if concept_data['concept'] == concept:
                concept_accuracy = concept_data['accuracy']
                break
        
        if concept_accuracy is None:
            # New concept, start with easy
            return 'easy'
        
        # Determine difficulty based on accuracy
        if concept_accuracy < 0.5:
            return 'easy'
        elif concept_accuracy < 0.8:
            return 'medium'
        else:
            return 'hard'
    
    def _parse_options(self, options):
        """Parse options from JSON string or return as is"""
        import json
        if isinstance(options, str):
            try:
                return json.loads(options)
            except:
                return options
        return options
    
    def record_practice_response(self, user_id: int, question_id: str, 
                               selected_answer: str, response_time_ms: int) -> Dict[str, Any]:
        """
        Record a practice response and update progress
        
        Returns:
            Analysis of the response
        """
        conn = self.get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get question details
            cur.execute("""
                SELECT correct_answer, concept, difficulty
                FROM questions
                WHERE id = %s
            """, (question_id,))
            
            question = cur.fetchone()
            if not question:
                return {'error': 'Question not found'}
            
            is_correct = selected_answer == question['correct_answer']
            
            # Record response
            cur.execute("""
                INSERT INTO responses 
                (user_id, question_id, question_number, is_correct, 
                 selected_answer, correct_answer, response_time_ms, 
                 difficulty, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                question_id,
                1,  # placeholder question number
                is_correct,
                selected_answer,
                question['correct_answer'],
                response_time_ms,
                question['difficulty'],
                datetime.now()
            ))
            
            response_id = cur.fetchone()['id']
            
            # Update user progress metrics
            self._update_user_progress(user_id, question['concept'], is_correct)
            
            conn.commit()
            
            return {
                'response_id': response_id,
                'is_correct': is_correct,
                'correct_answer': question['correct_answer'],
                'concept': question['concept'],
                'difficulty': question['difficulty'],
                'analysis': self._analyze_response(is_correct, response_time_ms, question['difficulty'])
            }
            
        finally:
            cur.close()
            conn.close()
    
    def _update_user_progress(self, user_id: int, concept: str, is_correct: bool):
        """Update user progress metrics (simplified - could use dedicated progress table)"""
        # In a full implementation, this would update a progress table
        # For now, we'll just record responses and compute progress on demand
        pass
    
    def _analyze_response(self, is_correct: bool, response_time_ms: int, 
                         difficulty: str) -> Dict[str, Any]:
        """Analyze a single response"""
        
        # Expected response times by difficulty (in milliseconds)
        expected_times = {
            'easy': 30000,    # 30 seconds
            'medium': 60000,  # 1 minute
            'hard': 90000     # 1.5 minutes
        }
        
        expected_time = expected_times.get(difficulty, 60000)
        time_ratio = response_time_ms / expected_time
        
        analysis = {
            'correctness': 'correct' if is_correct else 'incorrect',
            'response_time_ms': response_time_ms,
            'time_analysis': self._analyze_time(time_ratio, is_correct),
            'difficulty': difficulty,
            'performance': self._assess_performance(is_correct, time_ratio)
        }
        
        return analysis
    
    def _analyze_time(self, time_ratio: float, is_correct: bool) -> str:
        """Analyze if response was too fast, too slow, or appropriate"""
        if time_ratio < 0.5:
            return 'very_fast'
        elif time_ratio < 0.8:
            return 'fast'
        elif time_ratio < 1.2:
            return 'appropriate'
        elif time_ratio < 1.5:
            return 'slow'
        else:
            return 'very_slow'
    
    def _assess_performance(self, is_correct: bool, time_ratio: float) -> str:
        """Assess overall performance on this question"""
        if is_correct and time_ratio < 0.8:
            return 'excellent'
        elif is_correct and time_ratio < 1.2:
            return 'good'
        elif is_correct:
            return 'slow_but_correct'
        elif not is_correct and time_ratio < 0.5:
            return 'rushed_incorrect'
        elif not is_correct:
            return 'incorrect_with_effort'
        else:
            return 'average'
    
    def get_progress_report(self, user_id: int) -> Dict[str, Any]:
        """Generate comprehensive progress report"""
        user_progress = self._get_user_progress(user_id)
        
        # Calculate mastery levels
        mastery_by_concept = []
        for concept_data in user_progress['by_concept']:
            mastery_level = self._calculate_mastery_level(
                concept_data['accuracy'],
                concept_data['total_questions']
            )
            
            mastery_by_concept.append({
                'concept': concept_data['concept'],
                'accuracy': round(concept_data['accuracy'] * 100, 1),
                'total_questions': concept_data['total_questions'],
                'mastery_level': mastery_level,
                'avg_response_time': round(concept_data.get('avg_response_time', 0))
            })
        
        # Sort by mastery level (lowest first)
        mastery_by_concept.sort(key=lambda x: x['accuracy'])
        
        # Generate recommendations
        recommendations = self._generate_recommendations(user_progress)
        
        # Calculate overall metrics
        overall = user_progress['overall'] or {}
        overall_accuracy = round(overall.get('overall_accuracy', 0) * 100, 1)
        
        return {
            'user_id': user_id,
            'generated_at': datetime.now().isoformat(),
            'overall_accuracy': overall_accuracy,
            'total_questions': overall.get('total_questions', 0),
            'total_correct': overall.get('total_correct', 0),
            'avg_response_time': round(overall.get('overall_response_time', 0)),
            'mastery_by_concept': mastery_by_concept,
            'weakest_concepts': user_progress['weakest_concepts'],
            'strongest_concepts': user_progress['strongest_concepts'],
            'recommendations': recommendations,
            'next_week_focus': self._get_next_week_focus(user_progress)
        }
    
    def _calculate_mastery_level(self, accuracy: float, sample_size: int) -> str:
        """Calculate mastery level based on accuracy and sample size"""
        if sample_size < 5:
            return 'beginning'
        
        if accuracy >= 0.9:
            return 'mastered'
        elif accuracy >= 0.8:
            return 'proficient'
        elif accuracy >= 0.6:
            return 'developing'
        elif accuracy >= 0.4:
            return 'basic'
        else:
            return 'beginning'
    
    def _generate_recommendations(self, user_progress: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Overall accuracy recommendation
        overall_accuracy = user_progress['overall'].get('overall_accuracy', 0) if user_progress['overall'] else 0
        if overall_accuracy < 0.6:
            recommendations.append("Focus on building foundational skills with easier questions")
        elif overall_accuracy < 0.8:
            recommendations.append("Continue practice with mixed difficulty levels")
        else:
            recommendations.append("Challenge yourself with more difficult questions to reach mastery")
        
        # Weak concepts recommendation
        if user_progress['weakest_concepts']:
            weak_concepts_str = ', '.join(user_progress['weakest_concepts'][:3])
            recommendations.append(f"Targeted practice needed in: {weak_concepts_str}")
        
        # Response time recommendation
        avg_time = user_progress['overall'].get('overall_response_time', 0) if user_progress['overall'] else 0
        if avg_time > 90000:  # > 1.5 minutes average
            recommendations.append("Practice managing time pressure with timed sessions")
        elif avg_time < 30000:  # < 30 seconds average
            recommendations.append("Focus on accuracy over speed - take time to check work")
        
        # Consistency recommendation
        if len(user_progress['by_concept']) >= 3:
            accuracies = [c['accuracy'] for c in user_progress['by_concept']]
            consistency = statistics.stdev(accuracies) if len(accuracies) > 1 else 0
            if consistency > 0.3:
                recommendations.append("Work on consistent performance across all concepts")
        
        return recommendations
    
    def _get_next_week_focus(self, user_progress: Dict[str, Any]) -> str:
        """Determine focus for next week"""
        if not user_progress['weakest_concepts']:
            return "Review all concepts and tackle advanced problems"
        
        # Focus on weakest concept
        weakest = user_progress['weakest_concepts'][0] if user_progress['weakest_concepts'] else None
        
        # Check if user has practiced this concept enough
        for concept_data in user_progress['by_concept']:
            if concept_data['concept'] == weakest:
                if concept_data['total_questions'] < 10:
                    return f"Build foundation in {weakest} with basic practice"
                else:
                    return f"Master {weakest} with mixed difficulty questions"
        
        return f"Introduce and practice {weakest} concepts"
    
    def get_recommendations(self, user_id: int) -> Dict[str, Any]:
        """Get personalized recommendations for the user"""
        progress_report = self.get_progress_report(user_id)
        
        return {
            'user_id': user_id,
            'generated_at': datetime.now().isoformat(),
            'focus_areas': progress_report['weakest_concepts'][:2],
            'practice_plan': {
                'daily_goal': '10 questions per day',
                'weekly_goal': '70 questions per week',
                'focus_concepts': progress_report['weakest_concepts'][:3]
            },
            'specific_recommendations': progress_report['recommendations'],
            'predicted_improvement': self._predict_improvement(progress_report)
        }
    
    def _predict_improvement(self, progress_report: Dict[str, Any]) -> Dict[str, Any]:
        """Predict improvement based on current progress"""
        overall_accuracy = progress_report.get('overall_accuracy', 50)
        
        # Simple linear prediction based on typical learning curves
        weeks_needed = {
            'to_70%': max(0, (70 - overall_accuracy) / 5),  # 5% per week
            'to_80%': max(0, (80 - overall_accuracy) / 4),  # 4% per week
            'to_90%': max(0, (90 - overall_accuracy) / 3),  # 3% per week
        }
        
        return {
            'current_level': self._get_accuracy_level(overall_accuracy),
            'weeks_to_next_level': round(weeks_needed['to_70%'], 1),
            'projected_8_week_accuracy': min(100, overall_accuracy + 8 * 4),  # 4% per week
            'recommended_practice_hours': 3  # hours per week
        }
    
    def _get_accuracy_level(self, accuracy: float) -> str:
        """Convert accuracy to descriptive level"""
        if accuracy >= 90:
            return 'Advanced'
        elif accuracy >= 80:
            return 'Proficient'
        elif accuracy >= 70:
            return 'Competent'
        elif accuracy >= 60:
            return 'Developing'
        else:
            return 'Beginning'}