# Football Knowledge Graph

**~30K nodes. ~59K edges. 90 years of FIFA World Cup history -- tournaments, teams, players, goals, bookings, substitutions, penalty kicks, stadiums, managers and referees.**

> Part of the **Samyama** ecosystem — loaded into and queried via the graph engine at [samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph).
> This repo holds the loader and source-data specifics for the KG.

<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="License"></a>
<a href="https://huggingface.co/datasets/VaidhyaMegha/football-kg"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20dataset-VaidhyaMegha%2Ffootball--kg-yellow" alt="HuggingFace dataset"></a>

**The built graph is published as a dataset** -- you do not have to run the ETL to get it:
**[huggingface.co/datasets/VaidhyaMegha/football-kg](https://huggingface.co/datasets/VaidhyaMegha/football-kg)**
(`v1.0`, PDDL). It ships the node and edge CSVs plus `football.sgsnap`. This repository holds
the **code**; that dataset holds the **data**; the snapshot is the **graph**.

```python
from datasets import load_dataset
players = load_dataset("VaidhyaMegha/football-kg", "player", revision="v1.0")
```

> That release is a **subset** of the schema below -- 16,150 nodes and 12,384 edges across
> 8 node labels and 8 edge types, without Referee, Booking, Substitution, PenaltyKick or the
> `PLAYED_FOR` squad edges. See the dataset card's Limitations section.

---

We loaded tournaments, teams, players and goals from DataHub's World Cup datasets, then asked:

> *"Who has scored the most World Cup goals of all time?"*

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player)
WHERE g.own_goal = false
RETURN p.name AS player, count(g) AS goals
ORDER BY goals DESC LIMIT 5
```

| Player | Goals |
|--------|-------|
| **Miroslav Klose** | **16** |
| Ronaldo | 15 |
| Gerd Muller | 14 |
| Just Fontaine | 13 |
| Pele | 12 |

**Flat stat tables give you a leaderboard. A graph gives you connections** -- champion succession, manager lineages, goal-scoring paths across 90 years of World Cup history. Powered by [Samyama Graph](https://github.com/samyama-ai/samyama-graph).

---

## Documentation

New here? Start with the guides:

| Guide | What it covers |
|-------|----------------|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | prerequisites (Python ≥ 3.10) · install · run the engine (Docker) · load the graph · first query |
| **[docs/QUERYING.md](docs/QUERYING.md)** | ask questions via **MCP (Claude)**, the **HTTP API**, or the **Samyama CLI** |
| [docs/100-queries.md](docs/100-queries.md) | 100 example Cypher queries |

---

## Schema

**12 node labels** -- Player (10,401), Manager (475), Referee (493), Goal (3,637), Booking (3,178), Substitution (10,222), PenaltyKick (396), Stadium (240), Team (88), Match (1,248), Country (110), Tournament (30)

**19 edge types** -- IN_TOURNAMENT, HOME_TEAM, AWAY_TEAM, PLAYED_AT, HOSTED_BY, WON_BY, FINISHED, IN_GROUP, PLAYED_FOR, SCORED_IN, SCORED_BY, FOR_TEAM, IN_MATCH, BOOKED, INVOLVES, TAKEN_BY, FROM

| Node label | Key properties |
|------------|----------------|
| Player | player_id, name, family_name, given_name, birth_date, female, position, count_tournaments |
| Manager | manager_id, name, family_name, given_name, female, country |
| Referee | referee_id, name, family_name, given_name, female, country, confederation |
| Goal | goal_id, minute, minute_stoppage, own_goal, penalty, period |
| Booking | booking_id, minute, period, yellow_card, red_card, second_yellow_card, sending_off |
| Substitution | substitution_id, minute, period, going_off, coming_on |
| PenaltyKick | penalty_kick_id, converted |
| Stadium | stadium_id, name, city, country, capacity |
| Team | team_id, name, code, confederation, confederation_code, region, mens_team, womens_team |
| Match | match_id, name, date, time, stage, group_name, home_score, away_score, result, extra_time, penalty_shootout |
| Country | name |
| Tournament | tournament_id, name, year, start_date, end_date, host_country, winner, host_won, count_teams |

`PLAYED_FOR` carries per-tournament context (`tournament_id`, `position`, `shirt_number`) since a player's squad role can change across World Cups. `FINISHED` and `IN_GROUP` carry standings data (`position`, `points`, `wins`, etc.) on the edge itself, same pattern as cricket-kg's `WON` edge.

**Data source** -- [DataHub World Cup Datasets](https://datahub.io/collections/football) (PDDL): `tournaments.csv`, `teams.csv`, `stadiums.csv`, `matches.csv`, `players.csv`, `squads.csv`, `goals.csv`, `managers.csv`, and optionally `referees.csv`, `bookings.csv`, `substitutions.csv`, `penalty_kicks.csv`, `tournament_standings.csv`, `group_standings.csv`

## Quick Start

**Full walkthrough → [GETTING_STARTED.md](GETTING_STARTED.md)** (prerequisites, Docker, loading, querying).

Fastest path — run the engine and import the published snapshot into the `football` tenant
(needs **Python ≥ 3.10** for the tooling and **Docker** for the engine):

```bash
pip install -r requirements.txt
docker run --rm -p 8080:8080 -p 6379:6379 public.ecr.aws/f9f6l5u4/samyama-graph:1.1.0

curl -LO https://github.com/samyama-ai/samyama-graph/releases/download/kg-snapshots-v8/football.sgsnap  # ~0.4 MB
curl -X POST http://localhost:8080/api/tenants -H 'Content-Type: application/json' -d '{"id":"football","name":"Football KG"}'
curl -X POST http://localhost:8080/api/tenants/football/snapshot/import -F "file=@football.sgsnap"
```

Prefer to build from the DataHub CSVs instead of the snapshot? See
[GETTING_STARTED.md](GETTING_STARTED.md) §4B. To query it (Claude / HTTP / CLI), see
[docs/QUERYING.md](docs/QUERYING.md).

## Example Queries

```cypher
-- Top World Cup winners (men's + women's; Germany and West Germany are
-- distinct Team nodes, matching how the source data models them)
MATCH (t:Tournament)-[:WON_BY]->(team:Team)
RETURN team.name, count(t) AS titles
ORDER BY titles DESC LIMIT 5
-- Brazil (5), United States (4), Italy (4), Argentina (3), Germany (3)

-- Busiest stadiums
MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium)
RETURN s.name, s.city, count(m) AS matches
ORDER BY matches DESC LIMIT 5
```

See the full **[100-query showcase](docs/100-queries.md)** -- from single-table aggregations to network intelligence that SQL cannot express.

## MCP Server

```bash
python -m mcp_server.server --max-tournaments 5                          # embedded, quick test
python -m mcp_server.server --url http://localhost:8080 --graph football # against a running Samyama server
python -m mcp_server.server --list-tools                                 # see all auto-generated + custom tools
```

Register it with Claude and ask questions in natural language — see **[docs/QUERYING.md](docs/QUERYING.md)**.

## Links

| | |
|---|---|
| **Published dataset** | **[huggingface.co/datasets/VaidhyaMegha/football-kg](https://huggingface.co/datasets/VaidhyaMegha/football-kg)** |
| Samyama Graph | [github.com/samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph) |
| The Book | [samyama-ai.github.io/samyama-graph-book](https://samyama-ai.github.io/samyama-graph-book/) |
| DataHub World Cup Datasets | [datahub.io/collections/football](https://datahub.io/collections/football) |
| Contact | [samyama.dev/contact](https://samyama.dev/contact) |

## License

Apache 2.0 covers the **code** in this repository. The **data** is a separate matter: it comes
from the DataHub World Cup Datasets under **PDDL** (Open Data Commons Public Domain Dedication
and License), and PDDL -- not Apache 2.0 -- is what governs the
[published dataset](https://huggingface.co/datasets/VaidhyaMegha/football-kg) and any
redistribution of it.
