"""Evaluation metrics and query type definitions."""
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


class QueryType(Enum):
    """Types of queries supported by the system."""
    LOOKUP = "lookup"  # Direct factual queries
    SUMMARIZATION = "summarization"  # Content summarization requests
    SEMANTIC_LINKAGES = "semantic_linkages"  # Relationship and connection queries
    REASONING = "reasoning"  # Multi-step reasoning queries


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""
    query_id: str
    query: str
    query_type: QueryType
    precision: float
    recall: float
    latency_ms: float
    hallucination_rate: float
    retrieved_contexts: int
    relevant_contexts: int
    answer_quality_score: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "query_id": self.query_id,
            "query": self.query,
            "query_type": self.query_type.value,
            "precision": self.precision,
            "recall": self.recall,
            "latency_ms": self.latency_ms,
            "hallucination_rate": self.hallucination_rate,
            "retrieved_contexts": self.retrieved_contexts,
            "relevant_contexts": self.relevant_contexts,
            "answer_quality_score": self.answer_quality_score,
            "timestamp": self.timestamp.isoformat()
        }


class MetricCalculator:
    """Calculate evaluation metrics."""
    
    @staticmethod
    def calculate_precision(retrieved: List[str], relevant: List[str]) -> float:
        """Calculate precision: relevant retrieved / total retrieved."""
        if not retrieved:
            return 0.0
        
        # Use fuzzy matching for better precision calculation
        # This handles cases where content might be truncated or slightly different
        relevant_retrieved = 0
        for ret_item in retrieved:
            ret_lower = ret_item.lower().strip()
            # Check if this retrieved item matches any relevant item
            for rel_item in relevant:
                rel_lower = rel_item.lower().strip()
                # Exact match or substring match (one contains the other)
                if ret_lower == rel_lower or ret_lower in rel_lower or rel_lower in ret_lower:
                    relevant_retrieved += 1
                    break
                # Check for substantial overlap (at least 50% of shorter string)
                min_len = min(len(ret_lower), len(rel_lower))
                if min_len > 50:  # Only for longer strings
                    # Check first 200 chars for overlap
                    ret_prefix = ret_lower[:200]
                    rel_prefix = rel_lower[:200]
                    if ret_prefix in rel_prefix or rel_prefix in ret_prefix:
                        relevant_retrieved += 1
                        break
        
        return relevant_retrieved / len(retrieved) if retrieved else 0.0
    
    @staticmethod
    def calculate_recall(retrieved: List[str], relevant: List[str]) -> float:
        """Calculate recall: relevant retrieved / total relevant."""
        if not relevant:
            return 0.0
        relevant_retrieved = len(set(retrieved) & set(relevant))
        return relevant_retrieved / len(relevant)
    
    @staticmethod
    def calculate_f1(precision: float, recall: float) -> float:
        """Calculate F1 score."""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

