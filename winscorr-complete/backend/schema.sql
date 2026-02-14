-- WinScorr Complete Database Schema
-- PostgreSQL database for AI-powered tutoring system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    subscription_status VARCHAR(50) DEFAULT 'trial',
    subscription_expires TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- ============================================================================
-- QUESTIONS TABLE - Stores all 50 original SSAT questions
-- ============================================================================
CREATE TABLE IF NOT EXISTS questions (
    id VARCHAR(50) PRIMARY KEY,
    exam_type VARCHAR(50) NOT NULL DEFAULT 'ssat-middle',
    question_type VARCHAR(50) NOT NULL DEFAULT 'math',
    difficulty VARCHAR(20) NOT NULL,
    concept VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    options JSONB NOT NULL,
    correct_answer VARCHAR(255) NOT NULL,
    explanation TEXT,
    is_original BOOLEAN DEFAULT TRUE,
    source VARCHAR(255) DEFAULT 'winscorr_original',
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_questions_exam_type ON questions(exam_type);
CREATE INDEX idx_questions_concept ON questions(concept);
CREATE INDEX idx_questions_difficulty ON questions(difficulty);
CREATE INDEX idx_questions_active ON questions(active);

-- ============================================================================
-- RESPONSES TABLE - Tracks all student responses
-- ============================================================================
CREATE TABLE IF NOT EXISTS responses (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    question_id VARCHAR(50) REFERENCES questions(id),
    question_number INTEGER,
    is_correct BOOLEAN NOT NULL,
    selected_answer VARCHAR(255) NOT NULL,
    correct_answer VARCHAR(255) NOT NULL,
    response_time_ms INTEGER NOT NULL,
    difficulty VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_responses_session ON responses(session_id);
CREATE INDEX idx_responses_user ON responses(user_id);
CREATE INDEX idx_responses_question ON responses(question_id);
CREATE INDEX idx_responses_timestamp ON responses(timestamp);

-- ============================================================================
-- DIAGNOSTIC SESSIONS TABLE - Stores complete diagnostic results
-- ============================================================================
CREATE TABLE IF NOT EXISTS diagnostic_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    responses JSONB NOT NULL,
    report JSONB NOT NULL,
    fatigue_detected BOOLEAN DEFAULT FALSE,
    accuracy_decline VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_diagnostic_user ON diagnostic_sessions(user_id);
CREATE INDEX idx_diagnostic_session ON diagnostic_sessions(session_id);
CREATE INDEX idx_diagnostic_timestamp ON diagnostic_sessions(timestamp);

-- ============================================================================
-- AI INTERACTIONS TABLE - Tracks AI tutor interactions
-- ============================================================================
CREATE TABLE IF NOT EXISTS ai_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    question_id VARCHAR(50) REFERENCES questions(id),
    interaction_type VARCHAR(50) NOT NULL, -- 'explanation', 'hint', 'chat'
    user_message TEXT,
    ai_response TEXT NOT NULL,
    response_time_ms INTEGER,
    helpful BOOLEAN, -- User feedback
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_user ON ai_interactions(user_id);
CREATE INDEX idx_ai_question ON ai_interactions(question_id);
CREATE INDEX idx_ai_type ON ai_interactions(interaction_type);
CREATE INDEX idx_ai_timestamp ON ai_interactions(timestamp);

-- ============================================================================
-- PRACTICE SESSIONS TABLE - Tracks adaptive practice sessions
-- ============================================================================
CREATE TABLE IF NOT EXISTS practice_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    concept VARCHAR(100),
    difficulty VARCHAR(20),
    questions_completed INTEGER DEFAULT 0,
    accuracy DECIMAL(5,2),
    avg_response_time_ms INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_practice_user ON practice_sessions(user_id);
CREATE INDEX idx_practice_concept ON practice_sessions(concept);

-- ============================================================================
-- STUDENT PROGRESS TABLE - Aggregated progress tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS student_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    total_questions_attempted INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    overall_accuracy DECIMAL(5,2),
    concepts_mastered JSONB DEFAULT '[]',
    concepts_in_progress JSONB DEFAULT '[]',
    concepts_needs_work JSONB DEFAULT '[]',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_progress_user ON student_progress(user_id);

-- ============================================================================
-- CONCEPT MASTERY TABLE - Detailed concept tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS concept_mastery (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    concept VARCHAR(100) NOT NULL,
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    accuracy DECIMAL(5,2),
    mastery_level VARCHAR(50), -- 'beginning', 'basic', 'developing', 'proficient', 'mastered'
    last_practiced TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, concept)
);

CREATE INDEX idx_mastery_user ON concept_mastery(user_id);
CREATE INDEX idx_mastery_concept ON concept_mastery(concept);
CREATE INDEX idx_mastery_level ON concept_mastery(mastery_level);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update timestamp on row update
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for questions table
CREATE TRIGGER update_questions_updated_at BEFORE UPDATE ON questions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update student progress after new response
CREATE OR REPLACE FUNCTION update_student_progress()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert student progress
    INSERT INTO student_progress (user_id, total_questions_attempted, total_correct, overall_accuracy, last_updated)
    VALUES (
        NEW.user_id,
        1,
        CASE WHEN NEW.is_correct THEN 1 ELSE 0 END,
        CASE WHEN NEW.is_correct THEN 100.0 ELSE 0.0 END,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (user_id) DO UPDATE SET
        total_questions_attempted = student_progress.total_questions_attempted + 1,
        total_correct = student_progress.total_correct + CASE WHEN NEW.is_correct THEN 1 ELSE 0 END,
        overall_accuracy = ROUND(
            (student_progress.total_correct::numeric + CASE WHEN NEW.is_correct THEN 1 ELSE 0 END) / 
            (student_progress.total_questions_attempted::numeric + 1) * 100,
            2
        ),
        last_updated = CURRENT_TIMESTAMP;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for responses table (only if user_id is not null)
CREATE TRIGGER update_progress_on_response AFTER INSERT ON responses
    FOR EACH ROW 
    WHEN (NEW.user_id IS NOT NULL)
    EXECUTE FUNCTION update_student_progress();

-- ============================================================================
-- SEED DATA - The 50 Original SSAT Questions
-- ============================================================================
-- This will be populated by the load_questions.py script
-- Or you can manually insert from the original_questions.json file

-- ============================================================================
-- SAMPLE DATA FOR TESTING (Optional)
-- ============================================================================
-- Insert a test user
INSERT INTO users (email, password_hash, full_name, subscription_status)
VALUES ('test@winscorr.com', 'hashed_password_here', 'Test Student', 'active')
ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- View for concept performance overview
CREATE OR REPLACE VIEW concept_performance_overview AS
SELECT 
    u.id as user_id,
    u.email,
    q.concept,
    COUNT(*) as questions_attempted,
    SUM(CASE WHEN r.is_correct THEN 1 ELSE 0 END) as correct_answers,
    ROUND(AVG(CASE WHEN r.is_correct THEN 100.0 ELSE 0.0 END), 2) as accuracy,
    ROUND(AVG(r.response_time_ms), 0) as avg_response_time_ms
FROM responses r
JOIN users u ON r.user_id = u.id
JOIN questions q ON r.question_id = q.id
WHERE r.timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY u.id, u.email, q.concept
ORDER BY u.id, accuracy ASC;

-- View for fatigue analysis
CREATE OR REPLACE VIEW fatigue_analysis AS
SELECT 
    session_id,
    user_id,
    (report->>'fatigueDetected')::boolean as fatigue_detected,
    report->>'fatigueLevel' as fatigue_level,
    report->'dataSummary'->>'accuracyDecline' as accuracy_decline,
    timestamp
FROM diagnostic_sessions
ORDER BY timestamp DESC;

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_responses_user_timestamp ON responses(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_responses_user_concept ON responses(user_id, question_id);
CREATE INDEX IF NOT EXISTS idx_ai_user_timestamp ON ai_interactions(user_id, timestamp DESC);

-- ============================================================================
-- GRANTS (adjust for your user)
-- ============================================================================
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_db_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_db_user;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE questions IS 'Stores all SSAT Middle Level math questions';
COMMENT ON TABLE responses IS 'Tracks individual question responses from students';
COMMENT ON TABLE diagnostic_sessions IS 'Stores complete diagnostic test results with fatigue analysis';
COMMENT ON TABLE ai_interactions IS 'Logs all AI tutor interactions for quality monitoring';
COMMENT ON TABLE concept_mastery IS 'Tracks student mastery level for each mathematical concept';
COMMENT ON TABLE student_progress IS 'Aggregated student progress metrics';
