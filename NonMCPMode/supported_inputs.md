# Supported Inputs in Agent Chat Interface

## Overview
The Agent Chat Interface provides a natural language interface for interacting with an AI assistant. The system uses TinyLlama for planning and task execution, supporting various commands and operations.

## Basic Commands

### Model Interaction (Ask Commands)
- `ask <question>`: Ask any question to the AI model
  ```
  ask what is Python?
  ask how do I write a function in JavaScript?
  ask explain what this code does
  ask what are the best practices for error handling?
  ```

### File Operations
- `read file <filename>`: Read contents of a file
  ```
  read file test.txt
  read file config.yaml
  read file workspace/test.txt
  ```
- `write file <filename> <content>`: Create or update a file
  ```
  write file test.txt Hello World!
  write file config.json {"name": "test", "value": 123}
  write file workspace/newfile.txt This is new content
  ```

### Code Analysis and Error Checking
- `analyze <filename>`: Check for errors or issues in code files
  ```
  analyze main.py
  analyze tool_server.py
  ```

## System Features

### Automatic Planning
The system uses an AI model to:
- Analyze your request
- Create an execution plan
- Choose appropriate tools
- Handle failures with fallback strategies

### Error Handling
The system provides detailed error messages for:
- File operations (not found, permission denied)
- Model errors
- Connection issues
- Invalid commands
- Syntax errors

### Retry Mechanisms
- Automatic retry for failed operations
- Smart fallback strategies
- Connection error recovery
- Progress tracking for long operations

## Best Practices

1. File Operations
   - Use relative paths when possible (e.g., `test.txt` instead of full path)
   - Make sure files exist before reading
   - Provide clear content for write operations

2. Model Interactions
   - Ask clear, specific questions
   - Provide context when needed
   - Wait for responses to complete

3. General Usage
   - Commands are case-insensitive
   - Wait for operations to complete before new commands
   - Check error messages if something fails
   - Use proper quotes for content with spaces

## Examples

### Complete Interaction Examples

1. Reading a File:
```
> read file test.txt
Content of test.txt:
this is a file in workspace
```

2. Writing to a File:
```
> write file config.json {"name": "test"}
Successfully wrote to file: config.json
```

3. Asking Questions:
```
> ask what is a Python decorator?
[Detailed explanation with examples will be provided]
```

### Error Examples and Recovery

```
> read file nonexistent.txt
Error: File not found: nonexistent.txt

> write file /invalid/path/file.txt test
Error: Invalid path: Access denied
```

## Notes

- All file operations are workspace-aware
- The system maintains conversation history
- Long operations show progress indicators
- The system can handle multiple tasks in sequence
- Supports both simple and complex queries
