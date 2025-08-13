#!/usr/bin/env python3
"""
External Storage Service for Letta
==================================

This service monitors Letta's document processing and automatically
stores processed documents in Weaviate and Neo4j.
"""

import time
import json
import requests
import subprocess
import threading
from datetime import datetime
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class ExternalStorageService:
    def __init__(self):
        self.weaviate_url = "http://localhost:8080"
        self.letta_api_key = "sk-let-MGFmM2VkNjktN2I3Ni00MTg4LWJiODEtMjY5NjhjMTFmZWJjOmQ0YzgyOWZkLTRlZTgtNDJjMS1iNDIzLTVkODI2MjdjZjVlYw=="
        self.letta_url = "http://localhost:8283"
        self.processed_sources = set()
        
        # Use Docker PostgreSQL via command line
        self.use_docker_postgres = True
        logger.info("✅ Using Docker PostgreSQL via command line")
        
    def get_letta_sources(self):
        """Get all sources from Letta API."""
        try:
            response = requests.get(
                f"{self.letta_url}/v1/sources",
                headers={"Authorization": f"Bearer {self.letta_api_key}"}
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting sources: {e}")
            return []
    
    def extract_document_content(self, source_id):
        """Extract document content from PostgreSQL via Docker command."""
        try:
            # Query PostgreSQL via Docker command
            query = f"""
            SELECT fc.text 
            FROM file_contents fc 
            JOIN files f ON f.id = fc.file_id 
            WHERE f.source_id = '{source_id}'
            """
            
            cmd = [
                'docker', 'exec', 'postgres', 
                'psql', '-U', 'letta', '-d', 'letta', 
                '-t', '-c', query
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                if content and content != "(0 rows)":
                    return content
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return None
    
    def store_in_weaviate(self, source_data, content):
        """Store document in Weaviate."""
        try:
            weaviate_obj = {
                "class": "Document",
                "properties": {
                    "content": content[:10000],  # Limit content size
                    "source": source_data.get("name", "unknown"),
                    "category": "letta_processed",
                    "source_id": source_data.get("id", ""),
                    "description": source_data.get("description", ""),
                    "created_at": source_data.get("created_at", "")
                }
            }
            
            response = requests.post(
                f"{self.weaviate_url}/v1/objects",
                json=weaviate_obj,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                obj_id = response.json().get("id")
                logger.info(f"✅ Stored in Weaviate: {obj_id} for source {source_data['name']}")
                return True
            else:
                logger.error(f"❌ Weaviate storage failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Weaviate error: {e}")
            return False
    
    def store_in_neo4j(self, source_data, content):
        """Store document relationships in Neo4j."""
        try:
            # Extract key entities from content (simple keyword extraction)
            keywords = self.extract_keywords(content)
            
            # Create source and document nodes
            # Fix f-string backslash issue
            source_name = source_data.get('name', 'Unknown').replace('"', "'")
            source_desc = source_data.get('description', '').replace('"', "'")
            content_preview = content[:200].replace('"', "'")
            
            cypher_query = f"""
            MERGE (s:Source {{
                id: "{source_data.get('id', 'unknown')}", 
                name: "{source_name}",
                description: "{source_desc}"
            }})
            MERGE (d:Document {{
                id: "doc-{source_data.get('id', 'unknown')}", 
                content_preview: "{content_preview}...",
                created_at: "{source_data.get('created_at', '')}"
            }})
            MERGE (s)-[:CONTAINS]->(d)
            """
            
            # Add keyword relationships
            for i, keyword in enumerate(keywords[:5]):  # Limit to 5 keywords
                clean_keyword = keyword.replace('"', "'")
                cypher_query += f"""
                MERGE (k{i}:Keyword {{name: "{clean_keyword}"}})
                MERGE (d)-[:MENTIONS]->(k{i})
                """
            
            cypher_query += " RETURN s.name, d.id"
            
            result = subprocess.run([
                "docker", "exec", "neo4j", "cypher-shell",
                "-u", "neo4j", "-p", "lettagraph",
                cypher_query
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Stored in Neo4j: {source_data['name']}")
                return True
            else:
                logger.error(f"❌ Neo4j storage failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Neo4j error: {e}")
            return False
    
    def extract_keywords(self, content):
        """Extract key terms from content."""
        # Simple keyword extraction
        import re
        
        # Common technical terms and patterns
        keywords = set()
        
        # Find environment variables
        env_vars = re.findall(r'[A-Z_]{3,}(?:_[A-Z_]+)*', content)
        keywords.update(env_vars[:10])
        
        # Find API endpoints
        endpoints = re.findall(r'/[a-z-]+(?:/[a-z-]+)*', content)
        keywords.update(endpoints[:5])
        
        # Find configuration terms
        config_terms = re.findall(r'\b(?:config|endpoint|database|server|port|cors|health)\b', content.lower())
        keywords.update(config_terms[:5])
        
        return list(keywords)
    
    def process_new_sources(self):
        """Process any new sources that haven't been stored externally."""
        sources = self.get_letta_sources()
        
        for source in sources:
            source_id = source.get('id')
            
            if source_id not in self.processed_sources:
                logger.info(f"🔄 Processing new source: {source.get('name')}")
                
                # Extract content
                content = self.extract_document_content(source_id)
                
                if content:
                    # Store in external databases
                    weaviate_success = self.store_in_weaviate(source, content)
                    neo4j_success = self.store_in_neo4j(source, content)
                    
                    if weaviate_success and neo4j_success:
                        self.processed_sources.add(source_id)
                        logger.info(f"✅ Successfully processed: {source.get('name')}")
                    else:
                        logger.warning(f"⚠️ Partial processing for: {source.get('name')}")
                else:
                    logger.warning(f"⚠️ No content found for: {source.get('name')}")
    
    def run_monitoring_loop(self):
        """Run continuous monitoring loop."""
        logger.info("🚀 External Storage Service Started")
        logger.info("=" * 50)
        logger.info("📊 Monitoring Letta sources for new documents...")
        logger.info("🔍 Will store in Weaviate and Neo4j automatically")
        logger.info("")
        
        while True:
            try:
                self.process_new_sources()
                time.sleep(10)  # Check every 10 seconds
            except KeyboardInterrupt:
                logger.info("\n🛑 Service stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error

def main():
    """Main function to start the external storage service."""
    service = ExternalStorageService()
    
    # Run initial processing
    service.process_new_sources()
    
    # Start monitoring loop
    service.run_monitoring_loop()

if __name__ == "__main__":
    main()
