"""
Tool Manager Implementation for MCP Server
Handles tool execution and management using JSON-RPC 2.0 protocol
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import subprocess
import os
import yaml
from functools import wraps
import asyncio
from fnmatch import fnmatch

# Setup logging
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from yaml file"""
    config_path = Path("config.yaml")
    if not config_path.exists():
        default_config = {
            "workspace_root": "./workspace",
            "allowed_commands": ["git", "npm", "python", "pip"],
            "security": {
                "max_file_size_mb": 10,
                "request_timeout_seconds": 30
            }
        }
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f)
        return default_config
    
    with open(config_path) as f:
        return yaml.safe_load(f)

def with_retry(max_retries=3, delay=1):
    """Decorator for adding retry logic to async functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

class ToolManager:
    def __init__(self):
        self.config = load_config()
        self.workspace_root = Path(self.config["workspace_root"]).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.allowed_commands = set(self.config["allowed_commands"])
        self.execution_history = []
        logger.info(f"Initialized ToolManager with workspace: {self.workspace_root}")

    def validate_path(self, path: str) -> Path:
        """Validate and resolve file path"""
        try:
            input_path = Path(path)
            if input_path.is_absolute():
                full_path = input_path
            else:
                full_path = (self.workspace_root / input_path).resolve()
                
            if not str(full_path).startswith(str(self.workspace_root)):
                raise ValueError(f"Access denied: Path {path} outside workspace")
                
            return full_path
            
        except Exception as e:
            logger.error(f"Path validation error: {str(e)}")
            raise ValueError(f"Invalid path: {str(e)}")

    @with_retry()
    async def execute_tool(self, method: str, params: Dict) -> Dict:
        """Execute tool using JSON-RPC 2.0"""
        try:
            request_id = datetime.now().timestamp()
            
            result = await self._handle_method(method, params)
            
            self.execution_history.append({
                "method": method,
                "params": params,
                "timestamp": datetime.now().isoformat(),
                "success": True
            })
            
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
            
        except Exception as e:
            logger.error(f"Error executing {method}: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request_id
            }

    async def _handle_method(self, method: str, params: Dict) -> Dict:
        """Handle different tool methods"""
        if method == "read_file":
            return await self.read_file(params)
        elif method == "write_file":
            return await self.write_file(params)
        elif method == "execute_command":
            return await self.execute_command(params)
        elif method == "search_code":
            return await self.search_code(params)
        elif method == "file_search":
            return await self.search_files(params)
        elif method == "get_errors":
            return await self.check_errors(params)
        else:
            raise ValueError(f"Unknown method: {method}")

    async def read_file(self, params: Dict) -> Dict:
        """Read file contents"""
        try:
            path = self.validate_path(params["path"])
            
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            logger.info(f"Reading file: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "start_line" in params and "end_line" in params:
                lines = content.splitlines()
                content = '\n'.join(lines[params["start_line"]:params["end_line"] + 1])
            
            return {"content": content}
            
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise

    async def write_file(self, params: Dict) -> Dict:
        """Write file contents"""
        try:
            path = self.validate_path(params["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(params["content"])
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error writing file: {str(e)}")
            raise

    async def execute_command(self, params: Dict) -> Dict:
        """Execute terminal command"""
        try:
            command_parts = params["command"].split()
            if command_parts[0] not in self.allowed_commands:
                raise ValueError("Command not allowed")
            
            result = subprocess.run(
                command_parts,
                cwd=params.get("cwd", str(self.workspace_root)),
                capture_output=True,
                text=True,
                timeout=params.get("timeout", self.config["security"]["request_timeout_seconds"])
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            raise TimeoutError("Command timed out")
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            raise

    async def search_code(self, params: Dict) -> Dict:
        """Search code in workspace"""
        try:
            results = []
            pattern = params.get("file_pattern", "**/*")
            query = params["query"].lower()
            
            for file in self.workspace_root.rglob(pattern):
                if file.is_file():
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if query in content.lower():
                                results.append({
                                    "file": str(file.relative_to(self.workspace_root)),
                                    "matches": content.count(query)
                                })
                    except Exception:
                        continue
            
            return {"results": results}
            
        except Exception as e:
            logger.error(f"Error searching code: {str(e)}")
            raise

    async def search_files(self, params: Dict) -> Dict:
        """Search for files matching pattern"""
        try:
            pattern = params.get("pattern", "**/*")
            logger.info(f"Searching for files matching pattern: {pattern}")
            
            if not pattern.startswith('./') and not pattern.startswith('*/'): 
                pattern = '**/' + pattern
                
            pattern = pattern.replace('\\', '/')
            
            matches = []
            for root, dirs, files in os.walk(self.workspace_root):
                rel_path = Path(root).relative_to(self.workspace_root)
                for file in files:
                    file_path = rel_path / file
                    if self._matches_pattern(str(file_path), pattern.split('/')):
                        matches.append(str(file_path))
            
            return {"files": matches}
            
        except Exception as e:
            logger.error(f"Error searching files: {str(e)}")
            raise

    def _matches_pattern(self, path: str, pattern_parts: List[str]) -> bool:
        """Check if path matches pattern parts"""
        path_parts = path.split(os.sep)
        if len(pattern_parts) > len(path_parts):
            return False
        return all(
            fnmatch(part, pattern)
            for part, pattern in zip(path_parts[-len(pattern_parts):], pattern_parts)
        )

    async def check_errors(self, params: Dict) -> Dict:
        """Check for errors in files"""
        errors = []
        for file_path in params.get("filePaths", []):
            try:
                full_path = (self.workspace_root / file_path).resolve()
                if not str(full_path).startswith(str(self.workspace_root)):
                    continue
                
                if full_path.suffix == '.py':
                    try:
                        with open(full_path) as f:
                            compile(f.read(), str(full_path), 'exec')
                    except Exception as e:
                        errors.append({
                            "file": str(file_path),
                            "line": getattr(e, 'lineno', None),
                            "message": str(e)
                        })
                        
            except Exception as e:
                logger.error(f"Error checking {file_path}: {str(e)}")
                
        return {"errors": errors}
