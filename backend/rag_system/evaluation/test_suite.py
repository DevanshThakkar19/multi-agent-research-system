"""Test suite for evaluation framework."""
from typing import List, Dict
from dataclasses import dataclass

from .metrics import QueryType
from .evaluator import RAGEvaluator


@dataclass
class RAGTestCase:
    """A single test case for RAG evaluation."""
    query_id: str
    query: str
    query_type: QueryType
    expected_answer: str
    ground_truth_contexts: List[str]
    metadata: Dict = None


class EvaluationTestSuite:
    """Test suite for evaluating the RAG system."""
    
    def __init__(self):
        self.test_cases: List[RAGTestCase] = []
        self.evaluator = RAGEvaluator()
    
    def add_test_case(self, test_case: RAGTestCase):
        """Add a test case to the suite."""
        self.test_cases.append(test_case)
    
    def create_minimal_test_suite(self):
        """Create a minimal test suite with sample queries."""
        # Lookup query
        self.add_test_case(RAGTestCase(
            query_id="lookup_001",
            query="What is the capital of France?",
            query_type=QueryType.LOOKUP,
            expected_answer="The capital of France is Paris.",
            ground_truth_contexts=["France", "Paris", "capital"]
        ))
        
        # Summarization query
        self.add_test_case(RAGTestCase(
            query_id="summarization_001",
            query="Summarize the main points about machine learning.",
            query_type=QueryType.SUMMARIZATION,
            expected_answer="Machine learning is a subset of artificial intelligence...",
            ground_truth_contexts=["machine learning", "AI", "algorithms"]
        ))
        
        # Semantic linkages query
        self.add_test_case(RAGTestCase(
            query_id="semantic_001",
            query="How are neural networks related to deep learning?",
            query_type=QueryType.SEMANTIC_LINKAGES,
            expected_answer="Neural networks are the foundation of deep learning...",
            ground_truth_contexts=["neural networks", "deep learning", "relationships"]
        ))
        
        # Reasoning query
        self.add_test_case(RAGTestCase(
            query_id="reasoning_001",
            query="If a company's revenue increased by 20% and costs increased by 10%, what happened to profit?",
            query_type=QueryType.REASONING,
            expected_answer="Profit increased because revenue growth exceeded cost growth...",
            ground_truth_contexts=["revenue", "costs", "profit", "calculation"]
        ))
    
    def get_test_cases(self) -> List[RAGTestCase]:
        """Get all test cases."""
        return self.test_cases
    
    def get_test_cases_by_type(self, query_type: QueryType) -> List[RAGTestCase]:
        """Get test cases filtered by query type."""
        return [tc for tc in self.test_cases if tc.query_type == query_type]

