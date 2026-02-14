/**
 * WinScorr API Client
 * Handles all communication with backend API including AI features
 */

class ApiClient {
    constructor() {
        // Determine base URL based on environment
        this.baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'http://localhost:5000/api'
            : '/api'; // Use relative path for production (Railway)
        
        this.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        
        // Load auth token if exists
        const token = localStorage.getItem('winscorr_token');
        if (token) {
            this.headers['Authorization'] = `Bearer ${token}`;
        }
    }
    
    /**
     * Make HTTP request to API
     */
    async request(endpoint, method = 'GET', data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method,
            headers: this.headers,
            credentials: 'include'
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url, options);
            
            // Handle authentication errors
            if (response.status === 401) {
                localStorage.removeItem('winscorr_token');
                delete this.headers['Authorization'];
                // For now, just continue without auth (optional login)
                return null;
            }
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.error || `API Error: ${response.status}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error(`API Request Failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    // ========================================================================
    // Question Endpoints
    // ========================================================================
    
    /**
     * Get diagnostic questions (20 random from 50 originals)
     */
    async getQuestions(examType = 'ssat-middle') {
        try {
            const response = await this.request(`/questions/${examType}`);
            return response.questions || [];
        } catch (error) {
            console.error('Failed to load questions:', error);
            return this.getFallbackQuestions();
        }
    }
    
    /**
     * Fallback questions if API fails
     */
    getFallbackQuestions() {
        return [
            {
                id: 'fallback_1',
                question_text: 'A number is multiplied by 4 and then increased by 9. The result is 37. What is the original number?',
                options: ['6', '7', '8', '9', '10'],
                correct_answer: '7',
                difficulty: 'medium',
                concept: 'algebra',
                explanation: 'Let x be the number. 4x + 9 = 37, so 4x = 28, x = 7',
                question_number: 1
            },
            {
                id: 'fallback_2',
                question_text: 'Which of the following is closest to the value of 7/8 + 5/12?',
                options: ['1.1', '1.2', '1.3', '1.4', '1.5'],
                correct_answer: '1.3',
                difficulty: 'medium',
                concept: 'fractions',
                explanation: '7/8 = 0.875, 5/12 ≈ 0.417. Sum = 1.292 ≈ 1.3',
                question_number: 2
            }
        ];
    }
    
    // ========================================================================
    // Response Tracking
    // ========================================================================
    
    /**
     * Record a single response
     */
    async recordResponse(responseData) {
        try {
            return await this.request('/responses', 'POST', responseData);
        } catch (error) {
            console.error('Failed to record response:', error);
            // Save locally as backup
            this.saveResponseLocally(responseData);
            return { status: 'saved_locally' };
        }
    }
    
    /**
     * Save diagnostic results
     */
    async saveDiagnosticResults(resultsData) {
        try {
            return await this.request('/diagnostic/results', 'POST', resultsData);
        } catch (error) {
            console.error('Failed to save diagnostic results:', error);
            // Save locally as backup
            localStorage.setItem(
                `winscorr_diagnostic_${resultsData.sessionId}`,
                JSON.stringify(resultsData)
            );
            return { status: 'saved_locally' };
        }
    }
    
    /**
     * Save response locally (backup)
     */
    saveResponseLocally(responseData) {
        const key = `winscorr_responses_${responseData.sessionId}`;
        let responses = JSON.parse(localStorage.getItem(key) || '[]');
        responses.push(responseData);
        localStorage.setItem(key, JSON.stringify(responses));
    }
    
    // ========================================================================
    // AI Tutoring Endpoints - NEW!
    // ========================================================================
    
    /**
     * Get AI-powered explanation for wrong answer
     */
    async getAIExplanation(questionId, selectedAnswer, responseTimeMs, fatigueLevel = 'none') {
        try {
            const response = await this.request('/ai/explain', 'POST', {
                questionId,
                selectedAnswer,
                responseTimeMs,
                fatigueLevel
            });
            return response.explanation;
        } catch (error) {
            console.error('Failed to get AI explanation:', error);
            return 'Sorry, I couldn\'t generate an explanation right now. Please try asking a specific question in the chat!';
        }
    }
    
    /**
     * Get progressive hint from AI
     */
    async getAIHint(questionId, hintLevel = 1) {
        try {
            const response = await this.request('/ai/hint', 'POST', {
                questionId,
                hintLevel
            });
            return response.hint;
        } catch (error) {
            console.error('Failed to get AI hint:', error);
            return 'Think about what concept this question is testing. Take your time!';
        }
    }
    
    /**
     * Chat with AI tutor
     */
    async chatWithAI(message, questionId = null, history = []) {
        try {
            const response = await this.request('/ai/chat', 'POST', {
                message,
                questionId,
                history
            });
            return response.response;
        } catch (error) {
            console.error('Failed to chat with AI:', error);
            return 'I\'m having trouble connecting right now. Please try again!';
        }
    }
    
    // ========================================================================
    // Adaptive Tutoring
    // ========================================================================
    
    /**
     * Get next practice question (adaptive)
     */
    async getNextPracticeQuestion(concept = null, difficulty = null) {
        try {
            let endpoint = '/tutoring/next';
            const params = new URLSearchParams();
            if (concept) params.append('concept', concept);
            if (difficulty) params.append('difficulty', difficulty);
            if (params.toString()) endpoint += `?${params.toString()}`;
            
            const response = await this.request(endpoint);
            return response.question;
        } catch (error) {
            console.error('Failed to get next question:', error);
            return null;
        }
    }
    
    /**
     * Submit practice response
     */
    async submitPracticeResponse(questionId, selectedAnswer, responseTimeMs) {
        try {
            return await this.request('/tutoring/response', 'POST', {
                question_id: questionId,
                selected_answer: selectedAnswer,
                response_time_ms: responseTimeMs
            });
        } catch (error) {
            console.error('Failed to submit practice response:', error);
            return null;
        }
    }
    
    /**
     * Get progress report
     */
    async getProgressReport() {
        try {
            return await this.request('/tutoring/progress');
        } catch (error) {
            console.error('Failed to get progress report:', error);
            return null;
        }
    }
    
    /**
     * Get recommendations
     */
    async getRecommendations() {
        try {
            return await this.request('/tutoring/recommendations');
        } catch (error) {
            console.error('Failed to get recommendations:', error);
            return null;
        }
    }
    
    // ========================================================================
    // Authentication
    // ========================================================================
    
    /**
     * User signup
     */
    async signup(email, password, fullName) {
        try {
            const response = await this.request('/auth/signup', 'POST', {
                email,
                password,
                fullName
            });
            
            if (response.token) {
                localStorage.setItem('winscorr_token', response.token);
                this.headers['Authorization'] = `Bearer ${response.token}`;
            }
            
            return response;
        } catch (error) {
            console.error('Signup failed:', error);
            throw error;
        }
    }
    
    /**
     * User login
     */
    async login(email, password) {
        try {
            const response = await this.request('/auth/login', 'POST', {
                email,
                password
            });
            
            if (response.token) {
                localStorage.setItem('winscorr_token', response.token);
                this.headers['Authorization'] = `Bearer ${response.token}`;
            }
            
            return response;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    }
    
    /**
     * Logout
     */
    logout() {
        localStorage.removeItem('winscorr_token');
        delete this.headers['Authorization'];
    }
    
    // ========================================================================
    // Health Check
    // ========================================================================
    
    /**
     * Check API health
     */
    async checkHealth() {
        try {
            return await this.request('/health');
        } catch (error) {
            console.error('Health check failed:', error);
            return { status: 'unhealthy', error: error.message };
        }
    }
}

// Create global instance
window.apiClient = new ApiClient();
