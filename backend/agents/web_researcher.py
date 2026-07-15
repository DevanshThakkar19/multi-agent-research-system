"""
Web Researcher Agent
Performs autonomous web searches, fact-checking, and citation gathering.
"""

from typing import Dict, Any, List
import logging
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
import os

from core.agent_base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class WebResearcherAgent(BaseAgent):
    """
    Autonomous web researcher that searches, gathers information, and collects citations.
    Uses web search APIs to find relevant information.
    """
    
    def __init__(self, llm_model: str = "gpt-4o-mini", search_api: str = "tavily"):
        super().__init__(
            name="web_researcher",
            description="Searches the web for information, gathers facts, and collects citations"
        )
        self.llm = ChatOpenAI(model=llm_model, temperature=0)
        self.search_api = search_api
        self.search_tool = self._create_search_tool()
        
    def _create_search_tool(self) -> Tool:
        """Create web search tool based on available API"""
        # Try Tavily first, fallback to mock
        tavily_key = os.getenv("TAVILY_API_KEY")
        
        if tavily_key and tavily_key != "your_tavily_api_key_here":
            try:
                from tavily import TavilyClient
                tavily_client = TavilyClient(api_key=tavily_key)
                
                def search_web(query: str) -> str:
                    """Search the web using Tavily API"""
                    try:
                        results = tavily_client.search(
                            query=query, 
                            max_results=10,
                            search_depth="advanced",
                            include_answer=True,
                            include_raw_content=False
                        )
                        
                        formatted_results = []
                        for result in results.get("results", []):
                            formatted_results.append({
                                "title": result.get("title", ""),
                                "url": result.get("url", ""),
                                "content": result.get("content", "")[:500],  # Limit content length
                                "score": result.get("score", 0),
                                "published_date": result.get("published_date", "")
                            })
                        
                        # Include answer if available
                        if results.get("answer"):
                            formatted_results.insert(0, {
                                "title": "Direct Answer",
                                "url": "",
                                "content": results.get("answer", ""),
                                "score": 1.0,
                                "type": "answer"
                            })
                        
                        return str(formatted_results)
                    except Exception as e:
                        logger.error(f"Tavily search failed: {e}")
                        # Fallback to basic search
                        try:
                            basic_results = tavily_client.search(query=query, max_results=5)
                            return str([{"title": r.get("title", ""), "url": r.get("url", "")} 
                                      for r in basic_results.get("results", [])])
                        except:
                            return f"Search error: {str(e)}"
                
                logger.info("Tavily API initialized successfully")
                return Tool(
                    name="web_search",
                    description="Search the web for current information and facts using Tavily API",
                    func=search_web
                )
            except ImportError:
                logger.warning("Tavily package not installed. Install with: pip install tavily-python")
            except Exception as e:
                logger.warning(f"Tavily initialization failed: {e}")
        
        # Fallback: Use LLM to generate web research summary (no actual search)
        logger.info("No Tavily API key found, using LLM-based research summary")
        return Tool(
            name="web_search",
            description="Search the web (LLM-based summary)",
            func=lambda q: f"Web research summary for: {q} (Note: Actual web search requires Tavily API key)"
        )
    
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """
        Perform web research on the given query
        
        Args:
            task: Must contain 'query' or 'description' with research topic
            context: Optional context about what to focus on
            
        Returns:
            AgentResult with research findings and citations
        """
        query = task.get("query") or task.get("description", "")
        
        if not query:
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error="No query provided for web research"
            )
        
        try:
            # Perform web search (with timeout protection)
            import asyncio
            try:
                # Run sync tool in executor to avoid blocking
                loop = asyncio.get_event_loop()
                search_results = await asyncio.wait_for(
                    loop.run_in_executor(None, self.search_tool.run, query),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Web search timed out")
                search_results = f"Search timeout for: {query}"
            
            # Analyze and extract key information (with timeout)
            try:
                findings = await asyncio.wait_for(
                    self._analyze_search_results(query, search_results),
                    timeout=60.0  # 60 second timeout for LLM
                )
            except asyncio.TimeoutError:
                logger.warning("Analysis timed out, using simplified results")
                findings = [{"finding": "Analysis timeout - using basic search results", "relevance": "medium"}]
            
            # Extract citations
            citations = self._extract_citations(search_results)
            
            return AgentResult(
                success=True,
                data={
                    "query": query,
                    "findings": findings,
                    "citations": citations,
                    "sources": self._parse_sources(search_results)
                },
                metadata={
                    "num_sources": len(citations),
                    "search_api": self.search_api
                }
            )
        except Exception as e:
            logger.error(f"Web research failed: {e}")
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error=str(e)
            )
    
    async def _analyze_search_results(self, query: str, search_results: str) -> List[Dict[str, Any]]:
        """Analyze search results and extract key findings"""
        
        prompt = f"""Analyze the following web search results for the query: "{query}"

Search Results:
{search_results}

Extract and summarize the key findings. For each finding, include:
1. The main point or fact
2. Relevance to the query
3. Source information

Format as a structured list of findings."""
        
        response = await self.llm.ainvoke(prompt)
        
        # Parse response into structured findings
        findings = [
            {
                "finding": response.content[:200],  # Simplified - parse properly in production
                "relevance": "high",
                "source": "web_search"
            }
        ]
        
        return findings
    
    def _extract_citations(self, search_results: str) -> List[Dict[str, str]]:
        """Extract citations from search results"""
        citations = []
        
        # Try to parse structured results
        import re
        import json
        
        # Try to extract structured data if it's JSON-like
        try:
            # Look for dictionary-like structures
            if '{' in search_results:
                # Try to extract individual result dictionaries
                dict_pattern = r'\{[^{}]*"url"[^{}]*\}'
                matches = re.findall(dict_pattern, search_results)
                for match in matches[:10]:
                    try:
                        result_dict = eval(match)  # Safe for our controlled input
                        if "url" in result_dict:
                            url = result_dict.get("url", "").strip().rstrip("',\"")
                            if url and url.startswith("http"):
                                citations.append({
                                    "url": url,
                                    "title": result_dict.get("title", "Web Source").strip().rstrip("',\""),
                                    "type": result_dict.get("type", "web"),
                                    "score": result_dict.get("score", 0)
                                })
                    except:
                        continue
        except:
            pass
        
        # Fallback: Extract URLs using regex
        if not citations:
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\],\']+'
            urls = re.findall(url_pattern, search_results)
            seen_urls = set()
            for url in urls:
                # Clean URL: remove trailing quotes, commas, etc.
                clean_url = url.rstrip("',\"").strip()
                if clean_url not in seen_urls and len(clean_url) < 200 and clean_url.startswith("http"):
                    seen_urls.add(clean_url)
                    citations.append({
                        "url": clean_url,
                        "title": f"Source from {clean_url.split('/')[2] if '/' in clean_url else 'unknown'}",
                        "type": "web"
                    })
                    if len(citations) >= 10:
                        break
        
        return citations
    
    def _parse_sources(self, search_results: str) -> List[str]:
        """Parse source URLs from search results"""
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\],\']+'
        urls = re.findall(url_pattern, search_results)
        # Clean URLs: remove trailing quotes, commas, etc.
        clean_urls = [url.rstrip("',\"").strip() for url in urls if url.startswith("http")]
        return list(set(clean_urls))[:10]

