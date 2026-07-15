"""Neo4j client for knowledge graph operations."""
from typing import Dict, List, Optional
from neo4j import GraphDatabase
from loguru import logger

from ..utils.config import settings


class Neo4jClient:
    """Client for Neo4j knowledge graph operations."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize graph schema with constraints and indexes."""
        with self.driver.session() as session:
            try:
                # Create constraints (Neo4j 5.x syntax)
                session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
            except Exception as e:
                logger.warning(f"Constraint entity_id may already exist: {e}")
            
            try:
                session.run("CREATE CONSTRAINT file_id IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE")
            except Exception as e:
                logger.warning(f"Constraint file_id may already exist: {e}")
            
            try:
                # Create indexes (Neo4j 5.x syntax)
                session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")
            except Exception as e:
                logger.warning(f"Index entity_name may already exist: {e}")
            
            try:
                session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            except Exception as e:
                logger.warning(f"Index entity_type may already exist: {e}")
            
            logger.info("Neo4j schema initialized")
    
    def add_entities(self, entities: List[Dict], file_id: str, modality: str):
        """Add entities to the graph."""
        with self.driver.session() as session:
            import json
            for entity in entities:
                # Convert properties dict to JSON string if it's a dict
                properties = entity.get("properties", {})
                if isinstance(properties, dict):
                    properties_json = json.dumps(properties)
                else:
                    properties_json = str(properties)
                
                query = """
                MERGE (e:Entity {id: $entity_id})
                SET e.name = $name,
                    e.type = $type,
                    e.properties_json = $properties_json,
                    e.modality = $modality,
                    e.last_updated = datetime()
                WITH e
                MATCH (f:File {id: $file_id})
                MERGE (e)-[:APPEARS_IN]->(f)
                """
                
                try:
                    session.run(
                        query,
                        entity_id=entity.get("id"),
                        name=entity.get("name"),
                        type=entity.get("type"),
                        properties_json=properties_json,
                        modality=modality,
                        file_id=file_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to add entity {entity.get('id')}: {e}")
            
            logger.info(f"Added {len(entities)} entities to graph")
    
    def add_relationships(self, relationships: List[Dict]):
        """Add relationships to the graph."""
        with self.driver.session() as session:
            for rel in relationships:
                source_id = rel.get("source")
                target_id = rel.get("target")
                
                if not source_id or not target_id:
                    logger.warning(f"Skipping relationship with missing source/target: {rel}")
                    continue
                
                # Convert properties dict to JSON string if it's a dict
                import json
                properties = rel.get("properties", {})
                if isinstance(properties, dict):
                    properties_json = json.dumps(properties)
                else:
                    properties_json = str(properties)
                
                query = """
                MATCH (source:Entity {id: $source_id})
                MATCH (target:Entity {id: $target_id})
                MERGE (source)-[r:RELATED_TO]->(target)
                SET r.type = $rel_type,
                    r.properties_json = $properties_json,
                    r.last_updated = datetime()
                """
                
                try:
                    session.run(
                        query,
                        source_id=source_id,
                        target_id=target_id,
                        rel_type=rel.get("type", "RELATED_TO"),
                        properties_json=properties_json
                    )
                except Exception as e:
                    logger.warning(f"Failed to add relationship {source_id} -> {target_id}: {e}")
            
            logger.info(f"Added {len(relationships)} relationships to graph")
    
    def add_file_node(self, file_id: str, metadata: Dict):
        """Add a file node to the graph."""
        with self.driver.session() as session:
            # Neo4j doesn't support nested maps, so we flatten metadata or store as JSON string
            import json
            metadata_json = json.dumps(metadata)
            
            query = """
            MERGE (f:File {id: $file_id})
            SET f.name = $name,
                f.modality = $modality,
                f.ingestion_date = datetime(),
                f.file_path = $file_path,
                f.file_size = $file_size,
                f.file_format = $file_format,
                f.metadata_json = $metadata_json
            """
            
            session.run(
                query,
                file_id=file_id,
                name=metadata.get("file_name", ""),
                modality=metadata.get("modality", ""),
                file_path=metadata.get("file_path", ""),
                file_size=metadata.get("file_size", 0),
                file_format=metadata.get("file_format", ""),
                metadata_json=metadata_json
            )
    
    def query_graph(
        self,
        entity_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query the knowledge graph."""
        with self.driver.session() as session:
            conditions = []
            params = {"limit": limit}
            
            if entity_name:
                conditions.append("e.name CONTAINS $entity_name")
                params["entity_name"] = entity_name
            
            if entity_type:
                conditions.append("e.type = $entity_type")
                params["entity_type"] = entity_type
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Use OPTIONAL MATCH with type check to avoid warnings if relationship doesn't exist
            query = f"""
            MATCH (e:Entity)
            WHERE {where_clause}
            OPTIONAL MATCH (e)-[r]->(target:Entity)
            WHERE type(r) = 'RELATED_TO' OR r IS NULL
            RETURN e, collect({{target: target, relationship: r}}) as relationships
            LIMIT $limit
            """
            
            try:
                result = session.run(query, **params)
                nodes = []
                
                for record in result:
                    entity = dict(record["e"])
                    relationships = []
                    for rel_data in record["relationships"]:
                        if rel_data.get("target") and rel_data.get("relationship"):
                            relationships.append({
                                "target": dict(rel_data["target"]),
                                "relationship": dict(rel_data["relationship"])
                            })
                    
                    nodes.append({
                        "entity": entity,
                        "relationships": relationships
                    })
                
                return nodes
            except Exception as e:
                logger.warning(f"Graph query failed: {e}")
                return []
    
    def traverse_from_entity(
        self,
        entity_id: str,
        max_depth: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> Dict:
        """Traverse graph from a specific entity."""
        with self.driver.session() as session:
            rel_filter = ""
            if relationship_types:
                rel_types = "|".join(relationship_types)
                rel_filter = f":{rel_types}"
            
            query = f"""
            MATCH path = (start:Entity {{id: $entity_id}})-[*1..{max_depth}{rel_filter}]->(end:Entity)
            RETURN path
            LIMIT 50
            """
            
            result = session.run(query, entity_id=entity_id)
            paths = []
            
            for record in result:
                path = record["path"]
                nodes = [dict(node) for node in path.nodes]
                relationships = [dict(rel) for rel in path.relationships]
                paths.append({
                    "nodes": nodes,
                    "relationships": relationships
                })
            
            return {
                "entity_id": entity_id,
                "paths": paths
            }
    
    def close(self):
        """Close the database connection."""
        self.driver.close()

