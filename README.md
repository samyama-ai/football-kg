# Football Knowledge Graph

**~30K nodes. ~59K edges. 90 years of FIFA World Cup history -- tournaments, teams, players, goals, bookings, substitutions, penalty kicks, stadiums, managers and referees.**

> Part of the **Samyama** ecosystem — loaded into and queried via the graph engine at [samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph).
> This repo holds the loader and source-data specifics for the KG.

<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="License"></a>

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

### Load from snapshot (recommended)

```bash
# Download (0.4 MB)
curl -LO https://github.com/samyama-ai/samyama-graph/releases/download/kg-snapshots-v8/football.sgsnap

# Start Samyama and import
./target/release/samyama
curl -X POST http://localhost:8080/api/tenants \
  -H 'Content-Type: application/json' \
  -d '{"id":"football","name":"Football KG"}'
curl -X POST http://localhost:8080/api/tenants/football/snapshot/import \
  -F "file=@football.sgsnap"
```

### Build from source

```bash
git clone https://github.com/samyama-ai/football-kg.git && cd football-kg
pip install -e ".[dev]"
mkdir -p data   # place tournaments.csv, teams.csv, stadiums.csv, matches.csv, players.csv,
                # squads.csv, goals.csv, managers.csv (and optionally referees.csv,
                # bookings.csv, substitutions.csv, penalty_kicks.csv, tournament_standings.csv,
                # group_standings.csv) from DataHub here
python -m etl.loader --data-dir data                       # All tournaments
python -m etl.loader --data-dir data --max-tournaments 5    # Quick test
```

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
python -m mcp_server.server --max-tournaments 5          # embedded, quick test
python -m mcp_server.server --url http://localhost:8080  # against a running Samyama server
python -m mcp_server.server --list-tools                 # see all auto-generated + custom tools
```

## Links

| | |
|---|---|
| Samyama Graph | [github.com/samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph) |
| The Book | [samyama-ai.github.io/samyama-graph-book](https://samyama-ai.github.io/samyama-graph-book/) |
| DataHub World Cup Datasets | [datahub.io/collections/football](https://datahub.io/collections/football) |
| Contact | [samyama.dev/contact](https://samyama.dev/contact) |

## License

Apache 2.0. Data from DataHub World Cup Datasets is PDDL (Open Data Commons Public Domain Dedication and License).
