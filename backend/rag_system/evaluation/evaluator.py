"""Main evaluator for RAG system."""
import time
from typing import List, Dict, Optional
from deepeval import evaluate
from deepeval.metrics import HallucinationMetric, AnswerRelevancyMetric
from loguru import logger

from .metrics import EvaluationMetrics, QueryType, MetricCalculator
from ..utils.config import settings


class RAGEvaluator:
    """Evaluator for RAG system performance."""
    
    def __init__(self):
        self.metrics_history: List[EvaluationMetrics] = []
        self.calculator = MetricCalculator()
    
    def evaluate_query(
        self,
        query_id: str,
        query: str,
        query_type: QueryType,
        retrieved_contexts: List[str],
        relevant_contexts: List[str],
        answer: str,
        expected_answer: Optional[str] = None,
        ground_truth_contexts: Optional[List[str]] = None
    ) -> EvaluationMetrics:
        """
        Evaluate a single query.
        
        Args:
            query_id: Unique identifier for the query
            query: The user query
            query_type: Type of query
            retrieved_contexts: Contexts retrieved by the system
            relevant_contexts: Contexts marked as relevant
            answer: Generated answer
            expected_answer: Expected answer (for hallucination detection)
            ground_truth_contexts: Ground truth relevant contexts
        
        Returns:
            EvaluationMetrics object
        """
        start_time = time.time()
        
        # Calculate precision and recall
        if ground_truth_contexts:
            precision = self.calculator.calculate_precision(
                retrieved_contexts, ground_truth_contexts
            )
            recall = self.calculator.calculate_recall(
                retrieved_contexts, ground_truth_contexts
            )
        else:
            # Fallback: use relevant_contexts if ground truth not available
            precision = self.calculator.calculate_precision(
                retrieved_contexts, relevant_contexts
            )
            recall = self.calculator.calculate_recall(
                retrieved_contexts, relevant_contexts
            )
        
        # Calculate hallucination rate using DeepEval
        hallucination_rate = 0.0
        if expected_answer:
            try:
                from deepeval.test_case import LLMTestCase
                # Context should be a list of strings, not a single string
                context_list = retrieved_contexts if isinstance(retrieved_contexts, list) else [retrieved_contexts] if retrieved_contexts else []
                test_case = LLMTestCase(
                    input=query,
                    actual_output=answer,
                    expected_output=expected_answer,
                    context=context_list
                )
                hallucination_metric = HallucinationMetric(
                    threshold=0.5
                )
                score = hallucination_metric.measure(test_case)
                hallucination_rate = 1.0 - score
            except Exception as e:
                logger.warning(f"Hallucination detection failed: {e}")
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Create metrics object
        metrics = EvaluationMetrics(
            query_id=query_id,
            query=query,
            query_type=query_type,
            precision=precision,
            recall=recall,
            latency_ms=latency_ms,
            hallucination_rate=hallucination_rate,
            retrieved_contexts=len(retrieved_contexts),
            relevant_contexts=len(relevant_contexts)
        )
        
        self.metrics_history.append(metrics)
        logger.info(f"Evaluated query {query_id}: precision={precision:.3f}, recall={recall:.3f}")
        
        return metrics
    
    def get_aggregate_metrics(self) -> Dict:
        """Get aggregate metrics across all evaluations."""
        if not self.metrics_history:
            return {}
        
        return {
            "total_queries": len(self.metrics_history),
            "avg_precision": sum(m.precision for m in self.metrics_history) / len(self.metrics_history),
            "avg_recall": sum(m.recall for m in self.metrics_history) / len(self.metrics_history),
            "avg_latency_ms": sum(m.latency_ms for m in self.metrics_history) / len(self.metrics_history),
            "avg_hallucination_rate": sum(m.hallucination_rate for m in self.metrics_history) / len(self.metrics_history),
            "metrics_by_query_type": self._get_metrics_by_query_type()
        }
    
    def _get_metrics_by_query_type(self) -> Dict:
        """Get metrics grouped by query type."""
        by_type = {}
        for query_type in QueryType:
            type_metrics = [m for m in self.metrics_history if m.query_type == query_type]
            if type_metrics:
                by_type[query_type.value] = {
                    "count": len(type_metrics),
                    "avg_precision": sum(m.precision for m in type_metrics) / len(type_metrics),
                    "avg_recall": sum(m.recall for m in type_metrics) / len(type_metrics),
                    "avg_latency_ms": sum(m.latency_ms for m in type_metrics) / len(type_metrics)
                }
        return by_type

