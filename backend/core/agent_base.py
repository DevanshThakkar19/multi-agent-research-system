"""
Base Agent Class for Multi-Agent Research System
Provides common functionality for all agents in the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Standard result format for agent operations"""
    success: bool
    data: Any
    metadata: Dict[str, Any]
    error: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent research system"""
    
    def __init__(self, name: str, description: str, tools: List[Any] = None):
        self.name = name
        self.description = description
        self.tools = tools or []
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    @abstractmethod
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """
        Execute the agent's primary task
        
        Args:
            task: Task specification with required parameters
            context: Additional context from other agents or system
            
        Returns:
            AgentResult with execution results
        """
        pass
    
    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate task input before execution"""
        return True
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities and metadata"""
        return {
            "name": self.name,
            "description": self.description,
            "tools": [tool.__class__.__name__ if hasattr(tool, '__class__') else str(tool) for tool in self.tools]
        }
    
    def log_execution(self, task: Dict[str, Any], result: AgentResult):
        """Log agent execution for monitoring"""
        self.logger.info(
            f"Agent {self.name} executed task: {task.get('type', 'unknown')} - "
            f"Success: {result.success}"
        )






















