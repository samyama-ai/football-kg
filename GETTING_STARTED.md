# Getting Started — Football Knowledge Graph

From `git clone` to your first answer. The **snapshot path** is the fastest (a few minutes).

---

## 1. Prerequisites

- **Python ≥ 3.10** (required by the `samyama` SDK; macOS ships 3.9 — use `python3.10`+).
- **git**
- **Docker** — to run the Samyama engine (needed for the snapshot import and for serving MCP / CLI / API).

## 2. Install

```bash
git clone https://github.com/samyama-ai/football-kg.git
cd football-kg
python3 -m venv .venv && source .venv/bin/activate     # Python >= 3.10
pip install -r requirements.txt                         # note: pulls torch (~large) for semantic search
```

## 3. Run the engine (Docker)

```bash
docker run --rm -p 8080:8080 -p 6379:6379 public.ecr.aws/f9f6l5u4/samyama-graph:1.1.0
```

## 4. Load the graph — into the `football` tenant

### Option A — snapshot (recommended, ~seconds)
```bash
curl -LO https://github.com/samyama-ai/samyama-graph/releases/download/kg-snapshots-v8/football.sgsnap  # ~0.4 MB
curl -X POST http://localhost:8080/api/tenants -H 'Content-Type: application/json' \
  -d '{"id":"football","name":"Football KG"}'
curl -X POST http://localhost:8080/api/tenants/football/snapshot/import -F "file=@football.sgsnap"
```

### Option B — build from source (from DataHub CSVs)
```bash
mkdir -p data   # place tournaments.csv, teams.csv, stadiums.csv, matches.csv, players.csv,
                # squads.csv, goals.csv, managers.csv (and optionally referees.csv, bookings.csv,
                # substitutions.csv, penalty_kicks.csv, tournament_standings.csv, group_standings.csv)
                # from https://datahub.io/collections/football here
python -m etl.loader --data-dir data --url http://localhost:8080                  # all tournaments
python -m etl.loader --data-dir data --url http://localhost:8080 --max-tournaments 5   # quick test
```
*(Both load into the `football` tenant. Omit `--url` to build an in-memory graph instead. Build-from-source
carries the full schema — teams' `WON_BY` titles, referees, bookings, etc. — which the compact snapshot omits.)*

## 5. Ask your first question

Fastest is **Claude over MCP** — see **[docs/QUERYING.md](docs/QUERYING.md)**. Quick check over HTTP —
busiest World Cup stadiums:

```bash
curl -s -X POST http://localhost:8080/api/query -H 'Content-Type: application/json' -d '{
  "graph": "football",
  "query": "MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium) RETURN s.name AS stadium, s.city AS city, count(m) AS matches ORDER BY matches DESC LIMIT 5"
}'
# → Estadio Azteca / Mexico City (19), Parc des Princes / Paris (16), Maracanã / Rio (15), ...
```

> **Note on the snapshot:** `Player` and `Manager` nodes carry vector embeddings, so their `name`
> property is not returned by Cypher on the current published snapshot (you'll get `null` names;
> `player_id` still works). Team / Stadium / Tournament names query normally. The snapshot is also a
> compact subset (8 node labels / 8 edge types) — for the full schema (e.g. `WON_BY` titles), build
> from source (§4B).

## 6. The ETL pipeline

- Data source: **DataHub World Cup datasets** (CSV).
- `etl/loader.py` — builds the graph (Tournament, Team, Match, Stadium, Player, Goal, … + IN_TOURNAMENT /
  PLAYED_AT / SCORED_BY / …). Run `python -m etl.loader --help` for options.

## Next
- **[docs/QUERYING.md](docs/QUERYING.md)** — MCP (Claude), HTTP API, and the Samyama CLI
- **[docs/100-queries.md](docs/100-queries.md)** — 100 example queries · **[README](README.md#schema)** — schema
