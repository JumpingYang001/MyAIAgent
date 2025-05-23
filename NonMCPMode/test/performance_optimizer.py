"""
Performance Optimization Implementation
Handles caching, batching, and performance monitoring
"""

import time
import logging
import psutil
import threading
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache
from dataclasses import dataclass
import numpy as np
from collections import deque
import torch
import gc
from pathlib import Path
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    response_time: float
    memory_usage: float
    cpu_usage: float
    gpu_usage: Optional[float]
    token_throughput: float

class PerformanceOptimizer:
    def __init__(self, cache_size: int = 1000, 
                 batch_size: int = 4,
                 metrics_window: int = 100):
        self.cache_size = cache_size
        self.batch_size = batch_size
        self.metrics_window = metrics_window
        self.metrics_history: deque = deque(maxlen=metrics_window)
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        
    def start_monitoring(self):
        """Start performance monitoring in background thread"""
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(target=self._monitor_performance)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
    def stop_monitoring(self):
        """Stop performance monitoring"""
        if self.monitoring_thread:
            self.stop_monitoring.set()
            self.monitoring_thread.join()
            
    def _monitor_performance(self):
        """Continuous performance monitoring"""
        while not self.stop_monitoring.is_set():
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                self._analyze_metrics()
                time.sleep(1)  # Collect metrics every second
            except Exception as e:
                logger.error(f"Error monitoring performance: {str(e)}")
                
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        try:
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # Get GPU usage if available
            gpu_usage = None
            if torch.cuda.is_available():
                gpu_usage = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated()
                
            return PerformanceMetrics(
                response_time=0.0,  # Will be updated when processing requests
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                gpu_usage=gpu_usage,
                token_throughput=0.0  # Will be updated when processing requests
            )
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
            return None
            
    def _analyze_metrics(self):
        """Analyze metrics and trigger optimizations if needed"""
        if len(self.metrics_history) < 10:
            return
            
        recent_metrics = list(self.metrics_history)[-10:]
        
        # Check memory usage trend
        memory_trend = [m.memory_usage for m in recent_metrics]
        if np.mean(memory_trend) > 0.8 * psutil.virtual_memory().total:
            self._optimize_memory()
            
        # Check CPU usage trend
        cpu_trend = [m.cpu_usage for m in recent_metrics]
        if np.mean(cpu_trend) > 80:
            self._optimize_cpu()
            
        # Check GPU usage if available
        if torch.cuda.is_available():
            gpu_trend = [m.gpu_usage for m in recent_metrics if m.gpu_usage is not None]
            if gpu_trend and np.mean(gpu_trend) > 0.8:
                self._optimize_gpu()
                
    @lru_cache(maxsize=1000)
    def cache_result(self, input_text: str) -> str:
        """Cache results for repeated queries"""
        return input_text  # Placeholder for actual result
        
    def batch_requests(self, requests: List[str]) -> List[str]:
        """Batch multiple requests for efficient processing"""
        batched_results = []
        for i in range(0, len(requests), self.batch_size):
            batch = requests[i:i + self.batch_size]
            # Process batch (implement actual batch processing logic)
            batched_results.extend(batch)
        return batched_results
        
    def _optimize_memory(self):
        """Optimize memory usage"""
        logger.info("Optimizing memory usage...")
        
        # Clear Python garbage collector
        gc.collect()
        
        # Clear torch cache if using GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        # Clear LRU cache if too large
        if len(self.cache_result.cache_info().currsize) > self.cache_size:
            self.cache_result.cache_clear()
            
    def _optimize_cpu(self):
        """Optimize CPU usage"""
        logger.info("Optimizing CPU usage...")
        
        # Adjust batch size based on CPU load
        if self.batch_size > 1 and psutil.cpu_percent() > 80:
            self.batch_size = max(1, self.batch_size - 1)
        elif psutil.cpu_percent() < 50:
            self.batch_size = min(8, self.batch_size + 1)
            
    def _optimize_gpu(self):
        """Optimize GPU usage"""
        logger.info("Optimizing GPU usage...")
        
        if torch.cuda.is_available():
            # Clear GPU cache
            torch.cuda.empty_cache()
            
            # Adjust batch size based on GPU memory
            memory_used = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated()
            if memory_used > 0.8 and self.batch_size > 1:
                self.batch_size = max(1, self.batch_size - 1)
            elif memory_used < 0.5:
                self.batch_size = min(8, self.batch_size + 1)
                
    def measure_request_performance(self, func):
        """Decorator to measure request performance"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            # Update metrics
            response_time = end_time - start_time
            self.metrics_history[-1].response_time = response_time
            
            # Log performance data
            logger.info(f"Request processed in {response_time:.2f} seconds")
            return result
        return wrapper
        
    def save_metrics(self, filename: str = "performance_metrics.json"):
        """Save performance metrics to file"""
        try:
            metrics_data = [
                {
                    "timestamp": time.time(),
                    "response_time": m.response_time,
                    "memory_usage": m.memory_usage,
                    "cpu_usage": m.cpu_usage,
                    "gpu_usage": m.gpu_usage,
                    "token_throughput": m.token_throughput
                }
                for m in self.metrics_history
            ]
            
            with open(filename, 'w') as f:
                json.dump(metrics_data, f, indent=2)
                
            logger.info(f"Performance metrics saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving metrics: {str(e)}")

if __name__ == "__main__":
    # Example usage
    optimizer = PerformanceOptimizer()
    
    try:
        # Start performance monitoring
        optimizer.start_monitoring()
        
        # Example of measuring function performance
        @optimizer.measure_request_performance
        def example_request():
            time.sleep(1)  # Simulate work
            return "Response"
            
        # Test request
        response = example_request()
        
        # Save metrics
        optimizer.save_metrics()
        
    finally:
        # Stop monitoring
        optimizer.stop_monitoring()
