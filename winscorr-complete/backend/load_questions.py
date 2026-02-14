"""
Load YOUR original questions into PostgreSQL database
"""
import json
import psycopg2
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'winscorr'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': os.getenv('DB_PORT', 5432)


def load_your_questions():
    """Load your 50 original questions into database"""
    
    try:
        # Load your questions from JSON file
        with open('../data/original_questions.json', 'r') as f:
            questions = json.load(f)
        
        print(f"Loaded {len(questions) questions from JSON file")
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Clear existing questions for this exam type (optional)
        # cur.execute("DELETE FROM questions WHERE exam_type = 'ssat-middle'")
        # print("Cleared existing SSAT questions")
        
        inserted_count = 0
        skipped_count = 0
        
        for i, question in enumerate(questions, 1):
            try:
                # Check if question already exists (by question text)
                cur.execute(
                    "SELECT id FROM questions WHERE question_text = %s",
                    (question['question_text'],)
                )
                
                if cur.fetchone():
                    print(f"Skipping duplicate question {i: {question['question_text'][:50]...")
                    skipped_count += 1
                    continue
                
                # Insert question
                cur.execute("""
                    INSERT INTO questions 
                    (id, exam_type, question_type, difficulty, concept,
                     question_text, options, correct_answer, explanation,
                     is_original, source, attribution, active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),  # Generate new UUID
                    question.get('exam_type', 'ssat-middle'),
                    question.get('question_type', 'math'),
                    question.get('difficulty', 'medium'),
                    question.get('concept', 'general'),
                    question['question_text'],
                    json.dumps(question['options']),
                    str(question['correct_answer']),
                    question.get('explanation', ''),
                    True,  # is_original
                    'original',  # source
                    '© Your Name - All rights reserved',  # attribution
                    True,  # active
                    datetime.now()
                ))
                
                inserted_count += 1
                print(f"Inserted question {i: {question['question_text'][:50]...")
                
            except Exception as e:
                print(f"Error inserting question {i: {e")
                skipped_count += 1
                continue
        
        conn.commit()
        
        # Verify count
        cur.execute("SELECT COUNT(*) FROM questions WHERE exam_type = 'ssat-middle'")
        total_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        print(f"n✅Success!")
        print(f"Total questions in database: {total_count")
        print(f"Inserted: {inserted_count")
        print(f"Skipped (duplicates): {skipped_count")
        
        return True
        
    except Exception as e:
        print(f"❌Error loading questions: {e")
        return False

def verify_questions():
    """Verify questions are loaded correctly"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Get question counts by difficulty
        cur.execute("""
            SELECT difficulty, COUNT(*) 
            FROM questions 
            WHERE exam_type = 'ssat-middle'
            GROUP BY difficulty
            ORDER BY difficulty
        """)
        
        print("nu56522  Question Statistics:")
        for difficulty, count in cur.fetchall():
            print(f"  {difficulty: {count questions")
        
        # Get question counts by concept
        cur.execute("""
            SELECT concept, COUNT(*) 
            FROM questions 
            WHERE exam_type = 'ssat-middle'
            GROUP BY concept
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        
        print("nu56538  Top Concepts:")
        for concept, count in cur.fetchall():
            print(f"  {concept: {count questions")
        
        # Get sample questions
        cur.execute("""
            SELECT question_text, difficulty, concept
            FROM questions 
            WHERE exam_type = 'ssat-middle'
            LIMIT 3
        """)
        
        print("nu56589  Sample Questions:")
        for i, (text, difficulty, concept) in enumerate(cur.fetchall(), 1):
            print(f"n  Question {i ({difficulty - {concept):")
            print(f"  {text[:80]...")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error verifying questions: {e")

if __name__ == "__main__":
    print("u56960  Loading YOUR 50 Original Questions into WinScorr Database...")
    print("=" * 60)
    
    if load_your_questions():
        print("n" + "=" * 60)
        verify_questions()
        
        print("n✅Ready to use!")
        print("Your questions are now in the database.")
        print("Restart your backend to see them in the diagnostic.")
    else:
        print("n❌Failed to load questions")