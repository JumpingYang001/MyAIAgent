"""
Planning System Implementation for MCP Server
Handles task planning and execution strategies
"""

from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime
from model_manager import ModelManager

logger = logging.getLogger(__name__)

class Task:
    def __init__(self, goal: str, steps: List[Dict], task_id: str = None):
        self.id = task_id
        self.goal = goal
        self.steps = steps
        self.status = "pending"
        self.results = []
        self.error = None
        self.start_time = None
        self.end_time = None

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
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": self.steps,
            "status": self.status,
            "results": self.results,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time
        }

class PlanningSystem:
    def __init__(self, model_name: str = "microsoft/DialoGPT-small"):
        self.current_plan: Optional[List[Dict]] = None
        self.fallback_strategies: Dict[str, List[Dict]] = {}
        self.planning_rules = self._load_planning_rules()
        self.model_manager = ModelManager(model_name=model_name)

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

    async def _get_model_plan(self, goal: str, context: List[Dict]) -> Optional[str]:
        """Get plan from model using local ModelManager"""
        try:
            # Create a detailed prompt for plan generation
            context_str = "\n".join([json.dumps(ctx) for ctx in context]) if context else "No additional context."
            prompt = f"""Create a detailed plan for this task. Break it down into specific steps using available tools.

Task Goal: {goal}

Context:
{context_str}

Available Tools:
- read_file: Read file contents
- write_file: Create or update files
- search_code: Search through codebase
- analyze_code: Check for errors/issues
- execute_command: Run system commands
- model1: Use AI model for complex tasks

Format your response as a numbered list of steps. For each step, specify the tool to use and any parameters needed."""

            # Execute model request using model manager
            response = await self.model_manager.execute_model("generate", {"ask": prompt})
            if response and "result" in response:
                return response["result"].get("answer")
            return None
            
        except Exception as e:
            logger.error(f"Error getting model plan: {str(e)}")
            return None

    def _parse_model_response(self, response: str) -> List[Dict]:
        """Parse model response into a structured plan"""
        plan = []
        try:
            lines = response.split('\n')
            current_step = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Look for numbered steps
                if line[0].isdigit() and '.' in line[:3]:
                    # Save previous step if exists
                    if current_step:
                        plan.append(current_step)
                    current_step = {"description": line}
                    continue
                
                line_lower = line.lower()
                # Extract tool and parameters from step details
                if "tool:" in line_lower:
                    tool = line_lower.split("tool:")[1].strip()
                    if tool == "search_code":
                        tool = "semantic_search"  # Map to actual tool name
                    current_step["tool"] = tool
                    current_step["action"] = tool
                
                elif "parameters:" in line_lower or "params:" in line_lower:
                    try:
                        # Try to parse parameters as JSON if they're in that format
                        param_str = line.split(":", 1)[1].strip()
                        if "{" in param_str:
                            params = json.loads(param_str)
                        else:
                            # Parse key-value pairs in plain text
                            params = dict(p.split("=") for p in param_str.split(","))
                        current_step["parameters"] = params
                    except:
                        # If parsing fails, store as description
                        current_step["parameters"] = {"description": param_str}
            
            # Add the last step if exists
            if current_step:
                plan.append(current_step)
                
            # Validate and fix plan steps
            plan = self._validate_and_fix_plan(plan)
            return plan
            
        except Exception as e:
            logger.error(f"Error parsing model response: {str(e)}")
            # Fallback to basic plan
            return [{"action": "model1", "tool": "model1"}]

    def _validate_and_fix_plan(self, plan: List[Dict]) -> List[Dict]:
        """Validate and fix plan steps to ensure they have all required fields"""
        valid_tools = {
            "read_file", "write_file", "semantic_search", "get_errors",
            "execute_command", "model1"
        }
        
        fixed_plan = []
        for step in plan:
            # Ensure each step has the basic required fields
            if "tool" not in step:
                # Try to infer tool from description
                desc = step.get("description", "").lower()
                if "read" in desc and "file" in desc:
                    step["tool"] = "read_file"
                elif "write" in desc and "file" in desc:
                    step["tool"] = "write_file"
                elif "search" in desc:
                    step["tool"] = "semantic_search"
                elif "error" in desc or "check" in desc:
                    step["tool"] = "get_errors"
                elif "run" in desc or "execute" in desc:
                    step["tool"] = "execute_command"
                else:
                    step["tool"] = "model1"
            
            # Validate tool name
            if step["tool"] not in valid_tools:
                logger.warning(f"Invalid tool {step['tool']}, defaulting to model1")
                step["tool"] = "model1"
            
            # Ensure action matches tool
            step["action"] = step["tool"]
            
            # Initialize parameters if not present
            if "parameters" not in step:
                step["parameters"] = {}
            
            fixed_plan.append(step)
        
        return fixed_plan

    async def create_plan(self, goal: str, context: List[Dict]) -> List[Dict]:
        """Create execution plan for goal using local model manager"""
        try:
            # Get plan from model
            result = await self._get_model_plan(goal, context)
            
            if result:
                # Parse model response into a plan
                plan = self._parse_model_response(result)
                if plan:
                    self.current_plan = plan
                    return plan
                    
            # If model plan fails, try using planning rules
            rule_based_plan = self._create_rule_based_plan(goal)
            if rule_based_plan:
                self.current_plan = rule_based_plan
                return rule_based_plan
                    
            # Basic fallback plan if all else fails
            basic_plan = self._create_basic_plan(goal)
            self.current_plan = basic_plan
            return basic_plan
            
        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}")
            # Ultimate fallback - use model
            return [{"action": "model1", "tool": "model1"}]
            
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

    def _create_rule_based_plan(self, goal: str) -> Optional[List[Dict]]:
        """Create a plan based on planning rules"""
        try:
            goal_lower = goal.lower()
            
            # Check task patterns
            for task_name, pattern in self.planning_rules.get("task_patterns", {}).items():
                if any(p in goal_lower for p in pattern.get("patterns", [])):
                    return [
                        {"action": tool, "tool": tool, "parameters": {}}
                        for tool in pattern.get("tools", [])
                    ]
            
            # Check compound tasks
            for task_name, subtasks in self.planning_rules.get("compound_tasks", {}).items():
                if task_name.lower() in goal_lower:
                    plan = []
                    for subtask in subtasks:
                        # Look up tools for each subtask
                        if subtask in self.planning_rules.get("task_patterns", {}):
                            tools = self.planning_rules["task_patterns"][subtask].get("tools", [])
                            plan.extend([
                                {"action": tool, "tool": tool, "parameters": {}}
                                for tool in tools
                            ])
                    if plan:
                        return plan
            
            return None
            
        except Exception as e:
            logger.error(f"Error in rule-based planning: {str(e)}")
            return None
