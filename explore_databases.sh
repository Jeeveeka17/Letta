#!/bin/bash

echo "🎯 LETTA CONTEXT ENGINE - DATABASE EXPLORER"
echo "============================================="
echo ""

echo "📊 POSTGRESQL (Metadata)"
echo "========================"
echo "Sources:"
docker exec postgres psql -U letta -d letta -c "SELECT id, name, description FROM sources;" 2>/dev/null
echo ""

echo "🔍 WEAVIATE (Vector Embeddings)"
echo "==============================="
echo "Objects count:"
curl -s http://localhost:8080/v1/objects | jq '.objects | length'
echo ""
echo "Sample objects:"
curl -s http://localhost:8080/v1/objects | jq '.objects[] | {id: .id, content: .properties.content[0:100] + "..."}' 2>/dev/null
echo ""

echo "📈 NEO4J (Graph Relationships)"
echo "=============================="
echo "Node counts by type:"
docker exec neo4j cypher-shell -u neo4j -p lettagraph "MATCH (n) RETURN labels(n)[0] as node_type, count(n) as count" 2>/dev/null
echo ""
echo "Relationships:"
docker exec neo4j cypher-shell -u neo4j -p lettagraph "MATCH (a)-[r]->(b) RETURN labels(a)[0] + ' -[' + type(r) + ']-> ' + labels(b)[0] as relationship_pattern, count(*) as count" 2>/dev/null
echo ""

echo "🌐 WEB INTERFACES"
echo "================="
echo "• Neo4j Browser: http://localhost:7474 (neo4j/lettagraph)"
echo "• Weaviate Console: https://console.weaviate.cloud (connect to localhost:8080)"
echo "• Your Letta UI: http://localhost:3000"
echo ""

echo "🔍 QUICK COMMANDS"
echo "================"
echo "• Check this status: ./explore_databases.sh"
echo "• Neo4j query: docker exec neo4j cypher-shell -u neo4j -p lettagraph 'MATCH (n) RETURN n LIMIT 5'"
echo "• Weaviate objects: curl -s http://localhost:8080/v1/objects | jq '.objects'"
echo "• PostgreSQL tables: docker exec postgres psql -U letta -d letta -c '\\dt'"
