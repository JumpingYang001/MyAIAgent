"""
Server Manager for MCP Client
Handles server discovery, configuration, and management
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path
import logging
from dataclasses import dataclass
import yaml

logger = logging.getLogger(__name__)

@dataclass
class ServerConfig:
    name: str
    type: str
    command: str
    args: List[str]
    capabilities: List[str]

class ServerManager:
    def __init__(self, config_path: str = "server_config.json"):
        self.config_path = config_path
        self.servers: Dict[str, ServerConfig] = {}
        self.load_config()

    def load_config(self):
        """Load server configurations"""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
                for name, info in config.get("servers", {}).items():
                    self.servers[name] = ServerConfig(
                        name=name,
                        type=info.get("type", "unknown"),
                        command=info.get("command", ""),
                        args=info.get("args", []),
                        capabilities=info.get("capabilities", [])
                    )
                logger.info(f"Loaded {len(self.servers)} server configurations")
        except Exception as e:
            logger.error(f"Error loading server config: {str(e)}")

    def get_server(self, name: str) -> Optional[ServerConfig]:
        """Get server configuration by name"""
        return self.servers.get(name)

    def list_servers(self) -> List[str]:
        """List available servers"""
        return list(self.servers.keys())

    def get_servers_by_capability(self, capability: str) -> List[ServerConfig]:
        """Find servers that support a specific capability"""
        return [
            server for server in self.servers.values()
            if capability in server.capabilities
        ]

    def add_server(self, name: str, config: Dict) -> bool:
        """Add a new server configuration"""
        try:
            self.servers[name] = ServerConfig(
                name=name,
                type=config.get("type", "unknown"),
                command=config.get("command", ""),
                args=config.get("args", []),
                capabilities=config.get("capabilities", [])
            )
            self._save_config()
            return True
        except Exception as e:
            logger.error(f"Error adding server {name}: {str(e)}")
            return False

    def remove_server(self, name: str) -> bool:
        """Remove a server configuration"""
        if name in self.servers:
            del self.servers[name]
            self._save_config()
            return True
        return False

    def _save_config(self):
        """Save current configuration to file"""
        try:
            config = {
                "servers": {
                    name: {
                        "type": server.type,
                        "command": server.command,
                        "args": server.args,
                        "capabilities": server.capabilities
                    }
                    for name, server in self.servers.items()
                }
            }
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
