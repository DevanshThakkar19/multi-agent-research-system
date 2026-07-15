"""
Validator Agent
Cross-references facts, ensures consistency, and validates information.
"""

from typing import Dict, Any, List
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from core.agent_base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    """
    Validates facts, checks for consistency across sources, and identifies contradictions.
    Ensures the final research output is accurate and reliable.
    """
    
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        super().__init__(
            name="validator_agent",
            description="Validates facts, checks consistency, and identifies contradictions across sources"
        )
        self.llm = ChatOpenAI(model=llm_model, temperature=0)
        
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """
        Validate research findings for accuracy and consistency
        
        Args:
            task: Must contain 'synthesis' or 'results' with findings to validate
            context: Optional context about the research query
            
        Returns:
            AgentResult with validation results
        """
        synthesis = task.get("synthesis") or task.get("results", {})
        
        if not synthesis:
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error="No synthesis or results provided for validation"
            )
        
        try:
            # Perform validation
            validation = await self._validate_findings(synthesis, context)
            
            return AgentResult(
                success=True,
                data={
                    "validation": validation,
                    "consistency_score": validation.get("consistency_score", 0.0),
                    "issues": validation.get("issues", []),
                    "recommendations": validation.get("recommendations", [])
                },
                metadata={
                    "num_issues": len(validation.get("issues", [])),
                    "validation_status": "passed" if validation.get("consistency_score", 0) > 0.7 else "needs_review"
                }
            )
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error=str(e)
            )
    
    async def _validate_findings(
        self, 
        synthesis: Dict[str, Any], 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Validate findings for consistency and accuracy"""
        
        report = synthesis.get("report", {})
        full_report = report.get("full_report", report.get("summary", ""))
        sources = synthesis.get("sources", [])
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a fact-checker and consistency validator. Analyze research findings 
            for accuracy, consistency, and potential contradictions. Identify any issues and provide 
            recommendations."""),
            ("human", """Research Report to Validate:
{report}

Sources:
{sources}

Analyze this research report and:
1. Check for factual consistency across sources
2. Identify any contradictions or conflicting information
3. Flag any unsupported claims
4. Assess overall reliability
5. Provide specific recommendations for improvement

Provide a validation report with:
- Consistency score (0-1)
- List of issues found
- Recommendations for addressing issues"""),
        ])
        
        sources_str = "\n".join([str(s) for s in sources[:10]])  # Limit sources
        
        prompt = prompt_template.format_messages(
            report=full_report[:2000],  # Limit report length
            sources=sources_str
        )
        
        response = await self.llm.ainvoke(prompt)
        
        # Parse validation response
        validation = {
            "consistency_score": self._extract_consistency_score(response.content),
            "issues": self._extract_issues(response.content),
            "recommendations": self._extract_recommendations(response.content),
            "validation_notes": response.content
        }
        
        return validation
    
    def _extract_consistency_score(self, validation_text: str) -> float:
        """Extract consistency score from validation text"""
        import re
        # Look for score patterns like "0.8", "80%", "8/10"
        score_patterns = [
            r'consistency[:\s]+([0-9.]+)',
            r'score[:\s]+([0-9.]+)',
            r'([0-9.]+)\s*out\s*of\s*1',
            r'([0-9]+)%'
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, validation_text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                if score > 1:
                    score = score / 100  # Convert percentage
                return min(1.0, max(0.0, score))
        
        # Default score based on text analysis
        if "high" in validation_text.lower() or "good" in validation_text.lower():
            return 0.8
        elif "medium" in validation_text.lower() or "moderate" in validation_text.lower():
            return 0.6
        else:
            return 0.5
    
    def _extract_issues(self, validation_text: str) -> List[Dict[str, str]]:
        """Extract issues from validation text"""
        issues = []
        lines = validation_text.split("\n")
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ["issue", "problem", "contradiction", "inconsistency", "error"]):
                issues.append({
                    "type": "consistency" if "consistency" in line_lower else "factual",
                    "description": line.strip(),
                    "severity": "high" if any(w in line_lower for w in ["major", "critical", "significant"]) else "medium"
                })
        
        return issues[:5]  # Limit to 5 issues
    
    def _extract_recommendations(self, validation_text: str) -> List[str]:
        """Extract recommendations from validation text"""
        recommendations = []
        lines = validation_text.split("\n")
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ["recommend", "suggest", "should", "consider"]):
                recommendations.append(line.strip())
        
        return recommendations[:5]  # Limit to 5 recommendations

