"""
Agent Interface Implementation
Provides an autonomous agent that can proactively use tools to accomplish tasks
"""

import asyncio
import aiohttp
import aioconsole
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path
import threading
from datetime import datetime
import uuid
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress
from rich.prompt import Prompt

# Setup logging with file handler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_chat.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Setup rich console
console = Console()

class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    ERROR = "error"

@dataclass
class ConversationHistory:
    messages: List[Dict] = None
    max_history: int = 100
    
    def __post_init__(self):
        if self.messages is None:
            self.messages = []
            
    def add_message(self, role: str, content: str):
        """Add a message to history"""
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message)
        
        # Trim history if needed
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
            
    def save(self, filename: str = "chat_history.json"):
        """Save conversation history"""
        with open(filename, 'w') as f:
            json.dump({"messages": self.messages}, f, indent=2)
            
    def load(self, filename: str = "chat_history.json"):
        """Load conversation history"""
        try:
            with open(filename) as f:
                data = json.load(f)
                self.messages = data.get("messages", [])
        except FileNotFoundError:
            self.messages = []

@dataclass
class Task:
    id: str
    goal: str
    steps: List[Dict]
    status: str = "pending"
    results: List[Dict] = None
    error: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.results is None:
            self.results = []
            
    def start(self):
        """Mark task as started"""
        self.status = "running"
        self.start_time = datetime.now().isoformat()
        
    def complete(self, success: bool = True):
        """Mark task as completed"""
        self.status = "success" if success else "failed"
        self.end_time = datetime.now().isoformat()
        
    def to_dict(self) -> Dict:
        """Convert task to dictionary"""
        return asdict(self)

class TaskManager:
    def __init__(self):
        self.tasks: List[Task] = []
        self.max_tasks = 1000
        
    def create_task(self, goal: str, steps: List[Dict]) -> Task:
        """Create a new task"""
        task = Task(id=str(uuid.uuid4()), goal=goal, steps=steps)
        self.tasks.append(task)
        
        # Trim task history if needed
        if len(self.tasks) > self.max_tasks:
            self.tasks = self.tasks[-self.max_tasks:]
            
        return task
        
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
        
    def save_tasks(self, filename: str = "tasks.json"):
        """Save tasks to file"""
        with open(filename, 'w') as f:
            json.dump({"tasks": [t.to_dict() for t in self.tasks]}, f, indent=2)
            
    def load_tasks(self, filename: str = "tasks.json"):
        """Load tasks from file"""
        try:
            with open(filename) as f:
                data = json.load(f)
                self.tasks = [Task(**t) for t in data.get("tasks", [])]
        except FileNotFoundError:
            self.tasks = []

class ToolManager:
    def __init__(self, tool_url: str = "http://localhost:3000/api/tools"):
        self.tool_url = tool_url
        self.execution_history = []
        
    async def execute_tool(self, tool_name: str, parameters: Dict) -> Optional[Dict]:
        """Execute a specific tool"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.tool_url,
                    json={"name": tool_name, "parameters": parameters}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.execution_history.append({
                            "tool": tool_name,
                            "parameters": parameters,
                            "timestamp": datetime.now().isoformat(),
                            "success": True
                        })
                        return result
                        
            self.execution_history.append({
                "tool": tool_name,
                "parameters": parameters,
                "timestamp": datetime.now().isoformat(),
                "success": False
            })
            return None
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return None

class ModelManager:
    def __init__(self, model_url: str = "http://localhost:3000/api/generate"):
        self.model_url = model_url
        self.execution_history = []
        
    async def execute_model(self, model_name: str, parameters: Dict) -> Optional[Dict]:
        """Execute a specific model"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.model_url,
                    json={"name": model_name, "parameters": parameters}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.execution_history.append({
                            "model": model_name,
                            "parameters": parameters,
                            "timestamp": datetime.now().isoformat(),
                            "success": True
                        })
                        return result
                        
            self.execution_history.append({
                "model": model_name,
                "parameters": parameters,
                "timestamp": datetime.now().isoformat(),
                "success": False
            })
            return None
            
        except Exception as e:
            logger.error(f"Error executing model {model_name}: {str(e)}")
            return None

class MemorySystem:
    def __init__(self):
        self.working_memory: Dict = {}
        self.long_term_memory: List[Dict] = []
        self.context_window: List[Dict] = []
        self.max_context_size = 50
        
    def add_to_working_memory(self, key: str, value: object):
        """Add item to working memory"""
        self.working_memory[key] = value
        
    def store_long_term(self, item: Dict):
        """Store item in long-term memory"""
        self.long_term_memory.append({
            **item,
            "timestamp": datetime.now().isoformat()
        })
        
    def update_context(self, item: Dict):
        """Update context window"""
        self.context_window.append(item)
        if len(self.context_window) > self.max_context_size:
            self.context_window.pop(0)
            
    def get_relevant_context(self, query: str) -> List[Dict]:
        """Get context relevant to query"""
        # Implement relevance scoring and filtering
        return self.context_window[-10:]  # Simplified for now

class PlanningSystem:
    def __init__(self):
        self.current_plan: Optional[List[Dict]] = None
        self.fallback_strategies: Dict[str, List[Dict]] = {}
        self.planning_rules = self._load_planning_rules()
        
    def _load_planning_rules(self) -> Dict:
        """Load planning rules from JSON file"""
        try:
            with open('planning_rules.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("Planning rules file not found, using default rules")
            return {
                "task_patterns": {},
                "compound_tasks": {}
            }
            
    def _parse_model_response(self, response: str) -> List[Dict]:
        """Parse model response into a plan"""
        plan = []
        try:
            # Extract action items from response
            lines = response.split('\n')
            current_action = None
            
            for line in lines:
                line = line.strip().lower()
                if not line:
                    continue
                    
                # Look for tool mentions in the response
                if "read" in line and "file" in line:
                    plan.append({"action": "read_file", "tool": "read_file"})
                elif "write" in line and "file" in line:
                    plan.append({"action": "write_file", "tool": "write_file"})
                elif "search" in line and "code" in line:
                    plan.append({"action": "search_code", "tool": "semantic_search"})
                elif "check" in line and "error" in line:
                    plan.append({"action": "analyze_code", "tool": "get_errors"})
                elif any(word in line for word in ["ask", "query", "question", "what", "how", "why"]):
                    plan.append({"action": "model1", "tool": "model1"})
                    
            # If no specific tools were identified, use model response
            if not plan:
                plan.append({"action": "model1", "tool": "model1"})
                
            return plan
            
        except Exception as e:
            logger.error(f"Error parsing model response: {str(e)}")
            # Fallback to basic plan
            return [{"action": "model1", "tool": "model1"}]
    
    def create_plan(self, goal: str, context: List[Dict]) -> List[Dict]:
        """Create execution plan for goal using model"""
        try:
            # First try to get a plan from the model
            result = asyncio.run(self._get_model_plan(goal))
            
            if result:
                # Parse model response into a plan
                plan = self._parse_model_response(result)
                if plan:
                    self.current_plan = plan
                    return plan
                    
            # Fallback to task type based planning if model fails
            task_types = self._identify_task_types(goal)
            if task_types:
                plan = []
                for task_type in task_types:
                    tools = self._get_tools_for_task_type(task_type)
                    plan.extend(tools)
                self.current_plan = plan
                return plan
                
            # Basic fallback plan if all else fails
            basic_plan = self._create_basic_plan(goal)
            self.current_plan = basic_plan
            return basic_plan
            
        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}")
            # Ultimate fallback - use model
            return [{"action": "model1", "tool": "model1"}]
            
    async def _get_model_plan(self, goal: str) -> Optional[str]:
        """Get plan from model"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:3000/api/generate",
                    json={
                        "name": "model1",
                        "parameters": {
                            "ask": f"Given this task: {goal}\nWhat tools and steps are needed to complete it?",
                            "test": "test"
                        }
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("answer")
            return None
        except Exception as e:
            logger.error(f"Error getting model plan: {str(e)}")
            return None
            
    def _create_basic_plan(self, goal: str) -> List[Dict]:
        """Create basic plan based on goal keywords"""
        goal_lower = goal.lower()
        
        if "read" in goal_lower and "file" in goal_lower:
            return [{"action": "read_file", "tool": "read_file"}]
        elif "write" in goal_lower and "file" in goal_lower:
            return [{"action": "write_file", "tool": "write_file"}]
        elif "ask" in goal_lower:
            return [{"action": "model1", "tool": "model1"}]
        elif "code" in goal_lower:
            return [
                {"action": "search_code", "tool": "semantic_search"},
                {"action": "analyze_code", "tool": "get_errors"}
            ]
        
        # Default to model response
        return [{"action": "model1", "tool": "model1"}]

class Agent:
    def __init__(self, model_url: str = "http://localhost:3000/api/generate"):
        self.model_url = model_url
        self.tool_manager = ToolManager()
        self.model_manager = ModelManager()
        self.memory_system = MemorySystem()
        self.planning_system = PlanningSystem()
        self.conversation_history = ConversationHistory()
        self.task_manager = TaskManager()
        self.state = AgentState.IDLE
        self.current_task: Optional[Task] = None
        self.max_retries = 3
        self.retry_delay = 1
        
    async def _execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with retry logic"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (attempt + 1)  # Exponential backoff
                    logger.warning(f"Connection error: {str(e)}. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                raise
        
        raise last_error

    async def handle_task(self, goal: str):
        """Handle a new task with improved error handling"""
        self.state = AgentState.PLANNING
        self.conversation_history.add_message("user", goal)
        
        try:
            # Create task
            context = self.memory_system.get_relevant_context(goal)
            plan = self.planning_system.create_plan(goal, context)
            self.current_task = self.task_manager.create_task(goal=goal, steps=plan)
            self.current_task.start()
            
            # Execute plan
            self.state = AgentState.EXECUTING
            results = []
            
            with Progress() as progress:
                task = progress.add_task(f"[cyan]Executing task: {goal}", total=len(plan))
                
                for step in plan:
                    try:
                        if "ask" in goal.lower():
                            ask_content = goal.lower().replace("ask", "").strip()
                            result = await self._execute_with_retry(
                                self.model_manager.execute_model,
                                step["tool"],
                                {"ask": ask_content, "test": "test"}
                            )
                            if result and "answer" in result:
                                formatted_result = {
                                    "response": result["answer"].strip(),
                                    "type": "model_response"
                                }
                                results.append({
                                    "step": step,
                                    "result": formatted_result,
                                    "success": True
                                })
                                self.conversation_history.add_message(
                                    "assistant", 
                                    formatted_result["response"]
                                )
                        elif "read" in goal.lower() and "file" in goal.lower():
                            command = goal.lower()
                            file_name = command.replace("read", "").replace("file", "").strip()                            # Clean up the file name and ensure it's properly handled
                            file_name = file_name.strip()  # Remove any leading/trailing spaces
                            
                            # Always use relative path for workspace files
                            if Path(file_name).is_absolute():
                                file_name = str(Path(file_name).name)
                            
                            logger.info(f"Attempting to read file: {file_name}")
                            # Single attempt to read the file
                            result = await self._execute_with_retry(
                                self.tool_manager.execute_tool,
                                "read_file",
                                {
                                    "path": file_name,
                                    "start_line": None,
                                    "end_line": None
                                }
                            )
                            
                            if result and "content" in result:
                                formatted_result = {
                                    "content": result["content"],
                                    "type": "file_content"
                                }
                                results.append({
                                    "step": step,
                                    "result": formatted_result,
                                    "success": True
                                })
                                self.conversation_history.add_message(
                                    "assistant",
                                    f"Content of {file_name}:\n{formatted_result['content']}"
                                )
                            else:
                                error_msg = f"Could not read file: {file_name}"
                                results.append({
                                    "step": step,
                                    "error": error_msg,
                                    "success": False
                                })
                                self.conversation_history.add_message("system", error_msg)
                        elif "write" in goal.lower() and "file" in goal.lower():
                            command = goal.lower()
                            parts = command.split(" ", 3)  # Split into: write, file, filename, content
                            if len(parts) >= 4:
                                file_name = parts[2].strip()
                                content = parts[3].strip()
                                
                                result = await self._execute_with_retry(
                                    self.tool_manager.execute_tool,
                                    "write_file",
                                    {
                                        "path": file_name,
                                        "content": content
                                    }
                                )
                                
                                if result and result.get("success"):
                                    formatted_result = {
                                        "message": f"Successfully wrote to file: {file_name}",
                                        "type": "file_operation"
                                    }
                                    results.append({
                                        "step": step,
                                        "result": formatted_result,
                                        "success": True
                                    })
                                    self.conversation_history.add_message(
                                        "assistant",
                                        formatted_result["message"]
                                    )
                            
                    except Exception as e:
                        error_msg = f"Error executing step: {str(e)}"
                        logger.error(error_msg)
                        results.append({
                            "step": step,
                            "error": error_msg,
                            "success": False
                        })
                        self.conversation_history.add_message("system", error_msg)
                        
                    progress.update(task, advance=1)
                    
            # Evaluate results
            self.state = AgentState.EVALUATING
            self.current_task.results = results
            success_rate = sum(1 for r in results if r.get("success", False)) / len(results)
            
            if success_rate < 0.5:
                error_msg = "Task execution had significant failures"
                console.print(f"[red]{error_msg}[/red]")
                self.current_task.complete(success=False)
                self.conversation_history.add_message("system", error_msg)
                
                # Try to recover with fallback strategy
                if self.planning_system.fallback_strategies:
                    console.print("[yellow]Attempting recovery with fallback strategy...[/yellow]")
                    return await self.handle_task(goal)  # Retry with fallback
            else:
                success_msg = "Task completed successfully"
                console.print(f"[green]{success_msg}[/green]")
                self.current_task.complete(success=True)
                self.conversation_history.add_message("system", success_msg)
                
            self.state = AgentState.IDLE
            return results
            
        except Exception as e:
            error_msg = f"Task failed: {str(e)}"
            logger.error(error_msg)
            if self.current_task:
                self.current_task.complete(success=False)
                self.current_task.error = error_msg
            self.state = AgentState.ERROR
            self.conversation_history.add_message("system", error_msg)
            raise

    async def monitor_environment(self):
        """Monitor environment for events or conditions that require action"""
        while True:
            if self.state == AgentState.IDLE:
                # Check for conditions that might need attention
                try:
                    # Example: Check for errors in workspace
                    result = await self.tool_manager.execute_tool(
                        "get_errors",
                        {"filePaths": ["."]}
                    )
                    
                    if result and result.get("errors"):
                        console.print("[yellow]Detected code errors, initiating analysis...[/yellow]")
                        await self.handle_task("Analyze and suggest fixes for code errors")
                        
                except Exception as e:
                    logger.error(f"Error in environment monitoring: {str(e)}")
                    
            await asyncio.sleep(60)  # Check every minute
            
    def save_state(self, filename: str = "agent_state.json"):
        """Save agent state"""
        try:
            state = {
                "working_memory": self.memory_system.working_memory,
                "context_window": self.memory_system.context_window,
                "tool_history": self.tool_manager.execution_history,
                "current_state": self.state.value
            }
            
            with open(filename, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.info(f"Agent state saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving agent state: {str(e)}")
            
    def load_state(self, filename: str = "agent_state.json"):
        """Load agent state"""
        try:
            with open(filename) as f:
                state = json.load(f)
                
            self.memory_system.working_memory = state.get("working_memory", {})
            self.memory_system.context_window = state.get("context_window", [])
            self.tool_manager.execution_history = state.get("tool_history", [])
            self.state = AgentState(state.get("current_state", "idle"))
            
            logger.info(f"Agent state loaded from {filename}")
            
        except Exception as e:
            logger.error(f"Error loading agent state: {str(e)}")

async def main():
    agent = Agent()
    
    try:
        # Start environment monitoring in background
        monitor_task = asyncio.create_task(agent.monitor_environment())
        
        console.print("[bold blue]AI Agent Interface[/bold blue]")
        console.print("Type 'exit' to end the session\n")
        
        while True:
            try:
                # Get user input
                #pip install aioconsole
                user_input = await aioconsole.ainput("> ")
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                    
                # Handle task
                results = await agent.handle_task(user_input)
                
                # Display results
                if results:
                    for result in results:
                        if result.get("success"):
                            console.print(Panel(
                                Markdown(str(result["result"])),
                                border_style="green"
                            ))
                        else:
                            console.print(Panel(
                                f"Step failed: {result.get('error', 'Unknown error')}",
                                border_style="red"
                            ))
                            
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                console.print(f"[red]Error: {str(e)}[/red]")
                
    finally:
        # Save agent state
        agent.save_state()
        # Cancel monitoring task
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(main())
