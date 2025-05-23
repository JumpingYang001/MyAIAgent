"""
Chat Interface Implementation
Provides a terminal-based chat interface for the AI assistant
"""

import asyncio
import aiohttp
import logging
import prompt_toolkit
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from typing import Dict, Optional
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup rich console
console = Console()

# Prompt styling
style = Style.from_dict({
    'prompt': 'ansiyellow bold',
    'user-input': 'ansigreen',
})

class ChatInterface:
    def __init__(self, model_url: str = "http://localhost:3000/generate",
                 tool_url: str = "http://localhost:3000/api/tools"):
        self.model_url = model_url
        self.tool_url = tool_url
        self.session = PromptSession()
        self.conversation_history = []
        
    async def send_to_model(self, message: str) -> Optional[str]:
        """Send message to the language model"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.model_url,
                    json={"prompt": message, "conversation": self.conversation_history}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response")
            return None
        except Exception as e:
            logger.error(f"Error communicating with model: {str(e)}")
            return None
            
    async def execute_tool(self, tool_name: str, parameters: Dict) -> Optional[Dict]:
        """Execute a tool through the tool server"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.tool_url,
                    json={"name": tool_name, "parameters": parameters}
                ) as response:
                    if response.status == 200:
                        return await response.json()
            return None
        except Exception as e:
            logger.error(f"Error executing tool: {str(e)}")
            return None
            
    def display_response(self, response: str):
        """Display formatted response"""
        if response:
            # Parse response for any code blocks
            try:
                md = Markdown(response)
                console.print(Panel(md, border_style="blue"))
            except Exception:
                console.print(Panel(response, border_style="blue"))
                
    def update_history(self, role: str, content: str):
        """Update conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Keep history size manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
            
    async def start_chat(self):
        """Start the chat interface"""
        console.print("[bold blue]Local AI Assistant Chat[/bold blue]")
        console.print("Type 'exit' to end the conversation\n")
        
        while True:
            try:
                # Get user input
                user_input = await self.session.prompt_async(
                    [('class:prompt', '> ')],
                    style=style
                )
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                    
                # Update history with user input
                self.update_history("user", user_input)
                
                # Send to model and get response
                response = await self.send_to_model(user_input)
                
                if response:
                    # Display response
                    self.display_response(response)
                    
                    # Update history with assistant's response
                    self.update_history("assistant", response)
                else:
                    console.print("[red]Failed to get response from the model[/red]")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in chat interface: {str(e)}")
                console.print(f"[red]Error: {str(e)}[/red]")
                
        console.print("\n[bold blue]Chat session ended[/bold blue]")
        
    def save_history(self, filename: str = "chat_history.json"):
        """Save conversation history to file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, indent=2)
            logger.info(f"Chat history saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving chat history: {str(e)}")

if __name__ == "__main__":
    chat = ChatInterface()
    try:
        asyncio.run(chat.start_chat())
    finally:
        chat.save_history()
