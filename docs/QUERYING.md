# Querying the Football KG

Three ways to ask the graph questions, once it's loaded into the `football` tenant on a running engine
(see [GETTING_STARTED.md](../GETTING_STARTED.md)). All examples below were run live and return real results.

> **Heads-up:** on the current published snapshot, `Player` and `Manager` names come back `null`
> (those nodes carry vector embeddings). Team / Stadium / Tournament / Country names query normally, so
> the examples here use those. For player-level queries by name, build from source (see GETTING_STARTED §4B).

---

## 1. Claude, over MCP (natural language)

```bash
# register this KG's MCP server with Claude Code (once), pointed at the running engine:
claude mcp add football -- python -m mcp_server.server --url http://localhost:8080 --graph football

# start a new Claude Code session (MCP servers load at session start), then just ask:
#   "which stadiums hosted the most World Cup matches?"   → Estadio Azteca (19)
#   "which nations have hosted the most World Cups?"       → United States & France (3 each)
```

*(No engine? `python -m mcp_server.server --max-tournaments 5` loads a small graph in-memory and
serves it — good for a quick local demo.)*

## 2. HTTP API (`POST /api/query`)

```bash
curl -s -X POST http://localhost:8080/api/query -H 'Content-Type: application/json' -d '{
  "graph": "football",
  "query": "MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium) RETURN s.name AS stadium, s.city AS city, count(m) AS matches ORDER BY matches DESC LIMIT 3"
}'
```
```json
{"columns":["stadium","city","matches"],
 "records":[["Estadio Azteca","Mexico City",19],["Parc des Princes","Paris",16],["Estádio do Maracanã","Rio de Janeiro",15]]}
```

## 3. Samyama CLI (Redis wire protocol, `:6379`)

```bash
redis-cli -p 6379 GRAPH.QUERY football \
  "MATCH (t:Tournament) RETURN t.host_country, count(t) AS times ORDER BY times DESC LIMIT 3"
# 1) "United States" 3
# 2) "France"        3
# 3) "Brazil"        2
```

---

## More queries
See **[100-queries.md](100-queries.md)** for 100 example Cypher queries, and the
[schema](../README.md#schema) for the node/edge model.
