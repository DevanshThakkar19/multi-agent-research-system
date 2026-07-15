"""Setup script for initializing databases."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.graph.neo4j_client import Neo4jClient
from src.vector.qdrant_client import QdrantClient
from loguru import logger


def setup_databases():
    """Initialize and verify database connections."""
    logger.info("Setting up databases...")
    
    # Setup Neo4j
    try:
        logger.info("Connecting to Neo4j...")
        neo4j_client = Neo4jClient()
        logger.info("Neo4j connection successful")
        neo4j_client.close()
    except Exception as e:
        logger.error(f"Neo4j setup failed: {e}")
        return False
    
    # Setup Qdrant
    try:
        logger.info("Connecting to Qdrant...")
        qdrant_client = QdrantClient()
        logger.info("Qdrant connection successful")
    except Exception as e:
        logger.error(f"Qdrant setup failed: {e}")
        return False
    
    logger.info("All databases set up successfully!")
    return True


if __name__ == "__main__":
    success = setup_databases()
    sys.exit(0 if success else 1)

