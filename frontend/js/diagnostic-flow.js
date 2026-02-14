/**
 * Diagnostic Flow Manager
 * Manages the complete diagnostic test experience with AI tutoring
 */

class DiagnosticFlow {
    constructor() {
        this.currentQuestion = 0;
        this.questions = [];
        this.tracker = window.winscorrTracker;
        this.apiClient = window.apiClient;
        this.isComplete = false;
        this.conversationHistory = [];
        this.hintLevel = 0;
        
        this.init();
    }
    
    async init() {
        // Show loading state
        this.showLoading();
        
        // Load questions
        await this.loadQuestions();
        
        // Initialize UI
        this.initializeUI();
        
        // Start the test
        this.startTest();
    }
    
    /**
     * Show loading state
     */
    showLoading() {
        const loadingState = document.getElementById('loading-state');
        if (loadingState) {
            loadingState.style.display = 'block';
        }
    }
    
    /**
     * Hide loading state
     */
    hideLoading() {
        const loadingState = document.getElementById('loading-state');
        if (loadingState) {
            loadingState.style.display = 'none';
        }
    }
    
    /**
     * Load questions from API
     */
    async loadQuestions() {
        try {
            this.questions = await this.apiClient.getQuestions('ssat-middle');
            
            if (!this.questions || this.questions.length === 0) {
                throw new Error('No questions returned from API');
            }
            
            console.log(`Loaded ${this.questions.length} questions`);
            
            // Shuffle for fairness
            this.shuffleQuestions();
            
        } catch (error) {
            console.error('Failed to load questions:', error);
            // Use fallback
            this.questions = this.apiClient.getFallbackQuestions();
            this.shuffleQuestions();
        }
    }
    
    /**
     * Shuffle questions (Fisher-Yates algorithm)
     */
    shuffleQuestions() {
        for (let i = this.questions.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.questions[i], this.questions[j]] = [this.questions[j], this.questions[i]];
        }
        
        // Renumber questions
        this.questions.forEach((q, index) => {
            q.question_number = index + 1;
            if (!q.id) {
                q.id = `question_${index + 1}`;
            }
        });
    }
    
    /**
     * Initialize UI elements
     */
    initializeUI() {
        // Get all elements
        this.questionTextEl = document.getElementById('question-text');
        this.questionConceptEl = document.getElementById('question-concept');
        this.questionDifficultyEl = document.getElementById('question-difficulty');
        this.questionOptionsEl = document.getElementById('question-options');
        this.progressFillEl = document.getElementById('progress-fill');
        this.progressTextEl = document.getElementById('progress-text');
        this.timerDisplayEl = document.getElementById('timer-display');
        this.nextBtn = document.getElementById('next-btn');
        this.finishBtn = document.getElementById('finish-btn');
        
        // AI elements
        this.aiHelpSection = document.getElementById('ai-help-section');
        this.hintSection = document.getElementById('hint-section');
        this.hintButton = document.getElementById('hint-button');
        this.hintDisplay = document.getElementById('hint-display');
        this.hintLevelEl = document.getElementById('hint-level');
        this.currentHintLevelEl = document.getElementById('current-hint-level');
        this.chatSection = document.getElementById('chat-section');
        this.chatToggle = document.getElementById('chat-toggle');
        this.chatContainer = document.getElementById('chat-container');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.chatSend = document.getElementById('chat-send');
        this.aiExplanation = document.getElementById('ai-explanation');
        this.aiExplanationText = document.getElementById('ai-explanation-text');
        this.aiLoading = document.getElementById('ai-loading');
        
        // Event listeners
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => this.nextQuestion());
        }
        
        if (this.finishBtn) {
            this.finishBtn.addEventListener('click', () => this.finishDiagnostic());
        }
        
        if (this.hintButton) {
            this.hintButton.addEventListener('click', () => this.requestHint());
        }
        
        if (this.chatToggle) {
            this.chatToggle.addEventListener('click', () => this.toggleChat());
        }
        
        if (this.chatSend) {
            this.chatSend.addEventListener('click', () => this.sendChatMessage());
        }
        
        if (this.chatInput) {
            this.chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendChatMessage();
                }
            });
        }
    }
    
    /**
     * Start the test
     */
    startTest() {
        // Hide loading
        this.hideLoading();
        
        // Show test container
        const testContainer = document.getElementById('test-container');
        if (testContainer) {
            testContainer.style.display = 'block';
        }
        
        // Start timer
        this.startTimer();
        
        // Show first question
        this.showQuestion();
    }
    
    /**
     * Start the timer
     */
    startTimer() {
        this.testStartTime = Date.now();
        this.timerInterval = setInterval(() => {
            this.updateTimer();
        }, 1000);
    }
    
    /**
     * Update timer display
     */
    updateTimer() {
        if (!this.timerDisplayEl) return;
        
        const elapsed = Date.now() - this.testStartTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        
        this.timerDisplayEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    
    /**
     * Show current question
     */
    showQuestion() {
        if (this.currentQuestion >= this.questions.length || this.currentQuestion >= 20) {
            this.completeDiagnostic();
            return;
        }
        
        const question = this.questions[this.currentQuestion];
        
        // Reset hint level
        this.hintLevel = 0;
        this.conversationHistory = [];
        
        // Hide AI help section
        if (this.aiHelpSection) {
            this.aiHelpSection.style.display = 'none';
        }
        
        // Update question display
        if (this.questionTextEl) {
            this.questionTextEl.textContent = question.question_text;
        }
        
        if (this.questionConceptEl) {
            this.questionConceptEl.textContent = question.concept || 'Math';
        }
        
        if (this.questionDifficultyEl) {
            this.questionDifficultyEl.textContent = question.difficulty || 'Medium';
        }
        
        // Update options
        this.displayOptions(question);
        
        // Update progress
        this.updateProgress();
        
        // Start tracking this question
        this.tracker.startQuestion(
            question.id,
            question.question_number,
            question.difficulty || 'medium'
        );
    }
    
    /**
     * Display answer options
     */
    displayOptions(question) {
        if (!this.questionOptionsEl) return;
        
        this.questionOptionsEl.innerHTML = '';
        
        // Ensure options is an array
        const options = Array.isArray(question.options)
            ? question.options
            : JSON.parse(question.options || '[]');
        
        options.forEach((option, index) => {
            const button = document.createElement('button');
            button.className = 'option-btn';
            button.textContent = `${String.fromCharCode(65 + index)}) ${option}`;
            button.addEventListener('click', () => this.selectOption(option, question.correct_answer));
            this.questionOptionsEl.appendChild(button);
        });
    }
    
    /**
     * Handle option selection
     */
    async selectOption(selectedAnswer, correctAnswer) {
        const question = this.questions[this.currentQuestion];
        const isCorrect = selectedAnswer === correctAnswer;
        
        // Record response in tracker
        this.tracker.recordResponse(
            question.id,
            isCorrect,
            selectedAnswer,
            correctAnswer
        );
        
        // Send to backend
        await this.apiClient.recordResponse({
            sessionId: this.tracker.sessionId,
            questionId: question.id,
            questionNumber: question.question_number,
            isCorrect,
            selectedAnswer,
            correctAnswer,
            responseTimeMs: Date.now() - this.tracker.questionStartTime,
            difficulty: question.difficulty,
            timestamp: Date.now()
        });
        
        // Visual feedback
        this.showAnswerFeedback(selectedAnswer, correctAnswer, isCorrect);
        
        // Show AI help
        await this.showAIHelp(question, selectedAnswer, isCorrect);
        
        // Enable next button
        if (this.nextBtn) {
            this.nextBtn.disabled = false;
            this.nextBtn.style.opacity = '1';
        }
        
        // Auto-advance after delay
        setTimeout(() => {
            if (this.currentQuestion < Math.min(this.questions.length, 20) - 1) {
                // Not last question - show next button
            } else {
                // Last question - show finish button
                if (this.finishBtn && this.nextBtn) {
                    this.finishBtn.style.display = 'block';
                    this.nextBtn.style.display = 'none';
                }
            }
        }, 2000);
    }
    
    /**
     * Show visual feedback for answer
     */
    showAnswerFeedback(selectedAnswer, correctAnswer, isCorrect) {
        const buttons = document.querySelectorAll('.option-btn');
        buttons.forEach(btn => {
            btn.disabled = true;
            
            // Highlight selected answer
            if (btn.textContent.includes(selectedAnswer)) {
                btn.classList.add(isCorrect ? 'correct' : 'incorrect');
            }
            
            // Show correct answer if wrong
            if (!isCorrect && btn.textContent.includes(correctAnswer)) {
                btn.classList.add('show-correct');
            }
        });
    }
    
    /**
     * Show AI help after answering
     */
    async showAIHelp(question, selectedAnswer, isCorrect) {
        if (!this.aiHelpSection) return;
        
        // Show AI help section
        this.aiHelpSection.style.display = 'block';
        
        if (!isCorrect) {
            // Wrong answer - get AI explanation
            await this.getAIExplanation(question, selectedAnswer);
        }
        
        // Show chat option for follow-up questions
        if (this.chatSection) {
            this.chatSection.style.display = 'block';
        }
    }
    
    /**
     * Get AI explanation for wrong answer
     */
    async getAIExplanation(question, selectedAnswer) {
        if (!this.aiExplanation) return;
        
        // Show AI explanation container
        this.aiExplanation.style.display = 'block';
        
        // Show loading
        if (this.aiLoading) {
            this.aiLoading.style.display = 'flex';
        }
        if (this.aiExplanationText) {
            this.aiExplanationText.style.display = 'none';
        }
        
        try {
            // Get fatigue analysis for context
            const fatigueAnalysis = this.tracker.analyzeFatigue();
            
            // Get AI explanation
            const explanation = await this.apiClient.getAIExplanation(
                question.id,
                selectedAnswer,
                Date.now() - this.tracker.questionStartTime,
                fatigueAnalysis.fatigueLevel
            );
            
            // Hide loading, show explanation
            if (this.aiLoading) {
                this.aiLoading.style.display = 'none';
            }
            if (this.aiExplanationText) {
                this.aiExplanationText.style.display = 'block';
                this.aiExplanationText.innerHTML = this.formatAIResponse(explanation);
            }
            
        } catch (error) {
            console.error('Failed to get AI explanation:', error);
            if (this.aiLoading) {
                this.aiLoading.style.display = 'none';
            }
            if (this.aiExplanationText) {
                this.aiExplanationText.style.display = 'block';
                this.aiExplanationText.textContent = 'Sorry, I couldn\'t generate an explanation. Try asking in the chat below!';
            }
        }
    }
    
    /**
     * Format AI response (convert newlines to paragraphs)
     */
    formatAIResponse(text) {
        return text.split('\n\n').map(p => `<p>${p}</p>`).join('');
    }
    
    /**
     * Request progressive hint (before answering)
     */
    async requestHint() {
        if (this.hintLevel >= 3) {
            alert('You\'ve used all 3 hints for this question!');
            return;
        }
        
        const question = this.questions[this.currentQuestion];
        this.hintLevel++;
        
        if (!this.hintDisplay) return;
        
        // Show loading
        this.hintDisplay.style.display = 'block';
        this.hintDisplay.textContent = 'AI is thinking...';
        
        try {
            // Get AI hint
            const hint = await this.apiClient.getAIHint(question.id, this.hintLevel);
            
            // Display hint
            this.hintDisplay.textContent = hint;
            
            // Update hint level display
            if (this.hintLevelEl && this.currentHintLevelEl) {
                this.hintLevelEl.style.display = 'block';
                this.currentHintLevelEl.textContent = this.hintLevel;
            }
            
            // Disable button if max hints reached
            if (this.hintLevel >= 3 && this.hintButton) {
                this.hintButton.disabled = true;
                this.hintButton.textContent = 'No more hints available';
            }
            
        } catch (error) {
            console.error('Failed to get hint:', error);
            this.hintDisplay.textContent = 'Sorry, couldn\'t get a hint right now. Try again!';
        }
    }
    
    /**
     * Toggle chat interface
     */
    toggleChat() {
        if (!this.chatContainer) return;
        
        const isVisible = this.chatContainer.style.display === 'block';
        this.chatContainer.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible && this.chatInput) {
            this.chatInput.focus();
        }
    }
    
    /**
     * Send chat message to AI
     */
    async sendChatMessage() {
        if (!this.chatInput || !this.chatMessages) return;
        
        const message = this.chatInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        this.addChatMessage('user', message);
        
        // Clear input
        this.chatInput.value = '';
        
        // Add to conversation history
        this.conversationHistory.push({
            role: 'user',
            content: message
        });
        
        // Show loading
        this.addChatMessage('ai', '...', true);
        
        try {
            const question = this.questions[this.currentQuestion];
            
            // Get AI response
            const response = await this.apiClient.chatWithAI(
                message,
                question.id,
                this.conversationHistory
            );
            
            // Remove loading message
            const messages = this.chatMessages.querySelectorAll('.chat-message');
            const lastMessage = messages[messages.length - 1];
            if (lastMessage && lastMessage.textContent === '...') {
                lastMessage.remove();
            }
            
            // Add AI response
            this.addChatMessage('ai', response);
            
            // Add to conversation history
            this.conversationHistory.push({
                role: 'assistant',
                content: response
            });
            
        } catch (error) {
            console.error('Chat failed:', error);
            // Remove loading message
            const messages = this.chatMessages.querySelectorAll('.chat-message');
            const lastMessage = messages[messages.length - 1];
            if (lastMessage && lastMessage.textContent === '...') {
                lastMessage.remove();
            }
            this.addChatMessage('ai', 'Sorry, I\'m having trouble connecting. Please try again!');
        }
    }
    
    /**
     * Add message to chat
     */
    addChatMessage(role, text, isLoading = false) {
        if (!this.chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        messageDiv.textContent = text;
        
        if (isLoading) {
            messageDiv.style.fontStyle = 'italic';
            messageDiv.style.opacity = '0.7';
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    /**
     * Update progress bar and text
     */
    updateProgress() {
        const progress = ((this.currentQuestion + 1) / Math.min(this.questions.length, 20)) * 100;
        
        if (this.progressFillEl) {
            this.progressFillEl.style.width = `${progress}%`;
        }
        
        if (this.progressTextEl) {
            this.progressTextEl.textContent = `Question ${this.currentQuestion + 1} of ${Math.min(this.questions.length, 20)}`;
        }
    }
    
    /**
     * Move to next question
     */
    nextQuestion() {
        this.currentQuestion++;
        this.showQuestion();
        
        // Reset next button
        if (this.nextBtn) {
            this.nextBtn.disabled = true;
            this.nextBtn.style.opacity = '0.5';
        }
    }
    
    /**
     * Complete diagnostic and show results
     */
    completeDiagnostic() {
        this.finishDiagnostic();
    }
    
    /**
     * Finish diagnostic test
     */
    async finishDiagnostic() {
        // Stop timer
        clearInterval(this.timerInterval);
        this.isComplete = true;
        
        // Analyze fatigue
        const analysis = this.tracker.analyzeFatigue();
        const report = this.tracker.generateClinicalReport(analysis);
        
        // Save results to backend
        await this.saveResults(report);
        
        // Show results
        this.showResults(report);
    }
    
    /**
     * Save results to backend
     */
    async saveResults(report) {
        try {
            await this.apiClient.saveDiagnosticResults({
                sessionId: this.tracker.sessionId,
                report: report,
                responses: this.tracker.responses
            });
            console.log('Results saved to backend');
        } catch (error) {
            console.error('Failed to save results:', error);
            // Save locally as backup
            localStorage.setItem(
                `winscorr_diagnostic_${this.tracker.sessionId}`,
                JSON.stringify({
                    report,
                    responses: this.tracker.responses,
                    timestamp: Date.now()
                })
            );
        }
    }
    
    /**
     * Show results page
     */
    showResults(report) {
        // Hide test container
        const testContainer = document.getElementById('test-container');
        if (testContainer) {
            testContainer.style.display = 'none';
        }
        
        // Show results container
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            resultsContainer.innerHTML = this.generateResultsHTML(report);
            resultsContainer.style.display = 'block';
        }
        
        // Add event listeners for result buttons
        const signupBtn = document.getElementById('signup-btn');
        if (signupBtn) {
            signupBtn.addEventListener('click', () => {
                window.location.href = '/signup.html';
            });
        }
        
        const dashboardBtn = document.getElementById('dashboard-btn');
        if (dashboardBtn) {
            dashboardBtn.addEventListener('click', () => {
                window.location.href = '/dashboard.html';
            });
        }
        
        const retakeBtn = document.getElementById('retake-btn');
        if (retakeBtn) {
            retakeBtn.addEventListener('click', () => {
                window.location.reload();
            });
        }
    }
    
    /**
     * Generate results HTML
     */
    generateResultsHTML(report) {
        const fatigueColor = report.fatigueDetected ? '#ef4444' : '#10b981';
        
        return `
            <div class="container">
                <div class="results-header">
                    <h1 style="color: #2563eb; margin-bottom: 1rem;">Diagnostic Complete! 🎉</h1>
                    <p style="color: #475569; font-size: 1.125rem;">Your evidence-based assessment is ready</p>
                </div>
                
                <div class="result-card">
                    <h2 style="color: ${fatigueColor}; margin-bottom: 1.5rem; font-size: 1.75rem;">
                        ${report.keyFinding}
                    </h2>
                    
                    <div class="result-metrics">
                        <div class="metric">
                            <div class="metric-label">First Half Accuracy</div>
                            <div class="metric-value" style="color: ${fatigueColor};">${report.dataSummary.firstHalfAccuracy}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Second Half Accuracy</div>
                            <div class="metric-value" style="color: ${fatigueColor};">${report.dataSummary.secondHalfAccuracy}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Performance Change</div>
                            <div class="metric-value" style="color: ${fatigueColor};">${report.dataSummary.accuracyDecline}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Statistical Confidence</div>
                            <div class="metric-value" style="color: #2563eb;">${report.statisticalConfidence.confidenceLevel}</div>
                        </div>
                    </div>
                    
                    <div class="interpretation">
                        <h3 style="color: #0f172a; margin-bottom: 0.75rem; font-size: 1.5rem;">Clinical Interpretation</h3>
                        <p style="color: #475569; line-height: 1.7; font-size: 1.125rem;">${report.interpretation}</p>
                    </div>
                    
                    <div class="recommendations">
                        <h3 style="color: #0f172a; margin-bottom: 0.75rem; font-size: 1.5rem;">Personalized Recommendations</h3>
                        <ul style="color: #475569; padding-left: 1.5rem; font-size: 1.0625rem; line-height: 1.7;">
                            ${report.recommendations.map(rec => `<li style="margin-bottom: 0.5rem;">${rec}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="research-citation">
                        <strong>Research Basis:</strong> ${report.researchBasis.citation}
                    </div>
                </div>
                
                <div class="actions">
                    <button id="signup-btn" class="btn btn-primary btn-lg">
                        <span class="btn-icon">🚀</span>
                        Sign Up for Full Access - $149/month
                    </button>
                    <button id="dashboard-btn" class="btn btn-secondary btn-lg">
                        View Dashboard
                    </button>
                    <button id="retake-btn" class="btn btn-outline btn-lg">
                        Take Another Diagnostic
                    </button>
                </div>
                
                <div class="disclaimer">
                    <strong>Disclaimer:</strong> ${report.disclaimer}
                </div>
            </div>
        `;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('diagnostic')) {
        window.diagnosticFlow = new DiagnosticFlow();
    }
});
