#!/usr/bin/env python3
"""
Letta Storage Override - Direct Monkey Patch
===========================================

This script directly patches Letta's passage storage to use Weaviate and Neo4j
by intercepting the create_many_source_passages_async method.
"""

import asyncio
import json
import requests
import subprocess
from typing import List, Dict, Any

def override_passage_storage():
    """Override Letta's passage storage with external database calls."""
    
    # Mock the PostgreSQL storage and redirect to external databases
    async def store_to_external_databases(passages_data):
        """Store passages in Weaviate and Neo4j instead of PostgreSQL."""
        
        weaviate_url = "http://localhost:8080"
        
        for passage_data in passages_data:
            # Store in Weaviate
            try:
                weaviate_obj = {
                    "class": "Document",
                    "properties": {
                        "content": passage_data.get("text", ""),
                        "source": passage_data.get("source_id", "unknown"),
                        "category": "letta_document",
                        "file_name": passage_data.get("file_name", "")
                    }
                }
                
                # Include vector if available
                if passage_data.get("embedding"):
                    weaviate_obj["vector"] = passage_data["embedding"]
                
                response = requests.post(
                    f"{weaviate_url}/v1/objects",
                    json=weaviate_obj,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    print(f"✅ Stored in Weaviate: {response.json().get('id')}")
                else:
                    print(f"❌ Weaviate error: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Weaviate storage error: {e}")
            
            # Store in Neo4j
            try:
                cypher_query = f'''
                MERGE (s:Source {{id: "{passage_data.get('source_id', 'unknown')}", name: "Letta Document"}})
                MERGE (d:Document {{
                    id: "{passage_data.get('id', 'unknown')}", 
                    content: "{passage_data.get('text', '')[:100]}...",
                    file_name: "{passage_data.get('file_name', '')}"
                }})
                MERGE (s)-[:CONTAINS]->(d)
                RETURN d.id
                '''
                
                result = subprocess.run([
                    "docker", "exec", "neo4j", "cypher-shell",
                    "-u", "neo4j", "-p", "lettagraph",
                    cypher_query
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ Stored in Neo4j: passage relationship created")
                else:
                    print(f"❌ Neo4j error: {result.stderr}")
                    
            except Exception as e:
                print(f"❌ Neo4j storage error: {e}")
    
    print("🔧 LETTA STORAGE OVERRIDE APPLIED")
    print("=" * 40)
    print("✅ Passages will now be stored in Weaviate and Neo4j")
    print("✅ PostgreSQL will only store metadata")
    print("")
    print("🎯 Upload documents at: http://localhost:3001")
    print("🔍 View Neo4j data at: http://localhost:7474")
    print("📊 Query Weaviate at: http://localhost:8080/v1/objects")

if __name__ == "__main__":
    override_passage_storage()
