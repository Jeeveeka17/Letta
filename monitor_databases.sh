#!/bin/bash

echo "🗄️  LETTA CONTEXT ENGINE - DATABASE MONITORING DASHBOARD"
echo "========================================================"
echo ""

echo "📊 SYSTEM STATUS"
echo "---------------"
echo "🐳 Docker Services:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(letta|weaviate|neo4j|postgres)"
echo ""

echo "🔍 LETTA INTERNAL DATA"
echo "---------------------"
echo "📁 Sources:"
curl -s http://localhost:8283/v1/sources/ \
  -H "Authorization: Bearer sk-let-MGFmM2VkNjktN2I3Ni00MTg4LWJiODEtMjY5NjhjMTFmZWJjOmQ0YzgyOWZkLTRlZTgtNDJjMS1iNDIzLTVkODI2MjdjZjVlYw==" \
  | jq -r '.[] | "  • \(.name) (\(.id))"' || echo "  No sources found"

echo ""
echo "🤖 Agents:"
curl -s http://localhost:8283/v1/agents/ \
  -H "Authorization: Bearer sk-let-MGFmM2VkNjktN2I3Ni00MTg4LWJiODEtMjY5NjhjMTFmZWJjOmQ0YzgyOWZkLTRlZTgtNDJjMS1iNDIzLTVkODI2MjdjZjVlYw==" \
  | jq -r '.[] | "  • \(.name) (\(.id))"' || echo "  No agents found"

echo ""
echo "🗃️  WEAVIATE VECTOR DATABASE"
echo "---------------------------"
echo "📈 Total Objects:"
WEAVIATE_COUNT=$(curl -s http://localhost:8080/v1/objects | jq '.objects | length')
echo "  $WEAVIATE_COUNT objects stored"

if [ "$WEAVIATE_COUNT" -gt 0 ]; then
    echo ""
    echo "📄 Sample Objects:"
    curl -s http://localhost:8080/v1/objects | jq -r '.objects[0:3][] | "  • \(.class): \(.properties.content[0:100])..."'
fi

echo ""
echo "🕸️  NEO4J GRAPH DATABASE"
echo "------------------------"
echo "🔗 Nodes and Relationships:"
docker exec neo4j cypher-shell -u neo4j -p lettagraph \
  "MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC" 2>/dev/null \
  | grep -v "type" | grep -v "^$" | sed 's/^/  • /' || echo "  No nodes found"

echo ""
echo "📊 Total Graph Size:"
docker exec neo4j cypher-shell -u neo4j -p lettagraph \
  "MATCH (n) RETURN count(n) as nodes UNION MATCH ()-[r]->() RETURN count(r) as relationships" 2>/dev/null \
  | grep -E "^[0-9]+" | paste -sd "," | sed 's/^/  Nodes: /' | sed 's/,/, Relationships: /' || echo "  Empty database"

echo ""
echo "🐘 POSTGRESQL CORE DATABASE"
echo "---------------------------"
echo "📋 Tables:"
docker exec postgres psql -U letta -d letta -c \
  "SELECT schemaname, tablename, n_tup_ins as inserts FROM pg_stat_user_tables ORDER BY n_tup_ins DESC;" 2>/dev/null \
  | head -10 | tail -n +3 | sed 's/^/  • /' || echo "  No tables found"

echo ""
echo "💾 Database Sizes:"
docker exec postgres psql -U letta -d letta -c \
  "SELECT pg_size_pretty(pg_database_size('letta')) as database_size;" 2>/dev/null \
  | tail -n +3 | sed 's/^/  Total Size: /' || echo "  Size unknown"

echo ""
echo "========================================================"
echo "🔄 Run this script anytime: ./monitor_databases.sh"
echo "🌐 Web Interfaces:"
echo "  • Letta API: http://localhost:8283/docs"
echo "  • Weaviate: http://localhost:8080/v1/meta"
echo "  • Neo4j Browser: http://localhost:7474 (neo4j/lettagraph)"
echo "  • Frontend: http://localhost:3000"
echo "========================================================"
