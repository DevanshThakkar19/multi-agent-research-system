"""Entity and relationship extraction using LLMs."""
from typing import Dict, List, Optional
from openai import OpenAI
from loguru import logger

from ..utils.config import settings


class EntityExtractor:
    """Extract entities and relationships from content using LLMs."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    def extract_entities_and_relationships(
        self,
        content: str,
        modality: str,
        file_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Extract entities and relationships from content.
        
        Args:
            content: The content to extract from
            modality: Type of content (text, image, audio, video)
            file_id: Unique identifier for the source file
            metadata: Additional metadata
        
        Returns:
            Dictionary with entities and relationships
        """
        prompt = self._create_extraction_prompt(content, modality)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = self._parse_response(response.choices[0].message.content)
            result["file_id"] = file_id
            result["modality"] = modality
            
            logger.info(f"Extracted {len(result.get('entities', []))} entities and {len(result.get('relationships', []))} relationships")
            
            return result
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {"entities": [], "relationships": [], "file_id": file_id, "modality": modality}
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for entity extraction."""
        return """You are an expert at extracting structured information from content.
Extract entities (people, organizations, concepts, locations, etc.) and their relationships.
Return a JSON object with the following structure:
{
    "entities": [
        {
            "id": "unique_id",
            "name": "entity_name",
            "type": "PERSON|ORGANIZATION|CONCEPT|LOCATION|EVENT|OTHER",
            "properties": {}
        }
    ],
    "relationships": [
        {
            "source": "entity_id",
            "target": "entity_id",
            "type": "RELATED_TO|WORKS_FOR|LOCATED_IN|PART_OF|etc",
            "properties": {}
        }
    ]
}"""
    
    def _create_extraction_prompt(self, content: str, modality: str) -> str:
        """Create extraction prompt for the content."""
        # Truncate content if too long
        max_length = 8000
        if len(content) > max_length:
            content = content[:max_length] + "... [truncated]"
        
        return f"""Extract entities and relationships from the following {modality} content:

{content}

Focus on:
1. Named entities (people, organizations, locations)
2. Key concepts and topics
3. Relationships between entities
4. Important facts and connections

Return the results in the specified JSON format."""
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse LLM response into structured format."""
        import json
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response: {e}")
            return {"entities": [], "relationships": []}
    
    def cross_modal_link_entities(
        self,
        entity_sets: List[Dict],
        threshold: float = 0.8
    ) -> Dict:
        """
        Link entities across different modalities.
        
        Args:
            entity_sets: List of entity extraction results from different modalities
            threshold: Similarity threshold for linking
        
        Returns:
            Dictionary with linked entities
        """
        # Simple implementation: exact name matching
        # In production, would use embedding similarity
        all_entities = {}
        links = []
        
        for entity_set in entity_sets:
            for entity in entity_set.get("entities", []):
                entity_name = entity.get("name", "").lower()
                entity_id = entity.get("id", "")
                
                # Check for existing entity with same name
                if entity_name in all_entities:
                    links.append({
                        "source": all_entities[entity_name]["id"],
                        "target": entity_id,
                        "type": "CROSS_MODAL_LINK",
                        "confidence": 1.0
                    })
                else:
                    all_entities[entity_name] = entity
        
        return {
            "linked_entities": list(all_entities.values()),
            "cross_modal_links": links
        }

