"""
Research Coordinator Agent
Plans research tasks, delegates to specialists, and manages workflow.
"""

from typing import Dict, Any
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from core.agent_base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class ResearchCoordinatorAgent(BaseAgent):
    """
    Coordinates research tasks by breaking them down and delegating to specialists.
    Acts as the central planner for multi-agent research workflows.
    """
    
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        super().__init__(
            name="research_coordinator",
            description="Plans research tasks, breaks them into subtasks, and delegates to specialist agents"
        )
        self.llm = ChatOpenAI(model=llm_model, temperature=0)
        
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """
        Create a research plan for the given query
        
        Args:
            task: Must contain 'query' key with research question
            context: Optional context about available resources
            
        Returns:
            AgentResult with research plan
        """
        if not self.validate_input(task):
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error="Invalid task: missing 'query' field"
            )
        
        query = task.get("query", "")
        available_agents = task.get("available_agents", [])
        has_documents = context.get("has_documents", False) if context else False
        
        try:
            plan = await self._create_research_plan(query, available_agents, has_documents)
            
            return AgentResult(
                success=True,
                data=plan,
                metadata={
                    "query": query,
                    "num_tasks": len(plan.get("tasks", [])),
                    "estimated_duration": plan.get("estimated_duration", "unknown")
                }
            )
        except Exception as e:
            logger.error(f"Research coordination failed: {e}")
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error=str(e)
            )
    
    async def _create_research_plan(
        self, 
        query: str, 
        available_agents: list,
        has_documents: bool
    ) -> Dict[str, Any]:
        """Generate a structured research plan"""
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a research coordinator. Break down research queries into specific tasks 
            and assign them to appropriate agents. Consider dependencies and parallelization opportunities."""),
            ("human", """Research Query: {query}

Available Agents: {agents}

User has uploaded documents: {has_docs}

Create a detailed research plan with:
1. Task breakdown
2. Agent assignments
3. Task dependencies
4. Estimated duration

Format as structured plan with tasks array."""),
        ])
        
        agents_str = ", ".join(available_agents)
        prompt = prompt_template.format_messages(
            query=query,
            agents=agents_str,
            has_docs="Yes" if has_documents else "No"
        )
        
        response = await self.llm.ainvoke(prompt)
        
        # Parse and structure the plan
        plan = {
            "query": query,
            "tasks": self._parse_tasks(response.content, available_agents, has_documents),
            "estimated_duration": "5-10 minutes",
            "parallelizable": True
        }
        
        return plan
    
    def _parse_tasks(
        self, 
        response: str, 
        available_agents: list,
        has_documents: bool
    ) -> list:
        """Parse LLM response into structured task list"""
        tasks = []
        task_id = 1
        
        # Always include web research
        tasks.append({
            "task_id": f"task_{task_id}",
            "agent": "web_researcher",
            "description": f"Search the web for information about: {response[:100]}",
            "dependencies": [],
            "priority": "high"
        })
        task_id += 1
        
        # Include document analysis if documents available
        if has_documents:
            tasks.append({
                "task_id": f"task_{task_id}",
                "agent": "document_analyzer",
                "description": "Analyze uploaded documents using RAG system",
                "dependencies": [],
                "priority": "high"
            })
            task_id += 1
        
        # Synthesis task depends on research tasks
        tasks.append({
            "task_id": f"task_{task_id}",
            "agent": "synthesis_agent",
            "description": "Combine findings from all sources",
            "dependencies": [t["task_id"] for t in tasks if t["agent"] != "synthesis_agent"],
            "priority": "high"
        })
        task_id += 1
        
        # Validation task
        tasks.append({
            "task_id": f"task_{task_id}",
            "agent": "validator_agent",
            "description": "Validate facts and check consistency",
            "dependencies": [f"task_{task_id - 1}"],
            "priority": "medium"
        })
        
        return tasks

