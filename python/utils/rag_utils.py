"""Utility functions for RAG pipeline operations.

This module provides helper functions for document processing, 
text chunking, and RAG pipeline management.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import mimetypes

from llama_index.core import Document
from llama_index.core.node_parser import SimpleNodeParser, SentenceSplitter
from llama_index.core.schema import MetadataMode


logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Utility class for processing documents for RAG ingestion."""
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 128):
        """Initialize document processor.
        
        Args:
            chunk_size: Maximum size of text chunks
            chunk_overlap: Overlap between consecutive chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize node parser for text chunking
        self.node_parser = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def create_document_from_text(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ) -> Document:
        """Create a Document object from text content.
        
        Args:
            text: Text content
            metadata: Optional metadata dictionary
            doc_id: Optional document ID
            
        Returns:
            Document object
        """
        if metadata is None:
            metadata = {}
        
        # Add basic metadata
        metadata.update({
            'content_type': 'text',
            'character_count': len(text),
            'word_count': len(text.split())
        })
        
        return Document(
            text=text,
            metadata=metadata,
            id_=doc_id
        )
    
    def create_document_from_file(self, file_path: str) -> Optional[Document]:
        """Create a Document object from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Document object or None if file cannot be processed
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            # Get file info
            file_size = path.stat().st_size
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Read file content based on type
            if path.suffix.lower() in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
            else:
                logger.warning(f"Unsupported file type: {file_path}")
                return None
            
            # Create metadata
            metadata = {
                'file_path': str(path.absolute()),
                'file_name': path.name,
                'file_extension': path.suffix,
                'file_size': file_size,
                'mime_type': mime_type or 'unknown',
                'content_type': 'file'
            }
            
            return self.create_document_from_text(
                text=content,
                metadata=metadata,
                doc_id=str(path.absolute())
            )
            
        except Exception as e:
            logger.error(f"Failed to create document from file {file_path}: {e}")
            return None
    
    def process_directory(
        self, 
        directory_path: str, 
        file_extensions: Optional[List[str]] = None,
        recursive: bool = True
    ) -> List[Document]:
        """Process all supported files in a directory.
        
        Args:
            directory_path: Path to directory
            file_extensions: List of file extensions to include
            recursive: Whether to search recursively
            
        Returns:
            List of Document objects
        """
        documents = []
        
        try:
            path = Path(directory_path)
            
            if not path.exists() or not path.is_dir():
                logger.error(f"Directory not found: {directory_path}")
                return documents
            
            # Default file extensions
            if file_extensions is None:
                file_extensions = ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml']
            
            # Get file pattern
            pattern = "**/*" if recursive else "*"
            
            for file_path in path.glob(pattern):
                if file_path.is_file() and file_path.suffix.lower() in file_extensions:
                    doc = self.create_document_from_file(str(file_path))
                    if doc:
                        documents.append(doc)
            
            logger.info(f"Processed {len(documents)} documents from {directory_path}")
            
        except Exception as e:
            logger.error(f"Failed to process directory {directory_path}: {e}")
        
        return documents
    
    def chunk_document(self, document: Document) -> List[Document]:
        """Split a document into smaller chunks.
        
        Args:
            document: Document to chunk
            
        Returns:
            List of chunked Document objects
        """
        try:
            # Parse document into nodes
            nodes = self.node_parser.get_nodes_from_documents([document])
            
            # Convert nodes back to documents
            chunked_docs = []
            for i, node in enumerate(nodes):
                # Create metadata for chunk
                chunk_metadata = document.metadata.copy()
                chunk_metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(nodes),
                    'is_chunk': True,
                    'parent_doc_id': document.id_
                })
                
                # Create chunk document
                chunk_doc = Document(
                    text=node.text,
                    metadata=chunk_metadata,
                    id_=f"{document.id_}_chunk_{i}" if document.id_ else None
                )
                chunked_docs.append(chunk_doc)
            
            return chunked_docs
            
        except Exception as e:
            logger.error(f"Failed to chunk document: {e}")
            return [document]  # Return original document if chunking fails


class RAGUtilities:
    """Additional utility functions for RAG operations."""
    
    @staticmethod
    def validate_documents(documents: List[Document]) -> List[Document]:
        """Validate and filter documents.
        
        Args:
            documents: List of documents to validate
            
        Returns:
            List of valid documents
        """
        valid_docs = []
        
        for doc in documents:
            if not doc.text or not doc.text.strip():
                logger.warning(f"Skipping empty document: {doc.id_}")
                continue
            
            if len(doc.text.strip()) < 10:  # Minimum content length
                logger.warning(f"Skipping document with insufficient content: {doc.id_}")
                continue
            
            valid_docs.append(doc)
        
        logger.info(f"Validated {len(valid_docs)} out of {len(documents)} documents")
        return valid_docs
    
    @staticmethod
    def extract_text_from_response(response: Any) -> str:
        """Extract text from various response types.
        
        Args:
            response: Response object from query engine
            
        Returns:
            Extracted text content
        """
        if hasattr(response, 'response'):
            return str(response.response)
        elif hasattr(response, 'text'):
            return str(response.text)
        elif isinstance(response, str):
            return response
        else:
            return str(response)
    
    @staticmethod
    def create_context_from_documents(documents: List[Dict[str, Any]], max_length: int = 2000) -> str:
        """Create context string from retrieved documents.
        
        Args:
            documents: List of document dictionaries
            max_length: Maximum length of context string
            
        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0
        
        for doc in documents:
            content = doc.get('content', '')
            if not content:
                continue
            
            # Add document with separator
            doc_text = f"--- Document ---\n{content}\n"
            
            if current_length + len(doc_text) > max_length:
                break
            
            context_parts.append(doc_text)
            current_length += len(doc_text)
        
        return '\n'.join(context_parts)
    
    @staticmethod
    def format_rag_response(
        response: str, 
        sources: Optional[List[Dict[str, Any]]] = None,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """Format RAG response with optional source information.
        
        Args:
            response: Generated response text
            sources: List of source documents
            include_sources: Whether to include source information
            
        Returns:
            Formatted response dictionary
        """
        result = {
            'response': response,
            'timestamp': str(os.path.getmtime(__file__) if os.path.exists(__file__) else 0)
        }
        
        if include_sources and sources:
            formatted_sources = []
            for source in sources:
                source_info = {
                    'content_preview': source.get('content', '')[:200] + '...' if len(source.get('content', '')) > 200 else source.get('content', ''),
                    'score': source.get('score', 0.0),
                    'metadata': source.get('metadata', {})
                }
                formatted_sources.append(source_info)
            
            result['sources'] = formatted_sources
            result['source_count'] = len(formatted_sources)
        
        return result


def create_document_processor(chunk_size: int = 1024, chunk_overlap: int = 128) -> DocumentProcessor:
    """Factory function to create a DocumentProcessor instance.
    
    Args:
        chunk_size: Maximum size of text chunks
        chunk_overlap: Overlap between consecutive chunks
        
    Returns:
        DocumentProcessor instance
    """
    return DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)