# MCP Planning System Guide

## Overview

The MCP Planning System is a sophisticated task planning and execution framework that helps break down high-level goals into actionable steps using the TinyLlama Chat model. The system provides robust plan generation with fallback strategies for reliable operation.

## Core Components

### 1. Model Integration

- Uses TinyLlama-1.1B-Chat-v1.0 as the primary planning model
- Supports both CPU and CUDA-enabled GPU execution
- Automatic device selection based on availability
- Memory-efficient model loading and cleanup

### 2. Task Management

Tasks are the fundamental unit of work in the planning system. Each task has:

- **ID**: Unique identifier
- **Goal**: High-level description of what needs to be accomplished
- **Steps**: List of actions needed to complete the task
- **Status**: Current state (pending/running/success/failed)
- **Results**: Outputs from executed steps
- **Timing**: Start and end timestamps

Example task creation:
```python
task = Task(
    goal="Read and analyze config.json file",
    steps=[
        {"action": "read_file", "tool": "read_file"},
        {"action": "analyze_code", "tool": "get_errors"}
    ]
)
```

### 3. Plan Generation

The planning system uses a three-tier approach to generate execution plans:

1. **Model-based Planning** (Primary):
   - Uses TinyLlama Chat model to generate sophisticated plans
   - Provides context-aware prompting for better understanding
   - Generates structured step-by-step plans with tool parameters
   - Adapts to complex requirements using natural language understanding

2. **Rule-based Planning** (First Fallback):
   - Uses predefined patterns in planning_rules.json
   - Matches goals to known task patterns
   - Supports compound task definitions

3. **Basic Planning** (Ultimate Fallback):
   - Keyword-based planning for common operations
   - Ensures system always produces a workable plan
   - Handles basic file and code operations

### 4. Supported Actions

The planning system recognizes several core actions:

- **read_file**: Read file contents
- **write_file**: Create or update files
- **search_code**: Search through codebase
- **analyze_code**: Check for errors/issues
- **execute_command**: Run system commands
- **model1**: Use AI model for complex tasks

## Usage Guide

### 1. Basic Task Creation

```python
from planning_system import PlanningSystem, Task

# Initialize planning system with TinyLlama model
planner = PlanningSystem()

# Create and execute a plan
plan = await planner.create_plan(
    goal="Check config.json for errors",
    context=[{"file": "config.json"}]
)

# Create task from plan
task = Task(
    goal="Check config.json for errors",
    steps=plan
)

# Start task execution
task.start()
```

### 2. Using Planning Rules

Create a planning_rules.json file:
```json
{
    "task_patterns": {
        "file_operations": {
            "patterns": ["read", "write", "file"],
            "tools": ["read_file", "write_file"]
        },
        "code_analysis": {
            "patterns": ["analyze", "check", "errors"],
            "tools": ["get_errors", "semantic_search"]
        }
    },
    "compound_tasks": {
        "code_review": ["code_analysis", "model1"]
    }
}
```

### 3. Monitoring Tasks

Track task progress and results:

```python
# Check task status
if task.status == "running":
    print(f"Task started at: {task.start_time}")
elif task.status == "success":
    print(f"Task completed successfully at: {task.end_time}")
    print(f"Results: {task.results}")
```

## Best Practices

1. **Goal Definition**
   - Be specific and clear in goal descriptions
   - Include relevant context for better model understanding
   - Use consistent terminology
   - Provide file paths when working with files

2. **Error Handling**
   - Always check task status and errors
   - Use fallback strategies when needed
   - Log important events and failures
   - Monitor model execution status

3. **Plan Management**
   - Review generated plans before execution
   - Monitor long-running tasks
   - Keep planning rules updated
   - Clean up model resources properly

## Example Workflows

### 1. Code Analysis Task

```python
# Create a code analysis plan
plan = await planner.create_plan(
    goal="Find and fix errors in src/main.py",
    context=[{"file": "src/main.py"}]
)

# Execute the plan
task = Task(goal="Code analysis", steps=plan)
task.start()
```

### 2. File Operation Task

```python
# Create a file operation plan
plan = await planner.create_plan(
    goal="Read config.json and update settings",
    context=[{"file": "config.json"}]
)

# Execute with proper tracking
task = Task(goal="Update config", steps=plan)
task.start()
```

## Troubleshooting

### Common Issues

1. **Model-related Issues**
   - Ensure sufficient memory for model loading
   - Check GPU availability if using CUDA
   - Verify model downloads and cache
   - Monitor model response quality

2. **Plan Generation Fails**
   - Check model initialization status
   - Verify goal clarity and context
   - Review planning rules format
   - Try different planning tiers

3. **Task Execution Errors**
   - Check tool availability
   - Verify file permissions
   - Review error logs
   - Monitor resource usage

## API Reference

### Task Class

```python
class Task:
    def __init__(self, goal: str, steps: List[Dict], task_id: str = None)
    def start()  # Start task execution
    def complete(success: bool = True)  # Mark task as complete
    def to_dict() -> Dict  # Convert task to dictionary
```

### PlanningSystem Class

```python
class PlanningSystem:
    def __init__(self, model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    async def create_plan(goal: str, context: List[Dict]) -> List[Dict]
    def _load_planning_rules() -> Dict  # Load planning configuration
    def _validate_and_fix_plan(plan: List[Dict]) -> List[Dict]
```

## Security Considerations

1. **Model Security**
   - Use trusted model sources
   - Monitor model input/output
   - Implement rate limiting
   - Clean up model resources

2. **File Operations**
   - Validate file paths
   - Check permissions
   - Sanitize inputs

3. **Data Protection**
   - Protect sensitive task data
   - Secure planning rules
   - Log access appropriately

## Performance Optimization

1. **Model Optimization**
   - Use GPU when available
   - Implement proper cleanup
   - Monitor memory usage
   - Consider batch operations

2. **Plan Execution**
   - Use efficient tool combinations
   - Monitor execution times
   - Implement timeouts
   - Cache frequent operations

3. **Resource Management**
   - Monitor GPU memory
   - Implement memory limits
   - Clean up resources
   - Use appropriate batch sizes
