"""RAG (Retrieval Augmented Generation) service using NVIDIA API and ChromaDB.

This module provides RAG capabilities for SlinkBot using NVIDIA's LLM API
and ChromaDB for vector storage and retrieval.
"""

import logging
import os
from typing import List, Optional, Dict, Any
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    SimpleDirectoryReader,
    Document
)
from llama_index.llms.nvidia import NVIDIA
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.response.schema import Response
import chromadb
from chromadb.config import Settings

from config.settings import Config


logger = logging.getLogger(__name__)


class RAGService:
    """RAG service for document ingestion, indexing, and querying using NVIDIA LLM."""
    
    def __init__(self, config: Config):
        """Initialize RAG service with configuration.
        
        Args:
            config: Application configuration containing API keys and settings
        """
        self.config = config
        self.llm = None
        self.embedding_model = None
        self.vector_store = None
        self.index = None
        self.query_engine = None
        
        # ChromaDB settings
        self.chroma_path = "data/chroma_db"
        self.collection_name = "slinkbot_documents"
        
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize LLM, embeddings, and vector store."""
        try:
            # Initialize NVIDIA LLM
            if not self.config.api.nvidia_api_key:
                raise ValueError("NVIDIA API key is required for RAG service")
                
            self.llm = NVIDIA(
                model=self.config.api.nvidia_model,
                api_key=self.config.api.nvidia_api_key,
                base_url=self.config.api.nvidia_base_url,
                temperature=0.2,
                max_tokens=1024
            )
            
            # Initialize OpenAI embeddings (you can replace with NVIDIA embeddings if available)
            # For now using OpenAI embeddings - you may want to configure this separately
            self.embedding_model = OpenAIEmbedding(
                model="text-embedding-ada-002",
                api_key=os.getenv("OPENAI_API_KEY", "")  # Optional for embeddings
            )
            
            # Initialize ChromaDB
            self._initialize_chroma()
            
            logger.info("RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise
    
    def _initialize_chroma(self):
        """Initialize ChromaDB vector store."""
        try:
            # Ensure ChromaDB directory exists
            Path(self.chroma_path).mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB client
            chroma_client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            chroma_collection = chroma_client.get_or_create_collection(
                name=self.collection_name
            )
            
            # Initialize vector store
            self.vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            
            # Create storage context
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            
            # Try to load existing index or create new one
            try:
                self.index = VectorStoreIndex.from_vector_store(
                    vector_store=self.vector_store,
                    embed_model=self.embedding_model
                )
                logger.info("Loaded existing vector index")
            except Exception:
                # Create empty index if none exists
                self.index = VectorStoreIndex(
                    [],
                    storage_context=storage_context,
                    embed_model=self.embedding_model
                )
                logger.info("Created new vector index")
            
            # Create query engine
            self.query_engine = self.index.as_query_engine(
                llm=self.llm,
                similarity_top_k=5,
                response_mode="compact"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to the vector store.
        
        Args:
            documents: List of Document objects to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not documents:
                logger.warning("No documents provided to add")
                return False
            
            # Add documents to index
            for doc in documents:
                self.index.insert(doc)
            
            logger.info(f"Added {len(documents)} documents to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False
    
    def ingest_directory(self, directory_path: str, file_extensions: Optional[List[str]] = None) -> bool:
        """Ingest documents from a directory.
        
        Args:
            directory_path: Path to directory containing documents
            file_extensions: List of file extensions to include (e.g., ['.txt', '.md'])
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(directory_path):
                logger.error(f"Directory not found: {directory_path}")
                return False
            
            # Set default file extensions if not provided
            if file_extensions is None:
                file_extensions = ['.txt', '.md', '.pdf', '.docx']
            
            # Read documents from directory
            reader = SimpleDirectoryReader(
                input_dir=directory_path,
                file_extractor={ext: None for ext in file_extensions},
                recursive=True
            )
            
            documents = reader.load_data()
            
            if not documents:
                logger.warning(f"No documents found in {directory_path}")
                return False
            
            # Add documents to vector store
            return self.add_documents(documents)
            
        except Exception as e:
            logger.error(f"Failed to ingest directory {directory_path}: {e}")
            return False
    
    def query(self, question: str, context: Optional[str] = None) -> Optional[str]:
        """Query the RAG system with a question.
        
        Args:
            question: Question to ask
            context: Optional additional context to include
            
        Returns:
            Response text or None if query failed
        """
        try:
            if not self.query_engine:
                logger.error("Query engine not initialized")
                return None
            
            # Prepare query with optional context
            if context:
                full_query = f"Context: {context}\n\nQuestion: {question}"
            else:
                full_query = question
            
            # Execute query
            response = self.query_engine.query(full_query)
            
            if response and hasattr(response, 'response'):
                return response.response
            else:
                logger.warning("Empty response from query engine")
                return None
                
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return None
    
    def get_relevant_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query without generating a response.
        
        Args:
            query: Search query
            top_k: Number of top documents to return
            
        Returns:
            List of relevant documents with metadata
        """
        try:
            if not self.index:
                logger.error("Index not initialized")
                return []
            
            # Create a retriever
            retriever = self.index.as_retriever(similarity_top_k=top_k)
            
            # Retrieve relevant nodes
            nodes = retriever.retrieve(query)
            
            # Convert nodes to dict format
            documents = []
            for node in nodes:
                doc_dict = {
                    'content': node.text,
                    'score': node.score if hasattr(node, 'score') else 0.0,
                    'metadata': node.metadata if hasattr(node, 'metadata') else {}
                }
                documents.append(doc_dict)
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            return []
    
    def clear_index(self) -> bool:
        """Clear all documents from the vector store.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.vector_store:
                # Reset the collection
                chroma_client = chromadb.PersistentClient(path=self.chroma_path)
                chroma_client.delete_collection(name=self.collection_name)
                
                # Reinitialize
                self._initialize_chroma()
                
                logger.info("Vector store cleared successfully")
                return True
            else:
                logger.warning("Vector store not initialized")
                return False
                
        except Exception as e:
            logger.error(f"Failed to clear vector store: {e}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index.
        
        Returns:
            Dictionary containing index statistics
        """
        try:
            stats = {
                'initialized': self.index is not None,
                'vector_store_type': 'ChromaDB',
                'collection_name': self.collection_name,
                'chroma_path': self.chroma_path
            }
            
            if self.vector_store and hasattr(self.vector_store, '_collection'):
                try:
                    collection_info = self.vector_store._collection.count()
                    stats['document_count'] = collection_info
                except Exception:
                    stats['document_count'] = 'Unknown'
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {'error': str(e)}


def create_rag_service(config: Config) -> RAGService:
    """Factory function to create a RAG service instance.
    
    Args:
        config: Application configuration
        
    Returns:
        Initialized RAG service instance
    """
    return RAGService(config)