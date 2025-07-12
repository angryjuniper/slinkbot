#!/usr/bin/env python3
import sys
from openai import OpenAI
from simple_rag import SimpleRAG

class NVIDIAChat:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="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"
        )
        self.rag = SimpleRAG("nvidia")  # For codebase context
        
    def chat(self, message, use_rag=True):
        if use_rag:
            # Get relevant codebase context
            rag_result = self.rag.ask(message)
            context = f"Context from codebase:\n{rag_result['answer']}\n\nSource files: {', '.join(rag_result['sources'])}\n\n"
            full_message = context + f"User question: {message}"
        else:
            full_message = message
            
        try:
            completion = self.client.chat.completions.create(
                model="meta/llama-3.3-70b-instruct",
                messages=[{"role": "user", "content": full_message}],
                temperature=0.1,
                max_tokens=2048
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python nvidia_chat.py <your_question>")
        print("   or: python nvidia_chat.py --no-rag <your_question>")
        return
    
    chat = NVIDIAChat()
    
    if sys.argv[1] == "--no-rag":
        question = " ".join(sys.argv[2:])
        use_rag = False
    else:
        question = " ".join(sys.argv[1:])
        use_rag = True
    
    print(f"🤖 NVIDIA Llama 3.3 70B {'(with codebase context)' if use_rag else '(direct chat)'}")
    print("-" * 60)
    
    response = chat.chat(question, use_rag)
    print(response)

if __name__ == "__main__":
    main()
