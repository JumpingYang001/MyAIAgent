from typing import Dict, Any, Optional
import json
import sys
import logging
from enum import Enum
import asyncio
from datetime import datetime
import uuid
from pathlib import Path

from tool_manager import ToolManager
from model_manager import ModelManager
from memory_system import MemorySystem
from planning_system import PlanningSystem, Task

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    ERROR = "error"

class AgentServer:
    def __init__(self):
        self.state = AgentState.IDLE
        self.tool_manager = None  # Will be initialized during setup
        self.model_manager = None
        self.planning_system = None
        self.memory_system = None
        self.current_task = None
        self.max_retries = 3
        self.retry_delay = 1
        
    def initialize(self):
        """Initialize server components"""
        # Initialize components here
        logger.info("Agent server initialized")
        return {
            "capabilities": {
                "modelProperties": {
                    "name": "agent-mcp-server",
                    "version": "0.1.0"
                },
                "supportedMethods": [
                    "handle_task",
                    "get_state",
                    "monitor_environment"
                ]
            }
        }

    async def handle_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a task request"""
        goal = params.get("goal")
        if not goal:
            return {"error": "No goal provided"}

        try:
            self.state = AgentState.PLANNING
            # Implementation of task handling logic here
            # This will be similar to the original handle_task but adapted for MCP
            
            return {
                "status": "success",
                "state": self.state.value,
                "result": "Task completed"
            }
            
        except Exception as e:
            logger.error(f"Error handling task: {str(e)}")
            self.state = AgentState.ERROR
            return {
                "error": str(e),
                "state": self.state.value
            }

    async def get_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current agent state"""
        return {
            "state": self.state.value,
            "currentTask": self.current_task.to_dict() if self.current_task else None
        }

    async def monitor_environment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor environment for events"""
        # Implementation of environment monitoring
        return {
            "status": "monitoring",
            "state": self.state.value
        }

class MCPAgentServer:
    def __init__(self):
        self.agent = AgentServer()
        self.methods = {
            "initialize": self.agent.initialize,
            "handle_task": self.agent.handle_task,
            "get_state": self.agent.get_state,
            "monitor_environment": self.agent.monitor_environment
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        method = request.get('method')
        params = request.get('params', {})
        
        if method not in self.methods:
            return {
                'error': {
                    'code': -32601,
                    'message': f'Method {method} not found'
                }
            }

        try:
            if method == "initialize":
                result = self.methods[method]()
            else:
                result = await self.methods[method](params)
            
            return {'result': result}
            
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                'error': {
                    'code': -32000,
                    'message': str(e)
                }
            }

    async def run(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                    
                request = json.loads(line)
                response = await self.handle_request(request)
                
                # Add jsonrpc version and id from request
                response['jsonrpc'] = '2.0'
                if 'id' in request:
                    response['id'] = request['id']
                
                # Write response
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()
                
            except Exception as e:
                error_response = {
                    'jsonrpc': '2.0',
                    'error': {
                        'code': -32603,
                        'message': f'Internal error: {str(e)}'
                    }
                }
                if 'id' in request:
                    error_response['id'] = request['id']
                sys.stdout.write(json.dumps(error_response) + '\n')
                sys.stdout.flush()

if __name__ == "__main__":
    server = MCPAgentServer()
    asyncio.run(server.run())
