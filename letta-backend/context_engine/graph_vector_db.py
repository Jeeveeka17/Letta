import weaviate
from neo4j import GraphDatabase
import numpy as np
import os

class GraphVectorDB:
    def __init__(self):
        # Initialize Neo4j connection
        self.neo4j_driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "lettagraph")
        )
        
        # Initialize Weaviate client
        self.weaviate_client = weaviate.Client(
            url="http://localhost:8080",
            auth_client_secret=weaviate.AuthApiKey(api_key="default-key")
        )
        
    def create_schema(self):
        """Create schema in Weaviate and Neo4j"""
        # Create Weaviate schema
        try:
            if self.weaviate_client.schema.contains("Document"):
                self.weaviate_client.schema.delete_class("Document")
        except:
            pass

        try:
            # Create class schema
            class_obj = {
                "class": "Document",
                "description": "A collection of documents with vector embeddings",
                "vectorizer": "none",  # We'll provide our own vectors
                "properties": [
                    {
                        "name": "content",
                        "description": "The document content",
                        "dataType": ["text"]
                    },
                    {
                        "name": "category",
                        "description": "The document category",
                        "dataType": ["text"]
                    }
                ]
            }
            
            self.weaviate_client.schema.create_class(class_obj)
            print("Weaviate schema created successfully")
        except Exception as e:
            print(f"Error creating Weaviate schema: {e}")

        # Create Neo4j constraints and indexes
        with self.neo4j_driver.session() as session:
            try:
                # Create constraint on Document nodes
                session.run("CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
                print("Neo4j constraints created successfully")
            except Exception as e:
                print(f"Error creating Neo4j constraints: {e}")

    def add_document(self, content: str, category: str, vector: np.ndarray) -> str:
        """Add a document to both Weaviate and Neo4j"""
        try:
            # Add to Weaviate
            doc_uuid = self.weaviate_client.data_object.create(
                data_object={
                    "content": content,
                    "category": category
                },
                class_name="Document",
                vector=vector.tolist()
            )
            print(f"Document added to Weaviate with UUID: {doc_uuid}")

            # Add to Neo4j
            with self.neo4j_driver.session() as session:
                session.run(
                    """
                    CREATE (d:Document {
                        id: $id,
                        content: $content,
                        category: $category
                    })
                    """,
                    id=str(doc_uuid),
                    content=content,
                    category=category
                )
                print("Document added to Neo4j")
            
            return str(doc_uuid)
        except Exception as e:
            print(f"Error adding document: {e}")
            return None

    def search_similar(self, query_vector: np.ndarray, limit: int = 5):
        """Search for similar documents using vector similarity"""
        try:
            results = (
                self.weaviate_client.query
                .get("Document", ["content", "category"])
                .with_near_vector({
                    "vector": query_vector.tolist()
                })
                .with_limit(limit)
                .with_additional(["distance"])
                .do()
            )
            
            return results["data"]["Get"]["Document"]
        except Exception as e:
            print(f"Error searching similar documents: {e}")
            return []

    def create_relationship(self, doc_id1: str, doc_id2: str, relationship_type: str):
        """Create a relationship between two documents in Neo4j"""
        try:
            with self.neo4j_driver.session() as session:
                session.run(
                    f"""
                    MATCH (d1:Document {{id: $id1}})
                    MATCH (d2:Document {{id: $id2}})
                    CREATE (d1)-[:{relationship_type}]->(d2)
                    """,
                    id1=doc_id1,
                    id2=doc_id2
                )
                print(f"Relationship {relationship_type} created between documents")
        except Exception as e:
            print(f"Error creating relationship: {e}")

    def close(self):
        """Clean up resources"""
        self.neo4j_driver.close()
