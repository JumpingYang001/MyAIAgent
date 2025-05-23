"""
Model Manager Implementation for MCP Server
Handles model execution and management using JSON-RPC 2.0 protocol
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os

# Set HuggingFace mirror if needed
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self, model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0", device: str = "auto"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() and device == "auto" else "cpu"
        self.model = None
        self.tokenizer = None
        self.execution_history = []
        self.max_length = 2048
        
        # Initialize the model
        if not self.setup_model():
            logger.error("Failed to initialize model")
            raise RuntimeError("Model initialization failed")
        logger.info(f"Model initialized successfully on {self.device}")

    def setup_model(self) -> bool:
        """Initialize and configure the language model"""
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto",
                trust_remote_code=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
            
    async def execute_model(self, method: str, params: Dict) -> Optional[Dict]:
        """Execute a specific model using JSON-RPC 2.0"""
        try:
            # Format as JSON-RPC 2.0 request
            request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": datetime.now().timestamp()
            }
            
            # Generate response
            prompt = params.get("ask", "")
            response = self.generate_response(prompt)
            
            if response:
                self.execution_history.append({
                    "request": request,
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                })
                
                # Format as JSON-RPC 2.0 response
                return {
                    "jsonrpc": "2.0",
                    "result": {"answer": response},
                    "id": request["id"]
                }
            
            self.execution_history.append({
                "request": request,
                "timestamp": datetime.now().isoformat(),
                "success": False
            })
            
            # Format error as JSON-RPC 2.0 response
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error during model execution"
                },
                "id": request["id"]
            }
            
        except Exception as e:
            logger.error(f"Error executing model request: {str(e)}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": request.get("id", None)
            }

    def generate_response(self, prompt: str) -> Optional[str]:
        """Generate response from the model"""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not initialized")
            
        try:            
            # Format prompt for chat format
            formatted_prompt = f"<|user|>\n{prompt}\n<|assistant|>\n"
            
            # Tokenize input
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.device)
            
            # Generate response
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_length,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.2,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Decode and clean up response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response.replace(formatted_prompt, "").strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return None
            
    def cleanup(self):
        """Clean up model resources"""
        try:
            if self.model:
                del self.model
            if self.tokenizer:
                del self.tokenizer
            torch.cuda.empty_cache()
            logger.info("Model resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during model cleanup: {str(e)}")

    async def initialize(self) -> Dict:
        """Initialize the model manager and return capabilities"""
        return {
            "jsonrpc": "2.0",
            "result": {
                "capabilities": {
                    "modelProperties": {
                        "name": "model-manager",
                        "version": "1.0.0",
                        "supportedMethods": ["generate"],
                        "modelType": self.model_name,
                        "device": self.device
                    }
                }
            },
            "id": datetime.now().timestamp()
        }
