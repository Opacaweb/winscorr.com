"""
AI Tutor Service - Claude Sonnet 4 Powered Intelligence
Provides personalized explanations, hints, and conversational tutoring
"""
import os
from anthropic import Anthropic
from typing import Dict, List, Optional, Any
import json

class AITutorService:
    def __init__(self):
        """Initialize AI Tutor with Claude Sonnet 4"""
        api_key = os.getenv('ANTHROPIC_API_KEY', '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')
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"  # Latest Sonnet 4
        
        # System prompt for tutoring
        self.tutor_system_prompt = """You are an expert SSAT math tutor for middle school students (grades 6-8). 

Your teaching style:
- Patient, encouraging, and supportive
- Explain concepts clearly using grade-appropriate language
- Use concrete examples and visual descriptions
- Break down complex problems into manageable steps
- Celebrate student effort and progress
- Never give away the answer directly - guide students to discover it

Focus areas:
- Algebra (equations, expressions, variables)
- Fractions and decimals
- Geometry (perimeter, area, angles)
- Percentages and ratios
- Word problems and logical reasoning
- Number theory

Remember: You're helping students BUILD UNDERSTANDING, not just get correct answers."""

    def generate_personalized_explanation(
        self,
        question_data: Dict[str, Any],
        student_answer: str,
        correct_answer: str,
        student_performance: Optional[Dict] = None,
        response_time_ms: Optional[int] = None,
        fatigue_level: str = 'none'
    ) -> str:
        """
        Generate personalized explanation tailored to the student's specific situation
        
        Args:
            question_data: Question details from database
            student_answer: What the student selected
            correct_answer: The correct answer
            student_performance: Student's overall performance data
            response_time_ms: How long they took to answer
            fatigue_level: Detected fatigue level (none, low, moderate, high)
        
        Returns:
            Personalized explanation text
        """
        
        # Build context about the student
        context_parts = []
        
        # Concept mastery
        if student_performance and 'by_concept' in student_performance:
            concept = question_data.get('concept', '')
            for c in student_performance['by_concept']:
                if c['concept'] == concept:
                    accuracy = c['accuracy'] * 100
                    context_parts.append(f"Student's {concept} accuracy: {accuracy:.1f}%")
                    break
        
        # Response time analysis
        if response_time_ms:
            time_sec = response_time_ms / 1000
            if time_sec < 10:
                context_parts.append("Student answered very quickly (possibly rushing)")
            elif time_sec > 90:
                context_parts.append("Student took extra time with this problem")
        
        # Fatigue context
        if fatigue_level and fatigue_level != 'none':
            context_parts.append(f"Student showing signs of {fatigue_level} cognitive fatigue")
        
        context_str = " | ".join(context_parts) if context_parts else "First attempt at this concept"
        
        # Construct the prompt
        prompt = f"""A student just answered this SSAT math question incorrectly:

**Question:** {question_data['question_text']}

**Options:** {', '.join(question_data.get('options', []))}

**Student's Answer:** {student_answer}
**Correct Answer:** {correct_answer}

**Concept:** {question_data.get('concept', 'general math')}
**Difficulty:** {question_data.get('difficulty', 'medium')}

**Student Context:** {context_str}

**Your Task:**
Generate a personalized explanation that:
1. Acknowledges their effort positively
2. Identifies WHY they might have chosen {student_answer}
3. Explains the correct approach step-by-step
4. Uses the concept name explicitly to reinforce learning
5. Ends with an encouraging note

Keep it concise (3-4 short paragraphs), clear, and age-appropriate for middle school students."""

        try:
            # Call Claude Sonnet 4
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                system=self.tutor_system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"AI Tutor Error: {e}")
            # Fallback to basic explanation if AI fails
            return self._fallback_explanation(question_data, student_answer, correct_answer)
    
    def generate_hint(
        self,
        question_data: Dict[str, Any],
        hint_level: int = 1
    ) -> str:
        """
        Generate progressive hints without revealing the answer
        
        Args:
            question_data: Question details
            hint_level: 1 = gentle nudge, 2 = stronger guidance, 3 = almost giving answer
        
        Returns:
            Hint text
        """
        
        hint_instructions = {
            1: "Give a very gentle hint about what concept or approach to consider. Don't reveal any steps.",
            2: "Provide a hint about the first step or what to set up. Still don't solve it.",
            3: "Give a strong hint that guides them very close to the answer, but they still need to do the final calculation themselves."
        }
        
        prompt = f"""A student is stuck on this SSAT math question:

**Question:** {question_data['question_text']}

**Options:** {', '.join(question_data.get('options', []))}

**Concept:** {question_data.get('concept', 'general math')}

**Hint Level {hint_level}:** {hint_instructions[hint_level]}

Generate the appropriate hint now. Keep it brief (1-2 sentences) and encouraging."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.7,
                system=self.tutor_system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"AI Hint Error: {e}")
            return self._fallback_hint(question_data, hint_level)
    
    def chat(
        self,
        user_message: str,
        conversation_history: List[Dict] = None,
        context: Dict = None
    ) -> str:
        """
        Conversational AI tutoring - student can ask follow-up questions
        
        Args:
            user_message: Student's question/message
            conversation_history: Previous messages in this conversation
            context: Additional context (question_id, concept, etc.)
        
        Returns:
            AI tutor's response
        """
        
        # Build conversation context
        messages = []
        
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Add context if available
        system_prompt = self.tutor_system_prompt
        if context and context.get('concept'):
            system_prompt += f"\n\nCurrent topic: {context['concept']}"
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                system=system_prompt,
                messages=messages
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"AI Chat Error: {e}")
            return "I'm having trouble connecting right now. Could you try asking your question again?"
    
    def generate_progress_insights(self, progress_report: Dict) -> str:
        """
        Generate AI insights about student's overall progress
        
        Args:
            progress_report: Complete progress report from tutoring service
        
        Returns:
            AI-generated insights and encouragement
        """
        
        prompt = f"""Analyze this student's SSAT math progress and provide personalized insights:

**Overall Accuracy:** {progress_report.get('overall_accuracy', 0)}%
**Total Questions:** {progress_report.get('total_questions', 0)}
**Strongest Concepts:** {', '.join(progress_report.get('strongest_concepts', []))}
**Weakest Concepts:** {', '.join(progress_report.get('weakest_concepts', []))}

**Performance by Concept:**
{json.dumps(progress_report.get('mastery_by_concept', []), indent=2)}

Provide:
1. A positive observation about their strengths
2. One specific insight about their learning pattern
3. Actionable advice for their weakest area
4. An encouraging note about their potential

Keep it warm, specific, and motivating (3-4 paragraphs)."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.8,
                system=self.tutor_system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"AI Insights Error: {e}")
            return "Keep up the great work! You're making steady progress."
    
    def generate_study_plan(self, recommendations: Dict) -> Dict:
        """
        Generate AI-powered personalized study plan
        
        Args:
            recommendations: Recommendations from tutoring service
        
        Returns:
            Detailed study plan with AI suggestions
        """
        
        prompt = f"""Create a personalized weekly study plan for a middle school student based on:

**Focus Areas:** {', '.join(recommendations.get('focus_areas', []))}
**Current Recommendations:** {', '.join(recommendations.get('specific_recommendations', []))}

Generate a structured 5-day study plan with:
- Daily focus (15-20 min per day)
- Specific skills to practice each day
- Variety to keep it engaging
- Balance between weak areas and maintaining strengths

Format as JSON with this structure:
{{
  "weekly_theme": "brief description",
  "daily_plan": [
    {{"day": "Monday", "focus": "concept", "activity": "what to do", "duration": "15-20 min"}},
    ...
  ],
  "success_tip": "one encouraging tip"
}}"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.8,
                system=self.tutor_system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Try to parse as JSON
            response_text = message.content[0].text
            try:
                return json.loads(response_text)
            except:
                # If not valid JSON, return structured text
                return {
                    "plan_text": response_text,
                    "format": "text"
                }
            
        except Exception as e:
            print(f"AI Study Plan Error: {e}")
            return {
                "weekly_theme": "Focus on your weakest concepts",
                "daily_plan": [],
                "success_tip": "Consistency is key - practice a little bit each day!"
            }
    
    # ========================================================================
    # FALLBACK METHODS (if AI fails)
    # ========================================================================
    
    def _fallback_explanation(self, question_data: Dict, student_answer: str, correct_answer: str) -> str:
        """Fallback explanation if AI service fails"""
        explanation = question_data.get('explanation', '')
        
        return f"""Great effort on this problem! Let's work through it together.

You selected {student_answer}, but the correct answer is {correct_answer}.

{explanation}

Keep practicing - you're learning valuable {question_data.get('concept', 'math')} skills!"""
    
    def _fallback_hint(self, question_data: Dict, hint_level: int) -> str:
        """Fallback hint if AI service fails"""
        hints = {
            1: f"Think about what {question_data.get('concept', 'concept')} means in this problem.",
            2: f"Try breaking down the problem into smaller steps. What do you need to find first?",
            3: f"Look at the numbers carefully. What operation do you need to use?"
        }
        return hints.get(hint_level, "Take your time and read the question carefully.")
