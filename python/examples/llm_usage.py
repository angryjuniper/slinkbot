#!/usr/bin/env python3
"""Example usage of the NVIDIA LLM service for coding tasks.

This script demonstrates how to use the LLM service programmatically
for code generation, debugging, and explanation tasks.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import load_config
from services.llm_service import create_llm_service


def main():
    """Demonstrate LLM service usage."""
    print("🤖 NVIDIA LLM Service Example")
    print("=" * 40)
    
    # Check for API key
    if not os.getenv('NVIDIA_API_KEY'):
        print("❌ Error: NVIDIA_API_KEY environment variable not set!")
        print("Set it with: export NVIDIA_API_KEY='your-key-here'")
        return
    
    try:
        # Initialize service
        config = load_config()
        llm = create_llm_service(config)
        
        # Show model info
        print("📋 Model Information:")
        info = llm.get_model_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
        print()
        
        # Example 1: Code generation
        print("🔧 Code Generation Example:")
        code_prompt = "Create a Python function that calculates the factorial of a number using recursion"
        
        generated_code = llm.generate_code(
            prompt=code_prompt,
            language="python"
        )
        
        if generated_code:
            print("Generated code:")
            print(generated_code)
        else:
            print("Failed to generate code")
        print("-" * 40)
        
        # Example 2: Code debugging
        print("🐛 Code Debugging Example:")
        buggy_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# This will be slow for large n
result = fibonacci(100)  # This will take forever!
print(result)
"""
        
        debug_response = llm.debug_code(
            code=buggy_code,
            error_message="Function takes too long to execute for large inputs",
            language="python"
        )
        
        if debug_response:
            print("Debug analysis:")
            print(debug_response)
        else:
            print("Failed to debug code")
        print("-" * 40)
        
        # Example 3: Code explanation
        print("📖 Code Explanation Example:")
        complex_code = """
from functools import lru_cache

@lru_cache(maxsize=None)
def fibonacci_optimized(n):
    if n <= 1:
        return n
    return fibonacci_optimized(n-1) + fibonacci_optimized(n-2)
"""
        
        explanation = llm.explain_code(
            code=complex_code,
            language="python"
        )
        
        if explanation:
            print("Code explanation:")
            print(explanation)
        else:
            print("Failed to explain code")
        print("-" * 40)
        
        # Example 4: General chat
        print("💬 Chat Example:")
        chat_response = llm.chat(
            message="What are the best practices for error handling in Python?",
            context="I'm working on a web application and want to make it robust"
        )
        
        if chat_response:
            print("LLM response:")
            print(chat_response)
        else:
            print("Failed to get chat response")
        
        print("\n✅ All examples completed!")
        print("\n🚀 Usage with CLI tool:")
        print("  python tools/llm_cli.py generate 'Create a FastAPI endpoint'")
        print("  python tools/llm_cli.py debug --file buggy_code.py")
        print("  python tools/llm_cli.py explain --code 'def example(): pass'")
        print("  python tools/llm_cli.py chat 'How do I optimize this algorithm?'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()