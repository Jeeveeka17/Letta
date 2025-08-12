import weaviate
from neo4j import GraphDatabase
import numpy as np

class GraphVectorDB:
    def __init__(self):
        # Initialize Neo4j connection
        self.neo4j_driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "lettagraph")
        )
        
        # Initialize Weaviate client
        self.weaviate_client = weaviate.WeaviateClient(
            connection_params=weaviate.connect.ConnectionParams.from_params(
                http_host="localhost",
                http_port=8080,
                http_secure=False,
                grpc_host="localhost",
                grpc_port=50051,
                grpc_secure=False
            )
        )
        self.weaviate_client.connect()
        
    def create_schema(self):
        """Create schema in Weaviate and Neo4j"""
        # Create Weaviate schema
        try:
            self.weaviate_client.collections.delete("Document")
        except:
            pass

        try:
            # Create collection configuration
            properties = [
                {
                    "name": "content",
                    "dataType": ["text"]
                },
                {
                    "name": "category", 
                    "dataType": ["text"]
                }
            ]
            
            self.weaviate_client.collections.create(
                name="Document",
                description="A collection of documents with vector embeddings",
                properties=properties,
                vectorizer_config=None  # We'll provide our own vectors
            )
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
        document = {
            "content": content,
            "category": category
        }
        
        try:
            collection = self.weaviate_client.collections.get("Document")
            doc_uuid = collection.data.insert(
                properties=document,
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
            collection = self.weaviate_client.collections.get("Document")
            response = collection.query.near_vector(
                near_vector=query_vector.tolist(),
                limit=limit,
                return_metadata=["distance"]
            )
            
            return response.objects
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
        self.weaviate_client.close()
        self.neo4j_driver.close()
