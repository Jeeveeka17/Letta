import os
from typing import List, Optional
from fastapi import UploadFile
import weaviate
from neo4j import GraphDatabase
import magic
import json
from ..context_engine.context_engine import ContextEngine

class FileUploadAgent:
    def __init__(self, weaviate_client, neo4j_client, anthropic_api_key: str):
        self.weaviate_client = weaviate_client
        self.neo4j_client = neo4j_client
        self.context_engine = ContextEngine(anthropic_api_key=anthropic_api_key)
        self.mime = magic.Magic(mime=True)

    async def process_file(self, file: UploadFile) -> dict:
        """Process uploaded file and store in both vector and graph DBs."""
        try:
            # Read file content
            content = await file.read()
            
            # Detect file type
            file_type = self.mime.from_buffer(content)
            
            # Extract text based on file type
            if file_type.startswith('text/'):
                text_content = content.decode('utf-8')
            else:
                # Handle other file types if needed
                raise ValueError(f"Unsupported file type: {file_type}")

            # Generate embeddings and store in Weaviate
            vector_id = await self._store_in_weaviate(text_content, file.filename, file_type)
            
            # Store metadata in Neo4j
            graph_id = await self._store_in_neo4j(file.filename, file_type, vector_id)
            
            # Process context using the context engine
            context_result = self.context_engine.process_text(text_content)

            return {
                "status": "success",
                "vector_id": vector_id,
                "graph_id": graph_id,
                "file_name": file.filename,
                "file_type": file_type,
                "context": context_result
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def _store_in_weaviate(self, content: str, filename: str, file_type: str) -> str:
        """Store content in Weaviate vector database."""
        try:
            # Create a data object with the file content
            data_object = {
                "content": content,
                "source": filename,
                "type": file_type
            }

            # Store in Weaviate
            vector_id = self.weaviate_client.data_object.create(
                class_name="Document",
                data_object=data_object
            )

            return vector_id

        except Exception as e:
            raise Exception(f"Failed to store in Weaviate: {str(e)}")

    async def _store_in_neo4j(self, filename: str, file_type: str, vector_id: str) -> str:
        """Store metadata in Neo4j graph database."""
        try:
            # Create a node in Neo4j
            with self.neo4j_client.session() as session:
                result = session.run(
                    """
                    CREATE (f:File {
                        filename: $filename,
                        type: $file_type,
                        vector_id: $vector_id,
                        timestamp: datetime()
                    })
                    RETURN id(f) as node_id
                    """,
                    filename=filename,
                    file_type=file_type,
                    vector_id=vector_id
                )
                record = result.single()
                return str(record["node_id"])

        except Exception as e:
            raise Exception(f"Failed to store in Neo4j: {str(e)}")

    async def search_similar_files(self, query: str, limit: int = 5) -> List[dict]:
        """Search for similar files using vector similarity."""
        try:
            # Search in Weaviate
            vector_results = self.weaviate_client.query.get(
                "Document",
                ["content", "source", "type"]
            ).with_near_text({
                "concepts": [query]
            }).with_limit(limit).do()

            # Get related metadata from Neo4j
            results = []
            for item in vector_results["data"]["Get"]["Document"]:
                with self.neo4j_client.session() as session:
                    neo4j_result = session.run(
                        """
                        MATCH (f:File {vector_id: $vector_id})
                        RETURN f
                        """,
                        vector_id=item["_additional"]["id"]
                    )
                    neo4j_data = neo4j_result.single()
                    if neo4j_data:
                        results.append({
                            "content": item["content"],
                            "source": item["source"],
                            "type": item["type"],
                            "metadata": neo4j_data["f"]
                        })

            return results

        except Exception as e:
            raise Exception(f"Failed to search: {str(e)}")

