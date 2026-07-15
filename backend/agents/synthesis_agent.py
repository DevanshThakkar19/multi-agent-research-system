"""
Synthesis Agent
Combines multiple sources and generates comprehensive reports.
"""

from typing import Dict, Any, List
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from core.agent_base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class SynthesisAgent(BaseAgent):
    """
    Synthesizes information from multiple sources (web, documents, etc.)
    into comprehensive, well-structured reports.
    """
    
    def __init__(self, llm_model: str = "gpt-4o"):
        super().__init__(
            name="synthesis_agent",
            description="Combines findings from multiple sources into comprehensive reports"
        )
        self.llm = ChatOpenAI(model=llm_model, temperature=0)
        
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """
        Synthesize findings from multiple sources
        
        Args:
            task: Must contain 'query' and 'results' with findings from other agents
            context: Optional additional context
            
        Returns:
            AgentResult with synthesized report
        """
        query = task.get("query", "")
        results = task.get("results", {})
        
        if not query:
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error="No query provided for synthesis"
            )
        
        if not results:
            # If no results provided, generate a basic answer from the query itself
            logger.info("No results provided, generating basic answer from query")
            try:
                basic_answer = await self._generate_basic_answer(query)
                return AgentResult(
                    success=True,
                    data={
                        "query": query,
                        "report": {
                            "summary": basic_answer,
                            "full_report": basic_answer,
                            "sections": [],
                            "citations": []
                        },
                        "sources": [],
                        "key_points": [basic_answer[:200]]
                    },
                    metadata={
                        "num_sources": 0,
                        "report_length": len(basic_answer),
                        "note": "Generated without external sources"
                    }
                )
            except Exception as e:
                logger.error(f"Failed to generate basic answer: {e}")
                return AgentResult(
                    success=False,
                    data=None,
                    metadata={},
                    error=f"No results to synthesize and failed to generate basic answer: {str(e)}"
                )
        
        try:
            # Synthesize the findings
            report = await self._synthesize_findings(query, results)
            
            return AgentResult(
                success=True,
                data={
                    "query": query,
                    "report": report,
                    "sources": self._extract_all_sources(results),
                    "key_points": self._extract_key_points(report)
                },
                metadata={
                    "num_sources": len(self._extract_all_sources(results)),
                    "report_length": len(report.get("summary", ""))
                }
            )
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error=str(e)
            )
    
    async def _synthesize_findings(self, query: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize findings from multiple agents"""
        
        # Format results for synthesis
        formatted_results = self._format_results_for_synthesis(results)
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research synthesizer. Combine information from multiple 
            sources into a comprehensive, well-structured report. Ensure accuracy, coherence, and 
            proper attribution of sources."""),
            ("human", """Research Query: {query}

Findings from Multiple Sources:
{findings}

Create a comprehensive research report that:
1. Provides a clear executive summary
2. Synthesizes information from all sources
3. Identifies key themes and patterns
4. Highlights important facts and insights
5. Notes any contradictions or gaps
6. Includes proper source attribution

Format the report with clear sections and citations."""),
        ])
        
        prompt = prompt_template.format_messages(
            query=query,
            findings=formatted_results
        )
        
        response = await self.llm.ainvoke(prompt)
        
        # Parse response into structured report
        report = {
            "summary": response.content[:500],  # First 500 chars as summary
            "full_report": response.content,
            "sections": self._parse_sections(response.content),
            "citations": self._extract_citations_from_report(response.content)
        }
        
        return report
    
    def _format_results_for_synthesis(self, results: Dict[str, Any]) -> str:
        """Format agent results for synthesis prompt"""
        formatted = []
        
        for agent_name, result_data in results.items():
            if isinstance(result_data, dict):
                findings = result_data.get("findings", result_data.get("data", {}))
                formatted.append(f"\n=== {agent_name.upper()} FINDINGS ===\n")
                formatted.append(str(findings))
            else:
                formatted.append(f"\n=== {agent_name.upper()} ===\n{str(result_data)}")
        
        return "\n".join(formatted)
    
    def _parse_sections(self, report: str) -> List[Dict[str, str]]:
        """Parse report into sections"""
        sections = []
        lines = report.split("\n")
        current_section = {"title": "Introduction", "content": []}
        
        for line in lines:
            if line.strip().startswith("#") or (line.strip() and line[0].isupper() and len(line) < 100):
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {"title": line.strip(), "content": []}
            else:
                current_section["content"].append(line)
        
        if current_section["content"]:
            sections.append(current_section)
        
        return sections
    
    def _extract_citations_from_report(self, report: str) -> List[str]:
        """Extract citations mentioned in the report"""
        import re
        # Look for URL patterns
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, report)
        return list(set(urls))
    
    def _extract_all_sources(self, results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract all sources from agent results"""
        sources = []
        
        for agent_name, result_data in results.items():
            if isinstance(result_data, dict):
                citations = result_data.get("citations", [])
                sources_list = result_data.get("sources", [])
                
                if citations:
                    sources.extend(citations)
                elif sources_list:
                    for src in sources_list:
                        if isinstance(src, dict):
                            sources.append(src)
                        else:
                            sources.append({"url": str(src), "type": "web"})
        
        return sources
    
    def _extract_key_points(self, report: Dict[str, Any]) -> List[str]:
        """Extract key points from the report"""
        summary = report.get("summary", "")
        # Simple extraction - in production, use more sophisticated parsing
        sentences = summary.split(". ")
        return [s.strip() + "." for s in sentences[:5] if len(s) > 20]
    
    async def _generate_basic_answer(self, query: str) -> str:
        """Generate a basic answer when no sources are available"""
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful research assistant. Provide a comprehensive answer 
            to the user's question based on your knowledge."""),
            ("human", """Please provide a comprehensive answer to the following question:

{query}

Provide a well-structured answer with:
1. A clear definition or explanation
2. Key points and details
3. Relevant context or examples
4. A brief conclusion

Format your response as a clear, informative answer."""),
        ])
        
        prompt = prompt_template.format_messages(query=query)
        response = await self.llm.ainvoke(prompt)
        return response.content

