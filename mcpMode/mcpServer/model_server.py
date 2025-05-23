"""
Model Server Implementation for MCP
Provides a JSON-RPC 2.0 interface for model operations
"""

import sys
import json
import logging
from typing import Dict, Any
from model_manager import ModelManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

class ModelServer:
    def __init__(self):
        self.model_manager = None
        self.initialized = False
        self.methods = {
            "initialize": self.initialize,
            "generate": self.generate,
            "model_info": self.get_model_info
        }

    async def initialize(self, params: Dict = None) -> Dict:
        """Initialize the model server"""
        try:
            self.model_manager = ModelManager()
            self.initialized = True
            return {
                "capabilities": {
                    "supportedMethods": ["generate", "model_info"],
                    "modelProperties": {
                        "name": self.model_manager.model_name,
                        "device": self.model_manager.device,
                        "maxLength": self.model_manager.max_length
                    }
                }
            }
        except Exception as e:
            logger.error(f"Initialization failed: {str(e)}")
            return {"error": str(e)}

    async def generate(self, params: Dict) -> Dict:
        """Generate text using the model"""
        if not self.initialized:
            return {"error": "Server not initialized"}
        
        try:
            prompt = params.get("ask", "")
            if not prompt:
                return {"error": "No prompt provided"}
                
            # Generate response using the model
            inputs = self.model_manager.tokenizer(prompt, return_tensors="pt").to(self.model_manager.device)
            outputs = self.model_manager.model.generate(
                inputs["input_ids"],
                max_length=self.model_manager.max_length,
                temperature=0.7,
                do_sample=True
            )
            response = self.model_manager.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return {
                "answer": response,
                "model": self.model_manager.model_name
            }
            
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            return {"error": str(e)}

    async def get_model_info(self, params: Dict = None) -> Dict:
        """Get information about the current model"""
        if not self.initialized:
            return {"error": "Server not initialized"}
            
        return {
            "name": self.model_manager.model_name,
            "device": self.model_manager.device,
            "maxLength": self.model_manager.max_length
        }

    async def handle_request(self, request: Dict) -> Dict:
        """Handle an incoming JSON-RPC request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method not in self.methods:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method {method} not found"},
                "id": request_id
            }
            
        try:
            result = await self.methods[method](params)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": request_id
            }

async def main():
    """Main entry point for the model server"""
    server = ModelServer()
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            try:
                request = json.loads(line)
                response = await server.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
                continue
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            break

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
