"""
Memory System Implementation for MCP Server
Handles working memory, long-term memory, and context management
"""

from typing import Dict, List, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

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
        # In the future, implement more sophisticated relevance scoring
        return self.context_window[-10:]
        
    def save_state(self, filename: str = "memory_state.json"):
        """Save memory state"""
        try:
            state = {
                "working_memory": self.working_memory,
                "long_term_memory": self.long_term_memory,
                "context_window": self.context_window
            }
            with open(filename, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory state: {str(e)}")
            
    def load_state(self, filename: str = "memory_state.json"):
        """Load memory state"""
        try:
            with open(filename) as f:
                state = json.load(f)
                self.working_memory = state.get("working_memory", {})
                self.long_term_memory = state.get("long_term_memory", [])
                self.context_window = state.get("context_window", [])
        except Exception as e:
            logger.error(f"Error loading memory state: {str(e)}")
