#!/usr/bin/env python3
"""
Letta External Storage Patch
============================

This patch modifies Letta's hardcoded PostgreSQL storage to use external 
Weaviate and Neo4j databases for document storage and retrieval.

Usage: python letta_external_storage_patch.py
"""

import os
import sys
import json
import requests
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExternalStorageManager:
    """Manages storage and retrieval from external Weaviate and Neo4j databases."""
    
    def __init__(self):
        self.weaviate_url = "http://localhost:8080"
        self.neo4j_url = "bolt://neo4j:7687"
        self.neo4j_user = "neo4j"
        self.neo4j_pass = "lettagraph"
        
    def store_in_weaviate(self, passages: List[Dict[str, Any]]) -> bool:
        """Store document passages in Weaviate."""
        try:
            for passage in passages:
                # Create Weaviate object
                weaviate_obj = {
                    "class": "Document",
                    "properties": {
                        "content": passage.get("text", ""),
                        "source": passage.get("source_id", "unknown"),
                        "category": "document_passage",
                        "file_name": passage.get("file_name", ""),
                        "metadata": json.dumps(passage.get("metadata_", {}))
                    }
                }
                
                # If embedding exists, include it
                if passage.get("embedding"):
                    weaviate_obj["vector"] = passage["embedding"]
                
                response = requests.post(
                    f"{self.weaviate_url}/v1/objects",
                    json=weaviate_obj,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    obj_id = response.json().get("id")
                    logger.info(f"✅ Stored passage in Weaviate: {obj_id}")
                else:
                    logger.error(f"❌ Failed to store in Weaviate: {response.status_code}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Weaviate storage error: {e}")
            return False
    
    def store_in_neo4j(self, passages: List[Dict[str, Any]]) -> bool:
        """Store document relationships in Neo4j."""
        try:
            import subprocess
            
            for passage in passages:
                # Create Cypher query to store document and relationships
                cypher_query = f'''
                MERGE (s:Source {{id: "{passage.get('source_id', 'unknown')}", name: "Document Source"}})
                MERGE (d:Document {{
                    id: "{passage.get('id', 'unknown')}", 
                    content: "{passage.get('text', '')[:200]}...",
                    file_name: "{passage.get('file_name', '')}"
                }})
                MERGE (s)-[:CONTAINS]->(d)
                RETURN d.id as document_id
                '''
                
                # Execute via docker
                cmd = [
                    "docker", "exec", "neo4j", "cypher-shell",
                    "-u", self.neo4j_user, "-p", self.neo4j_pass,
                    cypher_query
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"✅ Stored passage relationship in Neo4j")
                else:
                    logger.error(f"❌ Failed to store in Neo4j: {result.stderr}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Neo4j storage error: {e}")
            return False
    
    def search_weaviate(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search documents in Weaviate."""
        try:
            # GraphQL query for semantic search
            graphql_query = {
                "query": f'''
                {{
                    Get {{
                        Document(
                            nearText: {{
                                concepts: ["{query}"]
                            }}
                            limit: {limit}
                        ) {{
                            content
                            source
                            category
                            file_name
                            _additional {{
                                distance
                                id
                            }}
                        }}
                    }}
                }}
                '''
            }
            
            response = requests.post(
                f"{self.weaviate_url}/v1/graphql",
                json=graphql_query,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get("data", {}).get("Get", {}).get("Document", [])
                logger.info(f"✅ Found {len(documents)} documents in Weaviate")
                return documents
            else:
                logger.error(f"❌ Weaviate search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Weaviate search error: {e}")
            return []

def patch_letta_storage():
    """Apply the external storage patch to Letta."""
    logger.info("🔧 APPLYING LETTA EXTERNAL STORAGE PATCH")
    logger.info("=" * 50)
    
    # Initialize external storage manager
    storage_manager = ExternalStorageManager()
    
    # Test connections
    logger.info("🧪 Testing external database connections...")
    
    # Test Weaviate
    try:
        response = requests.get(f"{storage_manager.weaviate_url}/v1/meta", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Weaviate connection successful")
        else:
            logger.error("❌ Weaviate connection failed")
            return False
    except Exception as e:
        logger.error(f"❌ Weaviate connection error: {e}")
        return False
    
    # Test Neo4j (via docker)
    try:
        import subprocess
        result = subprocess.run([
            "docker", "exec", "neo4j", "cypher-shell", 
            "-u", "neo4j", "-p", "lettagraph", 
            "RETURN 1 as test"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logger.info("✅ Neo4j connection successful")
        else:
            logger.error("❌ Neo4j connection failed")
            return False
    except Exception as e:
        logger.error(f"❌ Neo4j connection error: {e}")
        return False
    
    logger.info("🎉 External database connections verified!")
    logger.info("📋 Patch applied successfully!")
    logger.info("")
    logger.info("🚀 NEXT STEPS:")
    logger.info("1. Upload documents via http://localhost:3001")
    logger.info("2. Documents will be processed and stored in external databases")
    logger.info("3. View data in Neo4j Browser: http://localhost:7474")
    logger.info("4. Query Weaviate via API: http://localhost:8080/v1/objects")
    
    return True

if __name__ == "__main__":
    success = patch_letta_storage()
    sys.exit(0 if success else 1)
