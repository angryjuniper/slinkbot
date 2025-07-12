#!/usr/bin/env python3
"""Example script demonstrating RAG pipeline usage with NVIDIA API.

This script shows how to:
1. Initialize the RAG service with NVIDIA API
2. Ingest documents into the knowledge base
3. Query the RAG system
4. Manage the vector store

Make sure to set your NVIDIA_API_KEY environment variable before running.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import Config
from services.rag_service import create_rag_service
from utils.rag_utils import create_document_processor, RAGUtilities


def main():
    """Main example function."""
    print("🚀 SlinkBot RAG Pipeline Example")
    print("=" * 50)
    
    # Check for NVIDIA API key
    if not os.getenv('NVIDIA_API_KEY'):
        print("❌ Error: NVIDIA_API_KEY environment variable not set!")
        print("Please set your NVIDIA API key:")
        print("export NVIDIA_API_KEY='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'")
        return
    
    try:
        # Initialize configuration and services
        print("📋 Loading configuration...")
        config = Config()
        
        print("🔧 Initializing RAG service...")
        rag_service = create_rag_service(config)
        document_processor = create_document_processor()
        
        # Get index statistics
        print("\n📊 Current Index Statistics:")
        stats = rag_service.get_index_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Example 1: Add sample documents
        print("\n📚 Adding sample documents...")
        sample_documents = [
            {
                'title': 'SlinkBot Overview',
                'content': '''SlinkBot is a Discord bot designed for media management and automation. 
                It integrates with Jellyseerr, Radarr, and Sonarr to provide seamless media request handling. 
                The bot supports movie and TV show requests, download monitoring, and status notifications.'''
            },
            {
                'title': 'RAG System Guide',
                'content': '''The RAG (Retrieval Augmented Generation) system allows SlinkBot to answer questions 
                using a knowledge base of documents. It uses NVIDIA's LLM API for generation and ChromaDB for 
                vector storage. Users can add documents and query the system through Discord commands.'''
            },
            {
                'title': 'NVIDIA API Integration',
                'content': '''SlinkBot integrates with NVIDIA's developer API to provide LLM capabilities. 
                The integration supports the Llama 3.3 70B model and can be configured through environment variables. 
                The API key format is nvapi-followed by the actual key.'''
            }
        ]
        
        # Create and add documents
        documents = []
        for doc_data in sample_documents:
            doc = document_processor.create_document_from_text(
                text=doc_data['content'],
                metadata={
                    'title': doc_data['title'],
                    'source': 'example_script',
                    'category': 'documentation'
                }
            )
            documents.append(doc)
        
        success = rag_service.add_documents(documents)
        if success:
            print(f"✅ Successfully added {len(documents)} documents to the knowledge base")
        else:
            print("❌ Failed to add documents")
            return
        
        # Example 2: Query the system
        print("\n🤖 Testing RAG queries...")
        
        test_queries = [
            "What is SlinkBot?",
            "How does the RAG system work?",
            "What NVIDIA API does SlinkBot use?",
            "How do I configure the NVIDIA API key?"
        ]
        
        for query in test_queries:
            print(f"\n❓ Query: {query}")
            
            # Get response from RAG system
            response = rag_service.query(query)
            if response:
                print(f"💡 Response: {response}")
                
                # Get relevant documents
                sources = rag_service.get_relevant_documents(query, top_k=2)
                if sources:
                    print("📄 Top sources:")
                    for i, source in enumerate(sources, 1):
                        score = source.get('score', 0.0)
                        title = source.get('metadata', {}).get('title', 'Unknown')
                        print(f"  {i}. {title} (Score: {score:.3f})")
            else:
                print("❌ No response generated")
        
        # Example 3: Search without generation
        print("\n🔍 Testing document search...")
        search_query = "media management"
        search_results = rag_service.get_relevant_documents(search_query, top_k=3)
        
        print(f"Search query: {search_query}")
        print(f"Found {len(search_results)} relevant documents:")
        
        for i, result in enumerate(search_results, 1):
            title = result.get('metadata', {}).get('title', 'Unknown')
            score = result.get('score', 0.0)
            content = result.get('content', '')[:100] + '...'
            print(f"  {i}. {title} (Score: {score:.3f})")
            print(f"     Preview: {content}")
        
        # Example 4: Format response with sources
        print("\n📝 Testing formatted response...")
        test_response = rag_service.query("Explain SlinkBot's main features")
        if test_response:
            sources = rag_service.get_relevant_documents("SlinkBot features", top_k=2)
            formatted = RAGUtilities.format_rag_response(
                response=test_response,
                sources=sources,
                include_sources=True
            )
            
            print("Formatted Response:")
            print(f"Response: {formatted['response']}")
            print(f"Source Count: {formatted.get('source_count', 0)}")
            
            for i, source in enumerate(formatted.get('sources', []), 1):
                print(f"Source {i}: {source['content_preview']}")
        
        # Final statistics
        print("\n📊 Final Index Statistics:")
        final_stats = rag_service.get_index_stats()
        for key, value in final_stats.items():
            print(f"  {key}: {value}")
        
        print("\n✅ RAG pipeline example completed successfully!")
        print("\nNext steps:")
        print("1. Add your own documents using rag_service.ingest_directory()")
        print("2. Use the Discord commands: /rag_query, /rag_ingest_text, /rag_stats")
        print("3. Configure additional models or embedding providers")
        
    except Exception as e:
        print(f"❌ Error during RAG example: {e}")
        raise


if __name__ == "__main__":
    main()