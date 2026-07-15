"""
Multi-Agent Orchestrator
Coordinates and manages the execution of multiple agents for research tasks.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .agent_base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Orchestrates multiple agents to work together on complex research tasks.
    Manages task decomposition, agent coordination, and result synthesis.
    """
    
    def __init__(self, agents: Dict[str, BaseAgent], llm_model: str = "gpt-4o-mini"):
        self.agents = agents
        self.llm = ChatOpenAI(model=llm_model, temperature=0)
        self.execution_history: List[Dict[str, Any]] = []
        
    async def coordinate_research(
        self, 
        query: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Coordinate a research task across multiple agents
        
        Args:
            query: Research query from user
            context: Additional context (e.g., uploaded documents)
            
        Returns:
            Comprehensive research result with all agent outputs
        """
        logger.info(f"Starting research coordination for query: {query}")
        
        # Step 1: Plan research strategy
        plan = await self._create_research_plan(query, context)
        
        # Step 2: Execute tasks with parallelization support
        import asyncio
        results = {}
        
        async def execute_agent_with_timeout(agent_name, agent, task, timeout=120):
            """Execute agent with timeout"""
            try:
                # Ensure task has query if agent needs it
                if "query" not in task and query:
                    task["query"] = query
                
                result = await asyncio.wait_for(
                    agent.execute(task, context),
                    timeout=timeout
                )
                return agent_name, result, None
            except asyncio.TimeoutError:
                logger.error(f"Agent {agent_name} timed out after {timeout}s")
                return agent_name, None, f"Timeout after {timeout} seconds"
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                return agent_name, None, str(e)
        
        # Build dependency graph for parallel execution
        task_map = {task["task_id"]: task for task in plan["tasks"]}
        task_results = {}
        task_futures = {}
        
        async def execute_task_with_dependencies(task):
            """Execute a task, waiting for dependencies first"""
            task_id = task["task_id"]
            dependencies = task.get("dependencies", [])
            
            # Wait for dependencies to complete (if any)
            if dependencies:
                dependency_futures = [task_futures.get(dep) for dep in dependencies if dep in task_futures]
                if dependency_futures:
                    await asyncio.gather(*[f for f in dependency_futures if f is not None], return_exceptions=True)
            
            # Execute the task
            agent_name = task["agent"]
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                agent_name_result, result, error = await execute_agent_with_timeout(
                    agent_name, agent, task
                )
                
                task_results[task_id] = result
                
                if result:
                    results[agent_name] = result
                    self.execution_history.append({
                        "agent": agent_name,
                        "task": task,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    results[agent_name] = AgentResult(
                        success=False,
                        data=None,
                        metadata={},
                        error=error or "Unknown error"
                    )
        
        # Create futures for all tasks (enables parallel execution)
        for task in plan["tasks"]:
            task_futures[task["task_id"]] = execute_task_with_dependencies(task)
        
        # Execute all tasks in parallel (dependencies handled by await in execute_task_with_dependencies)
        await asyncio.gather(*task_futures.values(), return_exceptions=True)
        
        # Step 3: Synthesize results (synthesis agent can work even without other results)
        synthesis = await self._synthesize_results(query, results, context)
        
        # Step 4: Run validator if synthesis succeeded
        if synthesis.get("report") and "validator_agent" in self.agents:
            validator_task = {
                "query": query,
                "synthesis": synthesis,
                "results": {name: r.data for name, r in results.items() if r.success}
            }
            try:
                import asyncio
                validator_result = await asyncio.wait_for(
                    self.agents["validator_agent"].execute(validator_task, context),
                    timeout=60.0
                )
                if validator_result.success:
                    results["validator_agent"] = validator_result
            except Exception as e:
                logger.warning(f"Validator failed: {e}")
        
        return {
            "query": query,
            "plan": plan,
            "agent_results": results,
            "synthesis": synthesis,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _create_research_plan(
        self, 
        query: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a research plan by decomposing the query"""
        
        available_agents = list(self.agents.keys())
        agent_descriptions = {
            name: agent.get_capabilities()["description"] 
            for name, agent in self.agents.items()
        }
        
        prompt = f"""You are a research coordinator. Given the following research query, create a detailed plan.

Query: {query}

Available Agents:
{chr(10).join([f"- {name}: {desc}" for name, desc in agent_descriptions.items()])}

Context: {context.get('has_documents', False) if context else False} - User has uploaded documents

Create a research plan that:
1. Breaks down the query into specific tasks
2. Assigns each task to the appropriate agent
3. Identifies dependencies between tasks
4. Determines if tasks can run in parallel

Return a JSON structure with tasks, each containing:
- task_id: unique identifier
- agent: agent name to handle this task
- description: what the agent should do
- dependencies: list of task_ids this depends on
- priority: high/medium/low
"""
        
        import asyncio
        try:
            response = await asyncio.wait_for(
                self.llm.ainvoke(prompt),
                timeout=30.0  # 30 second timeout for planning
            )
        except asyncio.TimeoutError:
            logger.warning("Planning timed out, using default plan")
            response = type('obj', (object,), {'content': 'Default plan'})()
        
        # Parse response and create plan structure
        # In production, use structured output parsing
        context_with_query = context.copy() if context else {}
        context_with_query["query"] = query
        context_with_query["use_web_search"] = context.get("use_web_search", True) if context else True
        
        plan = {
            "query": query,
            "tasks": self._parse_plan_response(response.content, available_agents, context_with_query),
            "estimated_time": "30-60 seconds",
            "parallel_tasks": []
        }
        
        return plan
    
    def _parse_plan_response(self, response: str, available_agents: List[str], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Parse LLM response into structured task list"""
        # Simplified parser - in production, use structured output
        tasks = []
        use_documents = context.get("has_documents", False) if context else False
        use_web_search = context.get("use_web_search", True) if context else True
        query = context.get("query", "") if context else ""
        
        # Only add document analysis if documents are available and requested
        if use_documents and "document_analyzer" in available_agents:
            tasks.append({
                "task_id": "doc_analysis",
                "agent": "document_analyzer",
                "query": query,
                "description": "Analyze uploaded documents using RAG system",
                "dependencies": [],
                "priority": "high"
            })
        
        # Only add web research if requested
        if use_web_search and "web_researcher" in available_agents:
            tasks.append({
                "task_id": "web_research",
                "agent": "web_researcher",
                "query": query,
                "description": "Search the web for relevant information",
                "dependencies": [],
                "priority": "high"
            })
        
        # Synthesis depends on whatever tasks were created
        if "synthesis_agent" in available_agents:
            task_deps = [t["task_id"] for t in tasks]
            tasks.append({
                "task_id": "synthesis",
                "agent": "synthesis_agent",
                "query": query,
                "description": "Combine all research findings",
                "dependencies": task_deps,
                "priority": "high"
            })
        
        # Validation depends on synthesis
        if "validator_agent" in available_agents and tasks:
            tasks.append({
                "task_id": "validation",
                "agent": "validator_agent",
                "query": query,
                "description": "Validate facts and check consistency",
                "dependencies": ["synthesis"],
                "priority": "medium"
            })
        
        return tasks
    
    async def _synthesize_results(
        self,
        query: str,
        results: Dict[str, AgentResult],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Synthesize results from multiple agents"""
        
        # Collect successful results
        successful_results = {
            name: result.data 
            for name, result in results.items() 
            if result.success
        }
        
        if not successful_results:
            return {
                "summary": "Research completed but no results were successfully retrieved.",
                "sources": [],
                "confidence": 0.0
            }
        
        # Use synthesis agent if available
        if "synthesis_agent" in self.agents and successful_results:
            synthesis_agent = self.agents["synthesis_agent"]
            synthesis_task = {
                "type": "synthesize",
                "query": query,
                "results": successful_results
            }
            try:
                import asyncio
                synthesis_result = await asyncio.wait_for(
                    synthesis_agent.execute(synthesis_task, context),
                    timeout=60.0  # 60 second timeout for synthesis
                )
                
                if synthesis_result.success:
                    return synthesis_result.data
            except asyncio.TimeoutError:
                logger.warning("Synthesis timed out")
            except Exception as e:
                logger.error(f"Synthesis failed: {e}")
        
        # Fallback: simple concatenation
        return {
            "summary": f"Research completed for: {query}",
            "sources": list(successful_results.keys()),
            "findings": successful_results,
            "confidence": 0.7
        }
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status and history"""
        return {
            "total_executions": len(self.execution_history),
            "recent_executions": self.execution_history[-10:],
            "agents": {name: agent.get_capabilities() for name, agent in self.agents.items()}
        }

