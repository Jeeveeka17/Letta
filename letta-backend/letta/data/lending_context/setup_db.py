import json
import requests
import neo4j
from neo4j import GraphDatabase

def read_file(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def add_to_weaviate(content, category, source):
    headers = {
        "Authorization": "Bearer default-key",
        "Content-Type": "application/json"
    }
    
    data = {
        "class": "Document",
        "properties": {
            "content": content,
            "category": category,
            "source": source
        }
    }
    
    response = requests.post(
        "http://localhost:8080/v1/objects",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        return response.json()['id']
    else:
        print(f"Error adding to Weaviate: {response.text}")
        return None

def add_to_neo4j(tx, content, category, source):
    query = """
    CREATE (d:Document {
        content: $content,
        category: $category,
        source: $source
    })
    RETURN id(d)
    """
    result = tx.run(query, content=content, category=category, source=source)
    return result.single()[0]

def create_relationship(tx, from_id, to_id, relationship_type):
    query = """
    MATCH (a:Document), (b:Document)
    WHERE id(a) = $from_id AND id(b) = $to_id
    CREATE (a)-[r:REQUIRES]->(b)
    RETURN type(r)
    """
    tx.run(query, from_id=from_id, to_id=to_id)

def main():
    # Read files
    files = {
        "lending": "lending_rules.txt",
        "ekyc": "eKYC.txt",
        "pan": "PANNSDL.txt"
    }
    
    file_contents = {}
    for category, filename in files.items():
        filepath = f"./{filename}"
        file_contents[category] = read_file(filepath)
    
    # Add to Weaviate
    weaviate_ids = {}
    for category, content in file_contents.items():
        weaviate_id = add_to_weaviate(
            content,
            category,
            files[category]
        )
        if weaviate_id:
            weaviate_ids[category] = weaviate_id
            print(f"Added {category} to Weaviate with ID: {weaviate_id}")
    
    # Add to Neo4j
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "lettagraph")
    )
    
    with driver.session() as session:
        # Add documents
        neo4j_ids = {}
        for category, content in file_contents.items():
            neo4j_id = session.execute_write(
                add_to_neo4j,
                content,
                category,
                files[category]
            )
            neo4j_ids[category] = neo4j_id
            print(f"Added {category} to Neo4j with ID: {neo4j_id}")
        
        # Create relationships
        session.execute_write(
            create_relationship,
            neo4j_ids["lending"],
            neo4j_ids["ekyc"],
            "REQUIRES"
        )
        session.execute_write(
            create_relationship,
            neo4j_ids["ekyc"],
            neo4j_ids["pan"],
            "REQUIRES"
        )
        print("Created relationships in Neo4j")
    
    driver.close()

if __name__ == "__main__":
    main()
