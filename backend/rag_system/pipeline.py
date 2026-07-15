"""Main pipeline for ingesting and processing files."""
from typing import Dict, Optional
from loguru import logger

from .ingestion.ingestion_manager import IngestionManager
from .graph.graph_builder import GraphBuilder
from .vector.qdrant_client import QdrantClient
from .vector.embedding_generator import EmbeddingGenerator
from .utils.sentiment_analyzer import SentimentAnalyzer


class RAGPipeline:
    """Main pipeline for the RAG system."""
    
    def __init__(self):
        self.ingestion_manager = IngestionManager()
        self.graph_builder = GraphBuilder()
        self.qdrant_client = QdrantClient()
        self.embedding_generator = EmbeddingGenerator()
        self.sentiment_analyzer = SentimentAnalyzer()
        self._extraction_results = []  # Store for cross-modal linking
    
    def ingest_and_index(
        self,
        file_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Ingest a file and index it in both graph and vector databases.
        
        Args:
            file_path: Path to the file
            metadata: Optional metadata
        
        Returns:
            Dictionary with ingestion results
        """
        try:
            # Validate file
            is_valid, error_msg = self.ingestion_manager.validate_file(file_path)
            if not is_valid:
                raise ValueError(error_msg)
            
            # Ingest file
            ingested_content = self.ingestion_manager.ingest_file(file_path, metadata)
            
            # Analyze sentiment and add to metadata
            ingested_content = self.sentiment_analyzer.extract_sentiment_metadata(ingested_content)
            
            # Build knowledge graph
            graph_stats = self.graph_builder.build_from_ingested_content(ingested_content)
            
            # Index in vector database
            vector_stats = self._index_in_vector_db(ingested_content)
            
            # Store extraction result for cross-modal linking
            self._extraction_results.append({
                "file_id": ingested_content["metadata"]["file_id"],
                "modality": ingested_content["modality"],
                "entities": graph_stats.get("entities", []),
                "relationships": graph_stats.get("relationships", [])
            })
            
            return {
                "success": True,
                "file_id": ingested_content["metadata"]["file_id"],
                "modality": ingested_content["modality"],
                "graph_stats": graph_stats,
                "vector_stats": vector_stats
            }
        except Exception as e:
            logger.error(f"Pipeline ingestion failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _index_in_vector_db(self, ingested_content: Dict) -> Dict:
        """Index content in vector database."""
        content = ingested_content.get("content", {})
        metadata = ingested_content.get("metadata", {})
        modality = ingested_content.get("modality", "unknown")
        chunks = ingested_content.get("chunks", [])
        
        if not chunks:
            return {"documents_indexed": 0}
        
        # Extract text from chunks
        texts = []
        metadata_list = []
        
        for i, chunk in enumerate(chunks):
            # Handle different chunk formats
            if isinstance(chunk, str):
                text = chunk
            elif isinstance(chunk, dict):
                if modality == "text":
                    text = chunk.get("text", "")
                elif modality == "image":
                    # Combine OCR text and caption for better indexing
                    ocr_text = chunk.get('text', '') or chunk.get('ocr_text', '')
                    caption = chunk.get('caption', '')
                    # Prioritize OCR text, add caption for context
                    if ocr_text:
                        text = f"{ocr_text} {caption}".strip()
                    else:
                        text = caption if caption else f"Image: {metadata.get('file_name', '')}"
                elif modality == "audio":
                    text = chunk.get("text", "")
                elif modality == "video":
                    text = chunk.get("text", "")
                else:
                    text = str(chunk)
            else:
                text = str(chunk)
            
            if text:
                texts.append(text)
                metadata_list.append({
                    "file_id": metadata.get("file_id", ""),
                    "modality": modality,
                    "chunk_index": i,
                    **metadata
                })
        
        if texts:
            self.qdrant_client.add_documents(
                texts=texts,
                metadata_list=metadata_list,
                ids=[f"{metadata.get('file_id', '')}_{i}" for i in range(len(texts))]
            )
        
        return {"documents_indexed": len(texts)}
    
    def link_cross_modal_entities(self) -> Dict:
        """
        Link entities across different modalities after ingesting multiple files.
        
        Returns:
            Dictionary with cross-modal linking results
        """
        if not self._extraction_results or len(self._extraction_results) < 2:
            logger.info("Need at least 2 files from different modalities for cross-modal linking")
            return {"links_created": 0, "message": "Need multiple files from different modalities"}
        
        try:
            # Format extraction results for cross-modal linking
            entity_sets = []
            for result in self._extraction_results:
                entity_sets.append({
                    "entities": result.get("entities", []),
                    "modality": result.get("modality"),
                    "file_id": result.get("file_id")
                })
            
            # Perform cross-modal linking
            linking_result = self.graph_builder.link_cross_modal_entities(entity_sets)
            
            # Add links to Neo4j
            if linking_result.get("cross_modal_links"):
                self.graph_builder.neo4j_client.add_relationships(
                    linking_result["cross_modal_links"]
                )
            
            links_created = len(linking_result.get("cross_modal_links", []))
            logger.info(f"Created {links_created} cross-modal entity links")
            
            return {
                "links_created": links_created,
                "linked_entities": len(linking_result.get("linked_entities", [])),
                "details": linking_result
            }
        except Exception as e:
            logger.error(f"Cross-modal linking failed: {e}")
            return {"links_created": 0, "error": str(e)}

