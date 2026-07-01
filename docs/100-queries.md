# 100 Cypher Queries for the Football Knowledge Graph

**~1,248 matches | ~10,401 players | ~88 teams | ~30 tournaments | ~240 stadiums | ~475 managers | ~493 referees | ~3,637 goals | ~3,178 bookings | ~10,222 substitutions | ~396 penalty kicks**

These queries are organized in five progressive levels that illustrate where relational databases hit their ceiling and where graph databases take over.

| Level | Name | SQL Equivalent | Queries |
|-------|------|----------------|---------|
| 1 | **Foundation** | Single table, GROUP BY | 1--15 |
| 2 | **Relational Joins** | 2-table JOIN | 16--35 |
| 3 | **Multi-hop Traversals** | 3--5 JOINs, self-joins | 36--60 |
| 4 | **Path & Pattern Analytics** | Recursive CTEs, breaks down | 61--80 |
| 5 | **Network Intelligence** | Impossible in SQL | 81--100 |

---

## Level 1: Foundation (SQL-equivalent)

*These queries scan a single node type or edge type. Any RDBMS handles them trivially with a single table and GROUP BY.*

### 1. Total tournaments by decade

```cypher
MATCH (t:Tournament)
RETURN (toInteger(t.year) / 10) * 10 AS decade, count(t) AS tournaments
ORDER BY decade
```

### 2. Matches per tournament

```cypher
MATCH (t:Tournament)
RETURN t.name AS tournament, t.count_teams AS teams
ORDER BY t.year DESC
```

### 3. Total players in the dataset

```cypher
MATCH (n:Player) RETURN count(n) AS total_players
```

### 4. Players by position

```cypher
MATCH (p:Player)
RETURN p.position AS position, count(p) AS players
ORDER BY players DESC
```

### 5. Matches by stage

```cypher
MATCH (m:Match)
RETURN m.stage AS stage, count(m) AS matches
ORDER BY matches DESC
```

### 6. Highest individual match scorelines

```cypher
MATCH (m:Match)
WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
RETURN m.name AS match, m.date AS date, m.home_score AS home, m.away_score AS away
ORDER BY m.home_score + m.away_score DESC
LIMIT 25
```

### 7. Teams by confederation

```cypher
MATCH (team:Team)
RETURN team.confederation AS confederation, count(team) AS teams
ORDER BY teams DESC
```

### 8. Stadiums by capacity

```cypher
MATCH (s:Stadium)
RETURN s.name AS stadium, s.city AS city, s.capacity AS capacity
ORDER BY capacity DESC
LIMIT 20
```

### 9. Goals by period (first half, second half, extra time)

```cypher
MATCH (g:Goal)
RETURN g.period AS period, count(g) AS goals
ORDER BY goals DESC
```

### 10. Penalty goals count

```cypher
MATCH (g:Goal)
WHERE g.penalty = true
RETURN count(g) AS penalty_goals
```

### 11. Own goals count

```cypher
MATCH (g:Goal)
WHERE g.own_goal = true
RETURN count(g) AS own_goals
```

### 12. Countries in the dataset

```cypher
MATCH (c:Country) RETURN c.name AS country ORDER BY country
```

### 13. Managers by country

```cypher
MATCH (mgr:Manager)
RETURN mgr.country AS country, count(mgr) AS managers
ORDER BY managers DESC
LIMIT 20
```

### 14. Tournament host countries

```cypher
MATCH (t:Tournament)
RETURN t.host_country AS host, t.year AS year
ORDER BY year
```

### 15. Team codes lookup

```cypher
MATCH (t:Team)
RETURN t.code AS code, t.name AS name
ORDER BY t.name
```

---

## Level 2: Relational Joins (2-table JOIN equivalent)

*These queries traverse exactly one edge — the equivalent of a single SQL JOIN.*

### 16. Top goal scorers of all time

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player)
WHERE g.own_goal = false
RETURN p.name AS player, count(g) AS goals
ORDER BY goals DESC LIMIT 20
```

### 17. World Cup winners by team

```cypher
MATCH (t:Tournament)-[:WON_BY]->(team:Team)
RETURN team.name AS team, count(t) AS titles
ORDER BY titles DESC
```

### 18. Matches hosted per stadium

```cypher
MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium)
RETURN s.name AS stadium, count(m) AS matches
ORDER BY matches DESC LIMIT 20
```

### 19. Tournaments hosted per country

```cypher
MATCH (t:Tournament)-[:HOSTED_BY]->(c:Country)
RETURN c.name AS country, count(t) AS tournaments
ORDER BY tournaments DESC
```

### 20. Referees grouped by home country

```cypher
MATCH (r:Referee)-[:FROM]->(c:Country)
RETURN c.name AS country, collect(r.name) AS referees
ORDER BY country
```

### 21. Matches per tournament

```cypher
MATCH (m:Match)-[:IN_TOURNAMENT]->(t:Tournament)
RETURN t.name AS tournament, count(m) AS matches
ORDER BY matches DESC
```

### 22. Home team appearances

```cypher
MATCH (m:Match)-[:HOME_TEAM]->(t:Team)
RETURN t.name AS team, count(m) AS home_matches
ORDER BY home_matches DESC LIMIT 20
```

### 23. Away team appearances

```cypher
MATCH (m:Match)-[:AWAY_TEAM]->(t:Team)
RETURN t.name AS team, count(m) AS away_matches
ORDER BY away_matches DESC LIMIT 20
```

### 24. Squad size per team roster

```cypher
MATCH (p:Player)-[:PLAYED_FOR]->(t:Team)
RETURN t.name AS team, count(p) AS squad_size
ORDER BY squad_size DESC LIMIT 20
```

### 25. Card bookings per match

```cypher
MATCH (b:Booking)-[:IN_MATCH]->(m:Match)
RETURN m.name AS match, count(b) AS bookings
ORDER BY bookings DESC LIMIT 20
```

### 26. Goals scored in each match

```cypher
MATCH (g:Goal)-[:SCORED_IN]->(m:Match)
RETURN m.name AS match, count(g) AS goals
ORDER BY goals DESC LIMIT 20
```

### 27. Multi-tournament veterans (3+ tournaments)

```cypher
MATCH (p:Player)
WHERE p.count_tournaments >= 3
RETURN p.name AS player, p.count_tournaments AS tournaments
ORDER BY tournaments DESC
```

### 28. Stadium locations by country

```cypher
MATCH (s:Stadium)
RETURN s.country AS country, count(s) AS stadiums
ORDER BY stadiums DESC
```

### 29. Tournament team counts over time

```cypher
MATCH (t:Tournament)
RETURN t.year AS year, t.count_teams AS teams
ORDER BY year
```

### 30. Position breakdown of goal scorers

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player)
WHERE g.own_goal = false
RETURN p.position AS position, count(g) AS goals
ORDER BY goals DESC
```

### 31. Team codes that never hosted a tournament win

```cypher
-- pattern predicates aren't supported in WHERE here, so use OPTIONAL MATCH + IS NULL instead
MATCH (team:Team)
OPTIONAL MATCH (t:Tournament)-[:WON_BY]->(team)
WITH team, count(t) AS wins
WHERE wins = 0
RETURN team.name AS team
ORDER BY team LIMIT 25
```

### 32. Stadiums per city

```cypher
MATCH (s:Stadium)
RETURN s.city AS city, count(s) AS stadiums
ORDER BY stadiums DESC LIMIT 20
```

### 33. Goals per stadium

```cypher
MATCH (g:Goal)-[:SCORED_IN]->(m:Match)-[:PLAYED_AT]->(s:Stadium)
RETURN s.name AS stadium, count(g) AS goals
ORDER BY goals DESC LIMIT 20
```

### 34. Draws (result breakdown)

```cypher
MATCH (m:Match)
RETURN m.result AS result, count(m) AS matches
ORDER BY matches DESC
```

### 35. Confederation representation across tournaments

```cypher
-- this engine doesn't support [:TYPE1|TYPE2] alternation, so home/away
-- appearances are matched separately and summed per team first
MATCH (t:Team)
OPTIONAL MATCH (t)<-[:HOME_TEAM]-(hm:Match)
OPTIONAL MATCH (t)<-[:AWAY_TEAM]-(am:Match)
WITH t.confederation AS confederation, count(DISTINCT hm) + count(DISTINCT am) AS team_matches
RETURN confederation, sum(team_matches) AS matches
ORDER BY matches DESC
```

---

## Level 3: Multi-hop Traversals (3-5 JOINs, self-joins)

*These queries chain multiple edges — analogous to 3-5 table SQL JOINs, several of them self-joins on Team or Player.*

### 36. Highest scoring matches with stadium context

```cypher
MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium)
WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
RETURN m.name AS match, s.name AS stadium, m.home_score + m.away_score AS total_goals
ORDER BY total_goals DESC LIMIT 15
```

### 37. Head-to-head: Brazil vs Germany

```cypher
MATCH (t1:Team)<-[:HOME_TEAM]-(m:Match)-[:AWAY_TEAM]->(t2:Team)
WHERE (t1.name = "Brazil" AND t2.name = "Germany")
   OR (t1.name = "Germany" AND t2.name = "Brazil")
RETURN m.name AS match, m.date AS date, m.home_score AS home_score, m.away_score AS away_score
ORDER BY m.date
```

### 38. Goal scorers who also played in the final

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player)-[:PLAYED_FOR]->(t:Team), (m:Match)-[:HOME_TEAM]->(t)
WHERE m.stage = "final"
RETURN DISTINCT p.name AS player, t.name AS team
UNION
MATCH (g:Goal)-[:SCORED_BY]->(p:Player)-[:PLAYED_FOR]->(t:Team), (m:Match)-[:AWAY_TEAM]->(t)
WHERE m.stage = "final"
RETURN DISTINCT p.name AS player, t.name AS team
```

### 39. Penalty kicks in tournament finals

```cypher
MATCH (pk:PenaltyKick)-[:IN_MATCH]->(m:Match)-[:IN_TOURNAMENT]->(t:Tournament)
WHERE m.stage = "final"
RETURN t.name AS tournament, m.name AS match, pk.converted AS converted
ORDER BY t.year DESC
```

### 40. Goals scored by players from a specific confederation

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player)-[:PLAYED_FOR]->(t:Team)
WHERE g.own_goal = false AND t.confederation = "UEFA"
RETURN p.name AS player, count(g) AS goals
ORDER BY goals DESC LIMIT 15
```

### 41. Players who scored in more than one tournament

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player)
WHERE p.count_tournaments >= 2 AND g.own_goal = false
RETURN p.name AS player, count(g) AS goals, p.count_tournaments AS tournaments
ORDER BY goals DESC LIMIT 20
```

### 42. Stadiums that hosted a tournament final

```cypher
MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium), (m)-[:IN_TOURNAMENT]->(t:Tournament)
WHERE m.stage = "final"
RETURN t.name AS tournament, s.name AS stadium, s.city AS city
ORDER BY t.name
```

### 43. Teams that won a tournament they hosted

```cypher
-- Team names in this dataset match national-team country names directly
-- (there's no separate Team-country edge, so we compare on name)
MATCH (t:Tournament)-[:WON_BY]->(team:Team)
WHERE team.name = t.host_country
RETURN t.name AS tournament, team.name AS champion
```

### 44. Players who were booked and still scored in the same match

```cypher
MATCH (b:Booking)-[:BOOKED]->(p:Player), (b)-[:IN_MATCH]->(m:Match),
      (g:Goal)-[:SCORED_BY]->(p), (g)-[:SCORED_IN]->(m)
WHERE g.own_goal = false
RETURN p.name AS player, m.name AS match, b.minute AS booked_minute, g.minute AS goal_minute
ORDER BY m.date
```

### 45. Players who faced the host nation

```cypher
MATCH (t:Tournament)-[:HOSTED_BY]->(c:Country), (m:Match)-[:IN_TOURNAMENT]->(t),
      (m)-[:HOME_TEAM]->(host:Team), (m)-[:AWAY_TEAM]->(opponent:Team)
WHERE host.name = c.name
MATCH (p:Player)-[:PLAYED_FOR]->(opponent)
RETURN DISTINCT p.name AS player, opponent.name AS team, host.name AS host_team
UNION
MATCH (t:Tournament)-[:HOSTED_BY]->(c:Country), (m:Match)-[:IN_TOURNAMENT]->(t),
      (m)-[:AWAY_TEAM]->(host:Team), (m)-[:HOME_TEAM]->(opponent:Team)
WHERE host.name = c.name
MATCH (p:Player)-[:PLAYED_FOR]->(opponent)
RETURN DISTINCT p.name AS player, opponent.name AS team, host.name AS host_team
LIMIT 25
```

### 46. Average goals per match by tournament

```cypher
MATCH (m:Match)-[:IN_TOURNAMENT]->(t:Tournament)
WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
RETURN t.name AS tournament, avg(m.home_score + m.away_score) AS avg_goals
ORDER BY avg_goals DESC
```

### 47. Teams that scored in every match of a tournament

```cypher
MATCH (g:Goal)-[:SCORED_IN]->(m:Match)-[:IN_TOURNAMENT]->(tourn:Tournament),
      (g)-[:SCORED_BY]->(:Player)-[:PLAYED_FOR]->(t:Team)
RETURN tourn.name AS tournament, t.name AS team, count(DISTINCT m) AS matches_with_goal
ORDER BY matches_with_goal DESC LIMIT 20
```

### 48. Players who scored against the eventual champion

```cypher
MATCH (t:Tournament)-[:WON_BY]->(champion:Team),
      (m:Match)-[:IN_TOURNAMENT]->(t), (m)-[:HOME_TEAM]->(champion),
      (g:Goal)-[:SCORED_IN]->(m), (g)-[:SCORED_BY]->(p:Player)-[:PLAYED_FOR]->(opponent:Team)
WHERE opponent <> champion AND g.own_goal = false
RETURN p.name AS player, champion.name AS beat_eventual_champion_goal_against, t.name AS tournament
UNION
MATCH (t:Tournament)-[:WON_BY]->(champion:Team),
      (m:Match)-[:IN_TOURNAMENT]->(t), (m)-[:AWAY_TEAM]->(champion),
      (g:Goal)-[:SCORED_IN]->(m), (g)-[:SCORED_BY]->(p:Player)-[:PLAYED_FOR]->(opponent:Team)
WHERE opponent <> champion AND g.own_goal = false
RETURN p.name AS player, champion.name AS beat_eventual_champion_goal_against, t.name AS tournament
```

### 49. Stadium usage across multiple tournaments

```cypher
MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium), (m)-[:IN_TOURNAMENT]->(t:Tournament)
RETURN s.name AS stadium, count(DISTINCT t) AS tournaments_hosted
ORDER BY tournaments_hosted DESC LIMIT 15
```

### 50. Players substituted and later booked in the same match

```cypher
MATCH (sub:Substitution)-[:INVOLVES]->(p:Player), (sub)-[:IN_MATCH]->(m:Match),
      (b:Booking)-[:BOOKED]->(p), (b)-[:IN_MATCH]->(m)
RETURN p.name AS player, m.name AS match, sub.minute AS sub_minute, b.minute AS booked_minute
ORDER BY m.date
```

### 51. Goal minute distribution for a tournament

```cypher
MATCH (g:Goal)-[:SCORED_IN]->(m:Match)-[:IN_TOURNAMENT]->(t:Tournament)
WHERE t.name = "2014 FIFA World Cup" AND g.minute IS NOT NULL
RETURN (g.minute / 15) * 15 AS minute_bucket, count(g) AS goals
ORDER BY minute_bucket
```

### 52. Penalty conversion rate by tournament stage

```cypher
MATCH (pk:PenaltyKick)-[:IN_MATCH]->(m:Match)
RETURN m.stage AS stage, count(pk) AS attempts,
       count(CASE WHEN pk.converted = true THEN 1 END) AS converted
ORDER BY attempts DESC
```

### 53. Semi-finalists per tournament

```cypher
MATCH (m:Match)-[:IN_TOURNAMENT]->(t:Tournament)
WHERE m.stage CONTAINS "semi-final"
OPTIONAL MATCH (m)-[:HOME_TEAM]->(ht:Team)
OPTIONAL MATCH (m)-[:AWAY_TEAM]->(at:Team)
RETURN t.name AS tournament, collect(DISTINCT ht.name) AS home_semifinalists,
       collect(DISTINCT at.name) AS away_semifinalists
ORDER BY t.name
```

### 54. Players from non-host nations who scored at that tournament

```cypher
MATCH (t:Tournament)-[:HOSTED_BY]->(hc:Country), (m:Match)-[:IN_TOURNAMENT]->(t),
      (g:Goal)-[:SCORED_IN]->(m), (g)-[:SCORED_BY]->(p:Player)-[:PLAYED_FOR]->(team:Team)
WHERE team.name <> hc.name AND g.own_goal = false
RETURN DISTINCT p.name AS player, team.name AS player_team, hc.name AS host_country
LIMIT 25
```

### 55. Tournament finals and their goal tallies

```cypher
MATCH (m:Match)-[:IN_TOURNAMENT]->(t:Tournament)
WHERE m.stage = "final"
RETURN t.name AS tournament, m.home_score + m.away_score AS goals
ORDER BY t.year DESC
```

### 56. Stadiums in the winning country

```cypher
MATCH (t:Tournament)-[:WON_BY]->(team:Team), (s:Stadium)
WHERE s.country = team.name
RETURN DISTINCT t.name AS tournament, team.name AS champion, collect(DISTINCT s.name) AS stadiums
```

### 57. Player positions among top scorers

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player)
WHERE g.own_goal = false
WITH p, count(g) AS goals
WHERE goals >= 3
RETURN p.position AS position, count(p) AS scorers, sum(goals) AS total_goals
ORDER BY total_goals DESC
```

### 58. Teams beaten by the tournament champion

```cypher
MATCH (t:Tournament)-[:WON_BY]->(champion:Team),
      (m:Match)-[:IN_TOURNAMENT]->(t), (m)-[:HOME_TEAM]->(champion), (m)-[:AWAY_TEAM]->(loser:Team)
WHERE m.home_score > m.away_score
RETURN t.name AS tournament, champion.name AS champion, collect(loser.name) AS beaten_away
```

### 59. Impact substitutes: goals scored after coming on

```cypher
MATCH (sub:Substitution)-[:INVOLVES]->(p:Player), (sub)-[:IN_MATCH]->(m:Match),
      (g:Goal)-[:SCORED_BY]->(p), (g)-[:SCORED_IN]->(m)
WHERE sub.coming_on = true AND g.minute > sub.minute
RETURN p.name AS player, m.name AS match, sub.minute AS came_on, g.minute AS scored
ORDER BY g.minute - sub.minute ASC LIMIT 20
```

### 60. Cross-tournament team confederation dominance

```cypher
MATCH (t:Tournament)-[:WON_BY]->(team:Team)
RETURN team.confederation AS confederation, count(t) AS titles
ORDER BY titles DESC
```

---

## Level 4: Path & Pattern Analytics (recursive CTEs, breaks down in SQL)

*These queries express variable-length paths and structural patterns that push relational recursive CTEs to their limit.*

### 61. Shortest connection between two players via shared teams

```cypher
MATCH path = shortestPath(
  (p1:Player {player_id: "p1"})-[:PLAYED_FOR*..6]-(p2:Player {player_id: "p2"})
)
RETURN [n IN nodes(path) | n.name] AS chain
```

### 62. All teams reachable from a champion within 2 head-to-head hops

```cypher
-- a match has exactly one home and one away side, so "either direction" expands
-- to the 4 concrete home/away combinations across two hops, unioned together
MATCH (champion:Team)<-[:HOME_TEAM]-(m1:Match)-[:AWAY_TEAM]->(opp1:Team),
      (opp1)<-[:HOME_TEAM]-(m2:Match)-[:AWAY_TEAM]->(opp2:Team)
WHERE champion.name = "Germany" AND opp2 <> champion
RETURN DISTINCT opp2.name AS two_hop_opponent
UNION
MATCH (champion:Team)<-[:HOME_TEAM]-(m1:Match)-[:AWAY_TEAM]->(opp1:Team),
      (opp1)<-[:AWAY_TEAM]-(m2:Match)-[:HOME_TEAM]->(opp2:Team)
WHERE champion.name = "Germany" AND opp2 <> champion
RETURN DISTINCT opp2.name AS two_hop_opponent
UNION
MATCH (champion:Team)<-[:AWAY_TEAM]-(m1:Match)-[:HOME_TEAM]->(opp1:Team),
      (opp1)<-[:HOME_TEAM]-(m2:Match)-[:AWAY_TEAM]->(opp2:Team)
WHERE champion.name = "Germany" AND opp2 <> champion
RETURN DISTINCT opp2.name AS two_hop_opponent
UNION
MATCH (champion:Team)<-[:AWAY_TEAM]-(m1:Match)-[:HOME_TEAM]->(opp1:Team),
      (opp1)<-[:AWAY_TEAM]-(m2:Match)-[:HOME_TEAM]->(opp2:Team)
WHERE champion.name = "Germany" AND opp2 <> champion
RETURN DISTINCT opp2.name AS two_hop_opponent
LIMIT 25
```

### 63. Player pairs linked via a shared booking in the same match

```cypher
MATCH (b1:Booking)-[:IN_MATCH]->(m:Match)<-[:IN_MATCH]-(b2:Booking),
      (b1)-[:BOOKED]->(p1:Player), (b2)-[:BOOKED]->(p2:Player)
WHERE p1 <> p2
RETURN m.name AS match, p1.name AS player1, p2.name AS player2 LIMIT 20
```

### 64. Player co-appearance network within a single squad

```cypher
MATCH (p1:Player)-[:PLAYED_FOR]->(t:Team)<-[:PLAYED_FOR]-(p2:Player)
WHERE p1 <> p2 AND t.name = "Germany"
RETURN p1.name AS player1, p2.name AS player2 LIMIT 20
```

### 65. Back-to-back title defenses (this engine has no UNWIND, so this is a self-join instead of a list expansion)

```cypher
MATCH (t1:Tournament)-[:WON_BY]->(team:Team), (t2:Tournament)-[:WON_BY]->(team)
WHERE t2.year = t1.year + 4
RETURN team.name AS team, t1.year AS win_year, t2.year AS defended_in
ORDER BY team.name, t1.year
```

### 66. Goal-scoring paths: player -> match -> stadium -> city cluster

```cypher
MATCH (p:Player)<-[:SCORED_BY]-(g:Goal)-[:SCORED_IN]->(m:Match)-[:PLAYED_AT]->(s:Stadium)
WHERE g.own_goal = false
RETURN s.city AS city, count(DISTINCT p) AS distinct_scorers
ORDER BY distinct_scorers DESC LIMIT 20
```

### 67. Host nations that saw a different country lift the trophy

```cypher
MATCH (c1:Country)<-[:HOSTED_BY]-(t:Tournament)-[:WON_BY]->(team:Team)
WHERE c1.name <> team.name
RETURN c1.name AS host, team.name AS champion, t.year AS year
ORDER BY year LIMIT 25
```

### 68. Player transfer-like pattern: same player, multiple team edges (roster changes)

```cypher
MATCH (p:Player)-[:PLAYED_FOR]->(t:Team)
WITH p, collect(DISTINCT t.name) AS teams
WHERE size(teams) > 1
RETURN p.name AS player, teams
```

### 69. Tournament bracket depth: matches per stage as a funnel

```cypher
MATCH (m:Match)-[:IN_TOURNAMENT]->(t:Tournament)
WHERE t.name = "2014 FIFA World Cup"
RETURN m.stage AS stage, count(m) AS matches
ORDER BY matches DESC
```

### 70. Countries that both hosted and won a World Cup

```cypher
-- pattern predicates aren't supported in WHERE here, so both conditions are plain MATCH
-- clauses, and inline node properties can't reference a variable, so WHERE compares instead
MATCH (c:Country)
MATCH (:Tournament)-[:HOSTED_BY]->(c)
MATCH (:Tournament)-[:WON_BY]->(team:Team)
WHERE team.name = c.name
RETURN DISTINCT c.name AS country
```

### 71. Goal chains: players who scored in consecutive tournament stages

```cypher
MATCH (p:Player)<-[:SCORED_BY]-(g1:Goal)-[:SCORED_IN]->(m1:Match),
      (p)<-[:SCORED_BY]-(g2:Goal)-[:SCORED_IN]->(m2:Match)
WHERE m1.stage CONTAINS "semi-final" AND m2.stage = "final" AND g1 <> g2
RETURN DISTINCT p.name AS player
```

### 72. Stadium clusters by shared city hosting multiple tournaments

```cypher
MATCH (s:Stadium)<-[:PLAYED_AT]-(m:Match)-[:IN_TOURNAMENT]->(t:Tournament)
WITH s.city AS city, collect(DISTINCT t.name) AS tournaments
WHERE size(tournaments) > 1
RETURN city, tournaments
```

### 73. Shortest path between two teams via shared stadiums

```cypher
-- this engine has no relationship-type alternation, even inside variable-length
-- paths, so the path is left untyped (any relationship) rather than restricted
-- to HOME_TEAM|AWAY_TEAM|PLAYED_AT
MATCH path = shortestPath(
  (t1:Team {code: "BRA"})-[*..6]-(t2:Team {code: "GER"})
)
RETURN length(path) AS hops, path LIMIT 5
```

### 74. Confederation rivalry graph: cross-confederation matches

```cypher
MATCH (m:Match)-[:HOME_TEAM]->(t1:Team), (m)-[:AWAY_TEAM]->(t2:Team)
WHERE t1.confederation <> t2.confederation
RETURN t1.confederation AS conf1, t2.confederation AS conf2, count(m) AS matches
ORDER BY matches DESC
```

### 75. Player position clusters by shared team and tournament

```cypher
MATCH (p1:Player)-[:PLAYED_FOR]->(t:Team)<-[:PLAYED_FOR]-(p2:Player)
WHERE p1.position = p2.position AND p1 <> p2
RETURN p1.position AS position, count(*) AS teammate_pairs
ORDER BY teammate_pairs DESC
```

### 76. Tournament-to-tournament team continuity

```cypher
-- simplified to home-side appearances only (no relationship-type alternation
-- in this engine); PLAYED_FOR already gives full squad-level continuity too
MATCH (t1:Tournament)<-[:IN_TOURNAMENT]-(m1:Match)-[:HOME_TEAM]->(team:Team),
      (t2:Tournament)<-[:IN_TOURNAMENT]-(m2:Match)-[:HOME_TEAM]->(team)
WHERE t1.year < t2.year
RETURN DISTINCT team.name AS team, t1.year AS from_year, t2.year AS to_year
ORDER BY team.name LIMIT 25
```

### 77. Goal networks: scorers and assisting stage context

```cypher
MATCH (g:Goal)-[:SCORED_IN]->(m:Match)
WHERE g.penalty = true
RETURN m.stage AS stage, count(g) AS penalty_goals
ORDER BY penalty_goals DESC
```

### 78. Triangle of teams connected via shared stadiums

```cypher
-- simplified to home-side appearances only (no relationship-type alternation)
MATCH (t1:Team)<-[:HOME_TEAM]-(:Match)-[:PLAYED_AT]->(s:Stadium)<-[:PLAYED_AT]-(:Match)-[:HOME_TEAM]->(t2:Team),
      (t2)<-[:HOME_TEAM]-(:Match)-[:PLAYED_AT]->(s)<-[:PLAYED_AT]-(:Match)-[:HOME_TEAM]->(t3:Team)
WHERE t1 <> t2 AND t2 <> t3 AND t1 <> t3
RETURN DISTINCT t1.name AS team1, t2.name AS team2, t3.name AS team3, s.name AS shared_stadium LIMIT 10
```

### 79. Stadiums forming a "final host" lineage across decades

```cypher
MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium), (m)-[:IN_TOURNAMENT]->(t:Tournament)
WHERE m.stage = "final"
RETURN s.name AS stadium, collect(t.year) AS final_years
ORDER BY size(collect(t.year)) DESC
```

### 80. Path from a losing team back to the champion via shared opponents

```cypher
-- untyped variable-length path (no relationship-type alternation in this engine)
MATCH path = shortestPath(
  (loser:Team {code: "ARG"})-[*..6]-(champion:Team {code: "GER"})
)
RETURN [n IN nodes(path) | coalesce(n.name, n.match_id)] AS chain
```

---

## Level 5: Network Intelligence (impossible in SQL)

*Multi-hop, weighted, and structural graph queries with no reasonable SQL equivalent.*

> This engine exposes real graph algorithms (PageRank, shortest-path BFS, weakly-connected-components
> community detection) as Python SDK methods (`client.page_rank()`, `client.bfs()`, `client.wcc()`) and
> as MCP tools (`pagerank`, `shortest_path`, `communities`) — **not** as inline Cypher `CALL algo.*` or
> `CALL vector.search(...)` procedures, which don't exist here. The queries below are valid Cypher that
> capture the same analytical intent using aggregation and multi-hop traversal; where a query is standing
> in for a real algorithm, that's called out explicitly.

### 81. Multi-signal player influence score (PageRank stand-in)

```cypher
-- true PageRank: the `pagerank` MCP tool, or client.page_rank(label="Player", edge_type="SCORED_BY")
MATCH (p:Player)
OPTIONAL MATCH (p)<-[:SCORED_BY]-(g:Goal) WHERE g.own_goal = false
OPTIONAL MATCH (p)<-[:BOOKED]-(b:Booking)
OPTIONAL MATCH (p)<-[:INVOLVES]-(s:Substitution)
OPTIONAL MATCH (p)<-[:TAKEN_BY]-(pk:PenaltyKick)
RETURN p.name AS player,
       count(DISTINCT g) * 3 + count(DISTINCT b) + count(DISTINCT s) + count(DISTINCT pk) AS influence_score
ORDER BY influence_score DESC LIMIT 20
```

### 82. Intra-confederation match density (community stand-in)

```cypher
-- true community detection: the `communities` MCP tool, or client.wcc(label="Team", edge_type="HOME_TEAM")
MATCH (m:Match)-[:HOME_TEAM]->(t1:Team), (m)-[:AWAY_TEAM]->(t2:Team)
WHERE t1.confederation = t2.confederation
RETURN t1.confederation AS community, count(m) AS intra_confederation_matches
ORDER BY intra_confederation_matches DESC
```

### 83. Stadiums by distinct-team traffic (betweenness stand-in)

```cypher
-- there is no betweenness-centrality MCP tool or SDK method; this approximates
-- "bridge" venues by how many distinct teams have played there
MATCH (s:Stadium)<-[:PLAYED_AT]-(m:Match)-[:HOME_TEAM]->(t1:Team), (m)-[:AWAY_TEAM]->(t2:Team)
RETURN s.name AS stadium, count(DISTINCT t1) + count(DISTINCT t2) AS distinct_team_traffic
ORDER BY distinct_team_traffic DESC LIMIT 15
```

### 84. Shortest path between two arbitrary players through any shared structure

```cypher
-- untyped variable-length path (no relationship-type alternation in this engine)
MATCH path = shortestPath(
  (p1:Player)-[*..8]-(p2:Player)
)
WHERE p1.player_id = "P-07458" AND p2.player_id = "P-62722"
RETURN length(path) AS hops, path
```

### 85. Champion succession network: which teams beat the previous champion

```cypher
MATCH (t1:Tournament)-[:WON_BY]->(prev:Team), (t2:Tournament)-[:WON_BY]->(next:Team)
WHERE t2.year > t1.year
MATCH (m:Match)-[:IN_TOURNAMENT]->(t2), (m)-[:HOME_TEAM]->(prev), (m)-[:AWAY_TEAM]->(next)
RETURN prev.name AS previous_champion, next.name AS defeated_them_in, t2.name AS tournament
UNION
MATCH (t1:Tournament)-[:WON_BY]->(prev:Team), (t2:Tournament)-[:WON_BY]->(next:Team)
WHERE t2.year > t1.year
MATCH (m:Match)-[:IN_TOURNAMENT]->(t2), (m)-[:AWAY_TEAM]->(prev), (m)-[:HOME_TEAM]->(next)
RETURN prev.name AS previous_champion, next.name AS defeated_them_in, t2.name AS tournament
```

### 86. Goal-scoring influence graph weighted by tournament stage

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player), (g)-[:SCORED_IN]->(m:Match)
WITH p, CASE WHEN m.stage = "final" THEN 5 WHEN m.stage CONTAINS "semi-final" THEN 3 ELSE 1 END AS weight
RETURN p.name AS player, sum(weight) AS impact_score
ORDER BY impact_score DESC LIMIT 20
```

### 87. Team clustering by shared player pool across tournaments (talent pipelines)

```cypher
MATCH (p:Player)-[:PLAYED_FOR]->(t1:Team), (p)-[:PLAYED_FOR]->(t2:Team)
WHERE t1 <> t2
RETURN t1.name AS team1, t2.name AS team2, count(DISTINCT p) AS shared_players
ORDER BY shared_players DESC LIMIT 20
```

### 88. Referees per confederation (community stand-in)

```cypher
-- true community detection: the `communities` MCP tool, or client.wcc(label="Referee", edge_type="FROM")
MATCH (r:Referee)
RETURN r.confederation AS community, count(r) AS referees
ORDER BY referees DESC LIMIT 10
```

### 89. Weighted confederation rivalry strength

```cypher
MATCH (m:Match)-[:HOME_TEAM]->(t1:Team), (m)-[:AWAY_TEAM]->(t2:Team)
WHERE t1.confederation <> t2.confederation AND m.home_score IS NOT NULL
WITH t1.confederation AS c1, t2.confederation AS c2, count(m) AS matches, sum(m.home_score + m.away_score) AS goals
RETURN c1, c2, matches, goals, round(toFloat(goals) / matches * 100) / 100 AS goals_per_match
ORDER BY goals_per_match DESC
```

### 90. Stadiums by confederation reach (betweenness stand-in)

```cypher
MATCH (s:Stadium)<-[:PLAYED_AT]-(m:Match)-[:HOME_TEAM]->(t1:Team), (m)-[:AWAY_TEAM]->(t2:Team)
RETURN s.name AS stadium, count(DISTINCT t1.confederation) + count(DISTINCT t2.confederation) AS confederation_reach
ORDER BY confederation_reach DESC LIMIT 15
```

### 91. Multi-tournament veterans ranked by scoring output (PageRank stand-in)

```cypher
-- true PageRank: the `pagerank` MCP tool, filtered client-side to count_tournaments >= 2
MATCH (p:Player)
WHERE p.count_tournaments >= 2
OPTIONAL MATCH (p)<-[:SCORED_BY]-(g:Goal) WHERE g.own_goal = false
RETURN p.name AS player, p.count_tournaments AS tournaments, count(g) AS goals
ORDER BY goals DESC, tournaments DESC LIMIT 15
```

### 92. Biggest margins of victory

```cypher
MATCH (m:Match)-[:HOME_TEAM]->(t1:Team), (m)-[:AWAY_TEAM]->(t2:Team)
WHERE m.home_score > m.away_score
RETURN t1.name AS winner, t2.name AS loser, m.home_score - m.away_score AS margin
ORDER BY margin DESC LIMIT 15
```

### 93. Stadium career span: first and last World Cup year hosted

```cypher
MATCH (s:Stadium)<-[:PLAYED_AT]-(m:Match)-[:IN_TOURNAMENT]->(t:Tournament)
WITH s, min(t.year) AS first_year, max(t.year) AS last_year
WHERE last_year > first_year
RETURN s.name AS stadium, first_year, last_year, last_year - first_year AS span_years
ORDER BY span_years DESC LIMIT 15
```

### 94. Shortest path between two confederations through the match network

```cypher
-- untyped variable-length path (no relationship-type alternation in this engine)
MATCH path = shortestPath(
  (t1:Team {confederation: "CONMEBOL"})-[*..6]-(t2:Team {confederation: "AFC"})
)
RETURN length(path) AS hops, [n IN nodes(path) | coalesce(n.name, n.match_id)] AS chain
LIMIT 5
```

### 95. Players with comparable career shapes (vector-similarity stand-in)

```cypher
-- true embedding similarity search: the `search_player` MCP tool's vector backend, not raw Cypher
MATCH (target:Player {player_id: "P-07458"}), (p:Player)
WHERE p <> target AND p.position = target.position
  AND abs(p.count_tournaments - target.count_tournaments) <= 1
RETURN p.name AS player, p.position AS position, p.count_tournaments AS tournaments
ORDER BY abs(p.count_tournaments - target.count_tournaments) LIMIT 10
```

### 96. Full network snapshot: degree distribution across all node types

```cypher
MATCH (n)
RETURN labels(n)[0] AS label, count(n) AS nodes
ORDER BY nodes DESC
```

### 97. Team power ranking blending appearance volume and title count (PageRank stand-in)

```cypher
-- true PageRank: the `pagerank` MCP tool, or client.page_rank(label="Team", edge_type="HOME_TEAM")
MATCH (t:Team)
OPTIONAL MATCH (t)<-[:HOME_TEAM]-(hm:Match)
OPTIONAL MATCH (t)<-[:AWAY_TEAM]-(am:Match)
OPTIONAL MATCH (wt:Tournament)-[:WON_BY]->(t)
RETURN t.name AS team, count(DISTINCT hm) + count(DISTINCT am) AS matches_played, count(DISTINCT wt) AS titles
ORDER BY matches_played DESC, titles DESC LIMIT 20
```

### 98. Host-nation title rate

```cypher
MATCH (t:Tournament)-[:HOSTED_BY]->(hc:Country), (t)-[:WON_BY]->(champ:Team)
RETURN count(CASE WHEN hc.name = champ.name THEN 1 END) AS home_wins, count(*) AS total_tournaments,
       round(toFloat(count(CASE WHEN hc.name = champ.name THEN 1 END)) / count(*) * 100) AS home_win_pct
```

### 99. End-to-end lineage: goal -> scorer -> host-nation team -> hosted tournament -> champion

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player)-[:PLAYED_FOR]->(team:Team),
      (t:Tournament)-[:HOSTED_BY]->(c:Country), (t)-[:WON_BY]->(champ:Team)
WHERE g.own_goal = false AND team.name = c.name
RETURN p.name AS scorer, team.name AS team, c.name AS country,
       t.name AS hosted_tournament, champ.name AS champion
LIMIT 20
```

### 100. The whole graph, one traversal: every goal's full context

```cypher
MATCH (g:Goal)-[:SCORED_BY]->(p:Player), (g)-[:SCORED_IN]->(m:Match)-[:PLAYED_AT]->(s:Stadium),
      (m)-[:IN_TOURNAMENT]->(t:Tournament), (p)-[:PLAYED_FOR]->(team:Team)
WHERE g.own_goal = false
RETURN p.name AS scorer, team.name AS team, m.name AS match,
       s.name AS stadium, t.name AS tournament, g.minute AS minute
ORDER BY t.year DESC, g.minute
LIMIT 25
```
