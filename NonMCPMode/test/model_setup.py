"""
Language Model Setup Script
Handles downloading, configuring and running the local language model
"""

import os
# mirror, if this doesn't work please set it manually.
os.environ["HF_ENDPOINT"]="https://hf-mirror.com"
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#python model_setup.py
#INFO:__main__:Setting up model deepseek-ai/DeepSeek-V3-0324 on cpu
#ERROR:__main__:Error loading model: No package metadata was found for bitsandbytes
#C:\Users\mci-user\AppData\Local\Programs\Python\Python313\Lib\site-packages\transformers\utils\import_utils.py
#pip install bitsandbytes

class ModelSetup:
    # others: deepseek-ai/DeepSeek-V3-0324
    #ERROR:__main__:Error loading model: FP8 quantized models is only supported on GPUs with compute capability >= 8.9 (e.g 4090/H100), actual = `6.1`
    #This is because GTX 1050 requires that, so I test it with another model.
    #codellama/CodeLlama-7b-Instruct-hf seems be big size, i try below small size.
    #microsoft/DialoGPT-small
    #microsoft/DialoGPT-medium
    #openai-community/gpt2
    #TinyLlama/TinyLlama-1.1B-Chat-v1.0
    #run "huggingface-cli download --resume-download microsoft/DialoGPT-small --local-dir microsoft/DialoGPT-small" according to https://hf-mirror.com/
    def __init__(self, model_name="microsoft/DialoGPT-small", 
                 device="auto", 
                 quantization="other"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() and device == "auto" else "cpu"
        self.quantization = quantization
        self.model = None
        self.tokenizer = None
        
    def setup_model(self):
        """Initialize and configure the language model"""
        logger.info(f"Setting up model {self.model_name} on {self.device}")
        #If you meet below error, please enable developer mode on Windows: Setting>Update&Secuirty>For developers>Turn on "Developer Mode".
        #reason is that loading json failed when load json file resolved_config_file in get_tokenizer_config by AutoTokenizer.from_pretrained: C:\Users\mci-user\.cache\huggingface\hub\models--microsoft--DialoGPT-small\snapshots\49c537161a457d5256512f9d2d38a87d81ae0f0e\tokenizer_config.json
        #python model_setup.py
        #INFO:__main__:Setting up model microsoft/DialoGPT-small on cuda
        #ERROR:__main__:Error loading model: Expecting value: line 1 column 1 (char 0)
        #cache_dir="C:\\Users\\myname\\.cache\\huggingface\\hub"
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                #cache_dir=cache_dir,
                trust_remote_code=True
            )
            print("AutoModelForCausalLM.from_pretrained")
            # Load model with quantization if specified
            if self.quantization == "4bit":
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    trust_remote_code=True,
                    #cache_dir=cache_dir,
                    load_in_4bit=True
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    #cache_dir=cache_dir,
                    trust_remote_code=True
                )
                
            logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
            
    def generate_response(self, prompt, max_length=2048):
        """Generate response from the model"""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not initialized. Call setup_model first.")
            
        try:
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Generate response
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                num_return_sequences=1,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return None

    def cleanup(self):
        """Clean up resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        torch.cuda.empty_cache()
        logger.info("Model resources cleaned up")

if __name__ == "__main__":
    # Example usage
    model_setup = ModelSetup()
    if model_setup.setup_model():
        try:
            # Test generation
            response = model_setup.generate_response(
                #"Write a function to calculate fibonacci numbers."
                "hello, who are you?"
            )
            logger.info(f"Generated response:{response}")
        finally:
            model_setup.cleanup()
