"""Build knowledge graph from ingested content."""
from typing import Dict, List
from loguru import logger

from .neo4j_client import Neo4jClient
from .entity_extractor import EntityExtractor


class GraphBuilder:
    """Build and maintain the knowledge graph."""
    
    def __init__(self):
        self.neo4j_client = Neo4jClient()
        self.entity_extractor = EntityExtractor()
    
    def build_from_ingested_content(self, ingested_content: Dict) -> Dict:
        """
        Build graph nodes and relationships from ingested content.
        
        Args:
            ingested_content: Output from ingestion pipeline
        
        Returns:
            Dictionary with graph statistics
        """
        content = ingested_content.get("content", {})
        metadata = ingested_content.get("metadata", {})
        modality = ingested_content.get("modality", "unknown")
        file_id = metadata.get("file_id", "unknown")
        
        # Add file node
        self.neo4j_client.add_file_node(file_id, metadata)
        
        # Extract text content based on modality
        text_content = self._extract_text_content(content, modality)
        
        if not text_content:
            logger.warning(f"No text content extracted for {file_id}")
            return {"entities_added": 0, "relationships_added": 0}
        
        # Extract entities and relationships
        try:
            extraction_result = self.entity_extractor.extract_entities_and_relationships(
                text_content,
                modality,
                file_id,
                metadata
            )
            
            entities = extraction_result.get("entities", [])
            relationships = extraction_result.get("relationships", [])
        except Exception as e:
            logger.warning(f"Entity extraction failed (API quota or other issue): {e}")
            logger.info("Continuing without entity extraction - file will still be indexed in vector DB")
            entities = []
            relationships = []
        
        # Add to graph
        try:
            if entities:
                self.neo4j_client.add_entities(entities, file_id, modality)
            
            if relationships:
                self.neo4j_client.add_relationships(relationships)
        except Exception as e:
            logger.error(f"Failed to add to graph: {e}")
            # Continue even if graph addition fails
        
        return {
            "entities_added": len(entities),
            "relationships_added": len(relationships),
            "file_id": file_id
        }
    
    def _extract_text_content(self, content, modality: str) -> str:
        """Extract text content from different modalities."""
        # Handle case where content might be a string or dict
        if isinstance(content, str):
            return content
        
        if not isinstance(content, dict):
            return str(content)
        
        if modality == "text":
            return content.get("content", "")
        elif modality == "image":
            ocr_text = content.get("ocr_text", "")
            caption = content.get("caption", "")
            return f"{caption}\n{ocr_text}"
        elif modality == "audio":
            transcription = content.get("transcription", "")
            if isinstance(transcription, dict):
                return transcription.get("text", "")
            return str(transcription)
        elif modality == "video":
            transcription = content.get("transcription", {})
            if isinstance(transcription, dict):
                return transcription.get("text", "")
            return str(transcription)
        else:
            return ""
    
    def link_cross_modal_entities(self, extraction_results: List[Dict]) -> Dict:
        """
        Link entities across different modalities.
        
        Args:
            extraction_results: List of extraction results from different modalities
        
        Returns:
            Dictionary with cross-modal linking results
        """
        # Extract entities from all modalities
        entity_sets = []
        for result in extraction_results:
            entity_sets.append({
                "entities": result.get("entities", []),
                "modality": result.get("modality", "unknown"),
                "file_id": result.get("file_id", "")
            })
        
        # Perform cross-modal linking
        linking_result = self.entity_extractor.cross_modal_link_entities(entity_sets)
        
        # Add cross-modal relationships to graph
        if linking_result.get("cross_modal_links"):
            try:
                self.neo4j_client.add_relationships(linking_result["cross_modal_links"])
                logger.info(f"Added {len(linking_result['cross_modal_links'])} cross-modal links to graph")
            except Exception as e:
                logger.warning(f"Failed to add cross-modal links to graph: {e}")
        
        return linking_result
    
    def close(self):
        """Close connections."""
        self.neo4j_client.close()

