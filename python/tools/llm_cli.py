#!/usr/bin/env python3
"""Command-line interface for NVIDIA LLM service.

This CLI tool allows you to interact with the NVIDIA LLM from the command line,
which can be useful for IDE integration or automation.
"""

import argparse
import sys
from pathlib import Path
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import load_config
from services.llm_service import create_llm_service


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="NVIDIA LLM CLI Tool")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Code generation command
    gen_parser = subparsers.add_parser('generate', help='Generate code')
    gen_parser.add_argument('prompt', help='Code generation prompt')
    gen_parser.add_argument('--language', '-l', help='Programming language')
    gen_parser.add_argument('--context', '-c', help='Additional context')
    gen_parser.add_argument('--file', '-f', help='Read prompt from file')
    
    # Debug command
    debug_parser = subparsers.add_parser('debug', help='Debug code')
    debug_parser.add_argument('--code', help='Code to debug')
    debug_parser.add_argument('--file', '-f', help='Read code from file')
    debug_parser.add_argument('--error', '-e', help='Error message')
    debug_parser.add_argument('--language', '-l', help='Programming language')
    
    # Explain command
    explain_parser = subparsers.add_parser('explain', help='Explain code')
    explain_parser.add_argument('--code', help='Code to explain')
    explain_parser.add_argument('--file', '-f', help='Read code from file')
    explain_parser.add_argument('--language', '-l', help='Programming language')
    
    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Chat with LLM')
    chat_parser.add_argument('message', help='Your message')
    chat_parser.add_argument('--context', '-c', help='Additional context')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show model information')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Load configuration and create LLM service
        config = load_config()
        llm_service = create_llm_service(config)
        
        if args.command == 'generate':
            # Read prompt from file if specified
            if args.file:
                with open(args.file, 'r') as f:
                    prompt = f.read()
            else:
                prompt = args.prompt
            
            response = llm_service.generate_code(
                prompt=prompt,
                language=args.language,
                context=args.context
            )
            
            if response:
                print(response)
            else:
                print("Failed to generate code", file=sys.stderr)
                sys.exit(1)
        
        elif args.command == 'debug':
            # Read code from file if specified
            if args.file:
                with open(args.file, 'r') as f:
                    code = f.read()
            else:
                code = args.code
            
            if not code:
                print("Error: No code provided. Use --code or --file", file=sys.stderr)
                sys.exit(1)
            
            response = llm_service.debug_code(
                code=code,
                error_message=args.error,
                language=args.language
            )
            
            if response:
                print(response)
            else:
                print("Failed to debug code", file=sys.stderr)
                sys.exit(1)
        
        elif args.command == 'explain':
            # Read code from file if specified
            if args.file:
                with open(args.file, 'r') as f:
                    code = f.read()
            else:
                code = args.code
            
            if not code:
                print("Error: No code provided. Use --code or --file", file=sys.stderr)
                sys.exit(1)
            
            response = llm_service.explain_code(
                code=code,
                language=args.language
            )
            
            if response:
                print(response)
            else:
                print("Failed to explain code", file=sys.stderr)
                sys.exit(1)
        
        elif args.command == 'chat':
            response = llm_service.chat(
                message=args.message,
                context=args.context
            )
            
            if response:
                print(response)
            else:
                print("Failed to get response", file=sys.stderr)
                sys.exit(1)
        
        elif args.command == 'info':
            info = llm_service.get_model_info()
            print("NVIDIA LLM Configuration:")
            for key, value in info.items():
                print(f"  {key}: {value}")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()