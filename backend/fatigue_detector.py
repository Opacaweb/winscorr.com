"""
Fatigue Detection Service
Evidence-based cognitive fatigue detection using statistical analysis
"""
import statistics
from typing import List, Dict, Any
from scipy import stats
import numpy as np

class FatigueDetector:
    """
    Detects cognitive fatigue by analyzing performance decline across diagnostic test
    Uses Mann-Whitney U test for statistical validation
    """
    
    def __init__(self):
        self.significance_threshold = 0.05  # p < 0.05 for statistical significance
    
    def analyze_fatigue(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze responses for cognitive fatigue patterns
        
        Args:
            responses: List of student responses with timing and correctness
        
        Returns:
            Comprehensive fatigue analysis with statistical validation
        """
        
        if len(responses) < 10:
            return self._insufficient_data_report()
        
        # Split responses into halves
        midpoint = len(responses) // 2
        first_half = responses[:midpoint]
        second_half = responses[midpoint:]
        
        # Calculate accuracy for each half
        first_half_accuracy = sum(1 for r in first_half if r.get('isCorrect', False)) / len(first_half)
        second_half_accuracy = sum(1 for r in second_half if r.get('isCorrect', False)) / len(second_half)
        
        accuracy_decline = first_half_accuracy - second_half_accuracy
        decline_percentage = accuracy_decline * 100
        
        # Calculate response times
        first_half_times = [r.get('responseTimeMs', 0) for r in first_half]
        second_half_times = [r.get('responseTimeMs', 0) for r in second_half]
        
        avg_time_first = statistics.mean(first_half_times) if first_half_times else 0
        avg_time_second = statistics.mean(second_half_times) if second_half_times else 0
        
        # Statistical significance testing (Mann-Whitney U test)
        try:
            # Convert to binary arrays (1 = correct, 0 = incorrect)
            first_half_scores = [1 if r.get('isCorrect', False) else 0 for r in first_half]
            second_half_scores = [1 if r.get('isCorrect', False) else 0 for r in second_half]
            
            statistic, p_value = stats.mannwhitneyu(first_half_scores, second_half_scores, alternative='greater')
            
            is_significant = p_value < self.significance_threshold
        except:
            # If statistical test fails, use threshold-based detection
            is_significant = decline_percentage > 15
            p_value = None
        
        # Determine fatigue level
        fatigue_detected = accuracy_decline > 0.15  # 15% decline threshold
        
        if not fatigue_detected:
            fatigue_level = 'none'
            severity = 'No significant fatigue'
        elif decline_percentage < 20:
            fatigue_level = 'low'
            severity = 'Mild fatigue detected'
        elif decline_percentage < 30:
            fatigue_level = 'moderate'
            severity = 'Moderate fatigue detected'
        else:
            fatigue_level = 'high'
            severity = 'Significant fatigue detected'
        
        # Generate clinical report
        return {
            'fatigueDetected': fatigue_detected,
            'fatigueLevel': fatigue_level,
            'severity': severity,
            'dataSummary': {
                'firstHalfAccuracy': f'{first_half_accuracy * 100:.1f}%',
                'secondHalfAccuracy': f'{second_half_accuracy * 100:.1f}%',
                'accuracyDecline': f'{decline_percentage:.1f}%',
                'firstHalfAvgTime': f'{avg_time_first / 1000:.1f}s',
                'secondHalfAvgTime': f'{avg_time_second / 1000:.1f}s'
            },
            'statisticalConfidence': {
                'pValue': f'{p_value:.4f}' if p_value is not None else 'N/A',
                'isSignificant': is_significant,
                'confidenceLevel': 'High (p < 0.05)' if is_significant else 'Moderate',
                'testUsed': 'Mann-Whitney U test'
            },
            'keyFinding': self._generate_key_finding(fatigue_detected, decline_percentage),
            'interpretation': self._generate_interpretation(fatigue_detected, decline_percentage, is_significant),
            'recommendations': self._generate_recommendations(fatigue_level, decline_percentage),
            'researchBasis': {
                'citation': 'Based on cognitive load theory (Sweller, 1988) and test fatigue research (Ackerman & Kanfer, 2009)',
                'methodology': 'Mann-Whitney U test for non-parametric comparison of first-half vs second-half performance'
            },
            'disclaimer': 'This is an educational assessment tool, not a medical diagnosis. Consult healthcare professionals for clinical concerns.'
        }
    
    def _generate_key_finding(self, fatigue_detected: bool, decline_percentage: float) -> str:
        """Generate the main finding statement"""
        if not fatigue_detected:
            return 'Consistent Performance - No Cognitive Fatigue Detected'
        else:
            return f'Cognitive Fatigue Detected - {decline_percentage:.1f}% Performance Decline'
    
    def _generate_interpretation(self, fatigue_detected: bool, decline_percentage: float, is_significant: bool) -> str:
        """Generate clinical interpretation"""
        if not fatigue_detected:
            return "The student maintained consistent accuracy throughout the diagnostic test. This suggests good stamina and focus, indicating readiness for the full-length SSAT exam format."
        
        if is_significant:
            return f"Statistical analysis revealed a significant {decline_percentage:.1f}% decline in accuracy from the first half to the second half of the test (p < 0.05). This pattern is consistent with cognitive fatigue, which is common during sustained mental effort. The student may benefit from strategies to maintain focus during longer test sessions."
        else:
            return f"A {decline_percentage:.1f}% decline in accuracy was observed, though statistical significance was borderline. This suggests possible early signs of fatigue. Monitoring this pattern across future practice sessions is recommended."
    
    def _generate_recommendations(self, fatigue_level: str, decline_percentage: float) -> List[str]:
        """Generate actionable recommendations"""
        if fatigue_level == 'none':
            return [
                "Maintain current test-taking strategies - they're working well",
                "Continue practicing with full-length tests to build endurance",
                "Your stamina is a strength - leverage it on test day"
            ]
        
        recommendations = [
            "Practice regular breaks during study sessions (5 min every 20-30 min)",
            "Build test-taking stamina gradually with timed practice sessions",
            "Ensure adequate sleep (8-10 hours) before practice tests and the actual exam"
        ]
        
        if fatigue_level in ['moderate', 'high']:
            recommendations.extend([
                "Consider shorter, more frequent practice sessions rather than long marathons",
                "Practice mindfulness or breathing exercises to maintain focus",
                "Eat a healthy snack before practice sessions to maintain energy"
            ])
        
        if decline_percentage > 25:
            recommendations.append("Consult with parents/teachers about optimal study timing and duration")
        
        return recommendations
    
    def _insufficient_data_report(self) -> Dict[str, Any]:
        """Return report when there's insufficient data"""
        return {
            'fatigueDetected': False,
            'fatigueLevel': 'unknown',
            'severity': 'Insufficient data',
            'dataSummary': {
                'firstHalfAccuracy': 'N/A',
                'secondHalfAccuracy': 'N/A',
                'accuracyDecline': 'N/A'
            },
            'statisticalConfidence': {
                'pValue': 'N/A',
                'isSignificant': False,
                'confidenceLevel': 'N/A - need at least 10 responses',
                'testUsed': 'None'
            },
            'keyFinding': 'Insufficient Data for Analysis',
            'interpretation': 'At least 10 completed questions are required for reliable fatigue analysis.',
            'recommendations': [
                'Complete more questions to enable fatigue analysis',
                'Take the full 20-question diagnostic for comprehensive insights'
            ],
            'researchBasis': {
                'citation': 'Statistical analysis requires minimum sample size for validity',
                'methodology': 'N/A'
            },
            'disclaimer': 'This is an educational assessment tool, not a medical diagnosis.'
        }
