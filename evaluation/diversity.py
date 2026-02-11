from typing import List, Dict
import math
from collections import Counter


class DiversityEvaluator:
    """
    Evaluates the diversity of reactions to media items.
    Provides various metrics to measure how diverse the responses are.
    """
    
    @staticmethod
    def calculate_lexical_diversity(texts: List[str]) -> float:
        """
        Calculate lexical diversity (Type-Token Ratio) across multiple texts.
        
        Args:
            texts: List of text strings to analyze.
            
        Returns:
            Lexical diversity score between 0.0 and 1.0.
        """
        if not texts:
            return 0.0
        
        # Combine all texts and tokenize
        all_words = []
        for text in texts:
            words = text.lower().split()
            all_words.extend(words)
        
        if not all_words:
            return 0.0
        
        # Type-Token Ratio: unique words / total words
        unique_words = len(set(all_words))
        total_words = len(all_words)
        
        return min(unique_words / total_words, 1.0)
    
    @staticmethod
    def calculate_length_diversity(texts: List[str]) -> float:
        """
        Calculate diversity based on variation in response lengths.
        Uses coefficient of variation (CV).
        
        Args:
            texts: List of text strings to analyze.
            
        Returns:
            Length diversity score between 0.0 and 1.0.
        """
        if not texts or len(texts) < 2:
            return 0.0
        
        lengths = [len(text.split()) for text in texts]
        
        if not lengths:
            return 0.0
        
        mean_length = sum(lengths) / len(lengths)
        
        if mean_length == 0:
            return 0.0
        
        # Calculate standard deviation
        variance = sum((x - mean_length) ** 2 for x in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        
        # Coefficient of variation
        cv = std_dev / mean_length
        
        # Normalize to 0-1 range (CV can be > 1, so we cap it)
        return min(cv, 1.0)
    
    @staticmethod
    def calculate_semantic_diversity(reactions: List[Dict]) -> float:
        """
        Calculate semantic diversity based on different reaction types/patterns.
        
        This is a heuristic approach based on identifying different patterns
        in the reactions (questions, agreement, disagreement, neutral commentary).
        
        Args:
            reactions: List of reaction events with 'content' field.
            
        Returns:
            Semantic diversity score between 0.0 and 1.0.
        """
        if not reactions:
            return 0.0
        
        patterns = {
            'question': ['?', 'what', 'why', 'how', 'when', 'where', 'who'],
            'agreement': ['agree', 'yes', 'true', 'exactly', 'right', 'correct'],
            'disagreement': ['disagree', 'no', 'wrong', 'but', 'however', 'although'],
            'excitement': ['!', 'amazing', 'wow', 'great', 'excellent', 'fantastic'],
            'analytical': ['because', 'therefore', 'thus', 'analysis', 'consider'],
        }
        
        pattern_counts = {pattern: 0 for pattern in patterns}
        
        for reaction in reactions:
            content = reaction.get('content', '').lower()
            
            for pattern_name, keywords in patterns.items():
                if any(keyword in content for keyword in keywords):
                    pattern_counts[pattern_name] += 1
        
        # Calculate entropy of pattern distribution
        total = sum(pattern_counts.values())
        
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in pattern_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        # Normalize by maximum possible entropy (log2 of number of patterns)
        max_entropy = math.log2(len(patterns))
        
        return min(entropy / max_entropy, 1.0) if max_entropy > 0 else 0.0
    
    @staticmethod
    def calculate_overall_diversity(reactions: List[Dict]) -> float:
        """
        Calculate overall diversity score combining multiple metrics.
        
        Args:
            reactions: List of reaction events with 'content' field.
            
        Returns:
            Overall diversity score between 0.0 and 1.0.
        """
        if not reactions:
            return 0.0
        
        texts = [r.get('content', '') for r in reactions]
        
        lexical = DiversityEvaluator.calculate_lexical_diversity(texts)
        length = DiversityEvaluator.calculate_length_diversity(texts)
        semantic = DiversityEvaluator.calculate_semantic_diversity(reactions)
        
        # Weighted average
        return (lexical * 0.4 + length * 0.2 + semantic * 0.4)
