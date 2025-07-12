"""Direct NVIDIA LLM service for coding tasks and IDE integration.

This module provides a clean interface to NVIDIA's LLM API for code generation,
debugging, and other programming tasks without Discord dependencies.
"""

import logging
import os
from typing import Optional, Dict, Any, List
import json

from llama_index.llms.nvidia import NVIDIA
from config.settings import Config


logger = logging.getLogger(__name__)


class NVIDIALLMService:
    """Direct interface to NVIDIA LLM for coding tasks."""
    
    def __init__(self, config: Config):
        """Initialize NVIDIA LLM service.
        
        Args:
            config: Application configuration containing API keys
        """
        self.config = config
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the NVIDIA LLM client."""
        try:
            if not self.config.api.nvidia_api_key:
                raise ValueError("NVIDIA API key is required")
            
            self.llm = NVIDIA(
                model=self.config.api.nvidia_model,
                api_key=self.config.api.nvidia_api_key,
                base_url=self.config.api.nvidia_base_url,
                temperature=0.1,  # Lower temperature for code tasks
                max_tokens=4096   # Higher token limit for code
            )
            
            logger.info(f"NVIDIA LLM service initialized with model: {self.config.api.nvidia_model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize NVIDIA LLM: {e}")
            raise
    
    def generate_code(
        self, 
        prompt: str, 
        language: Optional[str] = None,
        context: Optional[str] = None
    ) -> Optional[str]:
        """Generate code based on a prompt.
        
        Args:
            prompt: Code generation prompt
            language: Programming language (optional)
            context: Additional context (optional)
            
        Returns:
            Generated code or None if failed
        """
        try:
            if not self.llm:
                logger.error("LLM not initialized")
                return None
            
            # Build the full prompt
            full_prompt = self._build_code_prompt(prompt, language, context)
            
            # Generate response
            response = self.llm.complete(full_prompt)
            
            if hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return None
    
    def debug_code(
        self, 
        code: str, 
        error_message: Optional[str] = None,
        language: Optional[str] = None
    ) -> Optional[str]:
        """Debug code and provide suggestions.
        
        Args:
            code: Code to debug
            error_message: Error message if available
            language: Programming language
            
        Returns:
            Debug suggestions or None if failed
        """
        try:
            if not self.llm:
                logger.error("LLM not initialized")
                return None
            
            # Build debug prompt
            debug_prompt = self._build_debug_prompt(code, error_message, language)
            
            # Generate response
            response = self.llm.complete(debug_prompt)
            
            if hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Code debugging failed: {e}")
            return None
    
    def explain_code(self, code: str, language: Optional[str] = None) -> Optional[str]:
        """Explain what a piece of code does.
        
        Args:
            code: Code to explain
            language: Programming language
            
        Returns:
            Code explanation or None if failed
        """
        try:
            if not self.llm:
                logger.error("LLM not initialized")
                return None
            
            prompt = f"""Explain what this code does in clear, concise terms:

{f'Language: {language}' if language else ''}

```
{code}
```

Provide a clear explanation of:
1. What the code does
2. Key functions or methods
3. Important logic or algorithms
4. Any notable patterns or techniques used
"""
            
            response = self.llm.complete(prompt)
            
            if hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Code explanation failed: {e}")
            return None
    
    def chat(self, message: str, context: Optional[str] = None) -> Optional[str]:
        """General chat interface for coding questions.
        
        Args:
            message: User message/question
            context: Optional context or previous conversation
            
        Returns:
            Response or None if failed
        """
        try:
            if not self.llm:
                logger.error("LLM not initialized")
                return None
            
            # Build chat prompt
            if context:
                full_prompt = f"Context: {context}\n\nUser: {message}\n\nAssistant:"
            else:
                full_prompt = f"User: {message}\n\nAssistant:"
            
            response = self.llm.complete(full_prompt)
            
            if hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return None
    
    def _build_code_prompt(
        self, 
        prompt: str, 
        language: Optional[str] = None, 
        context: Optional[str] = None
    ) -> str:
        """Build a structured prompt for code generation."""
        
        parts = ["You are an expert programmer. Generate clean, efficient, well-commented code."]
        
        if language:
            parts.append(f"Language: {language}")
        
        if context:
            parts.append(f"Context: {context}")
        
        parts.append(f"Request: {prompt}")
        parts.append("Provide only the code with minimal explanation unless specifically asked for details.")
        
        return "\n\n".join(parts)
    
    def _build_debug_prompt(
        self, 
        code: str, 
        error_message: Optional[str] = None, 
        language: Optional[str] = None
    ) -> str:
        """Build a structured prompt for code debugging."""
        
        parts = ["You are an expert programmer. Debug this code and provide clear solutions."]
        
        if language:
            parts.append(f"Language: {language}")
        
        if error_message:
            parts.append(f"Error: {error_message}")
        
        parts.append(f"Code:\n```\n{code}\n```")
        parts.append("Provide:\n1. What's wrong\n2. How to fix it\n3. Corrected code if needed")
        
        return "\n\n".join(parts)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration."""
        return {
            'model': self.config.api.nvidia_model,
            'base_url': self.config.api.nvidia_base_url,
            'api_key_configured': bool(self.config.api.nvidia_api_key),
            'initialized': self.llm is not None
        }


def create_llm_service(config: Config) -> NVIDIALLMService:
    """Factory function to create an LLM service instance.
    
    Args:
        config: Application configuration
        
    Returns:
        Initialized LLM service instance
    """
    return NVIDIALLMService(config)