"""Run all README showcase queries against a loaded football-kg graph."""

import sys
sys.path.insert(0, ".")
from samyama import SamyamaClient
from etl.loader import load_football

GRAPH = "default"


def q(client, cypher):
    r = client.query_readonly(cypher, GRAPH)
    return [dict(zip(r.columns, row)) for row in r.records]


def run_all(client):
    print("=" * 70)
    print("FOOTBALL-KG FULL DATASET QUERIES")
    print("=" * 70)

    # Graph stats
    print("\n## Graph Statistics\n")
    for label in ["Player", "Manager", "Referee", "Goal", "Booking", "Substitution", "PenaltyKick",
                  "Stadium", "Team", "Match", "Country", "Tournament"]:
        rows = q(client, f"MATCH (n:{label}) RETURN count(n) AS c")
        print(f"  {label:15s} {rows[0]['c']:>8,}")

    total_nodes = q(client, "MATCH (n) RETURN count(n) AS c")[0]["c"]
    total_edges = q(client, "MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
    print(f"\n  {'Total nodes':15s} {total_nodes:>8,}")
    print(f"  {'Total edges':15s} {total_edges:>8,}")

    # Top goal scorers
    print("\n## Top Goal Scorers of All Time\n")
    rows = q(client, """
        MATCH (g:Goal)-[:SCORED_BY]->(p:Player)
        WHERE g.own_goal = false
        RETURN p.name AS player, count(g) AS goals
        ORDER BY goals DESC LIMIT 10
    """)
    print(f"  {'Player':25s} {'Goals':>6s}")
    for r in rows:
        print(f"  {str(r['player']):25s} {r['goals']:>6,}")

    # Top tournament winners
    print("\n## Top World Cup Winners\n")
    rows = q(client, """
        MATCH (t:Tournament)-[:WON_BY]->(team:Team)
        RETURN team.name AS team, count(t) AS titles
        ORDER BY titles DESC LIMIT 10
    """)
    print(f"  {'Team':25s} {'Titles':>6s}")
    for r in rows:
        print(f"  {str(r['team']):25s} {r['titles']:>6,}")

    # Highest scoring matches
    print("\n## Highest Scoring Matches\n")
    rows = q(client, """
        MATCH (m:Match)
        WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
        RETURN m.name AS match, m.date AS date,
               m.home_score + m.away_score AS total_goals, m.stage AS stage
        ORDER BY total_goals DESC LIMIT 10
    """)
    print(f"  {'Match':30s} {'Date':12s} {'Goals':>6s} {'Stage':20s}")
    for r in rows:
        date = str(r.get("date", "") or "")
        stage = str(r.get("stage", "") or "")
        print(f"  {str(r['match']):30s} {date:12s} {r['total_goals']:>6,} {stage:20s}")

    # Multi-hop: multi-tournament veterans
    print("\n## Multi-Tournament Veterans (3+ tournaments)\n")
    rows = q(client, """
        MATCH (p:Player)
        WHERE p.count_tournaments >= 3
        RETURN p.name AS player, p.count_tournaments AS tournaments
        ORDER BY tournaments DESC LIMIT 10
    """)
    print(f"  {'Player':25s} {'Tournaments':>11s}")
    for r in rows:
        print(f"  {str(r['player']):25s} {r['tournaments']:>11,}")

    # Busiest stadiums
    print("\n## Busiest Stadiums\n")
    rows = q(client, """
        MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium)
        RETURN s.name AS stadium, s.city AS city, count(m) AS matches
        ORDER BY matches DESC LIMIT 10
    """)
    print(f"  {'Stadium':30s} {'City':20s} {'Matches':>8s}")
    for r in rows:
        city = str(r.get("city", "") or "")
        print(f"  {str(r['stadium']):30s} {city:20s} {r['matches']:>8,}")

    # Goals by stage
    print("\n## Goals by Match Stage\n")
    rows = q(client, """
        MATCH (g:Goal)-[:SCORED_IN]->(m:Match)
        WHERE g.own_goal = false
        RETURN m.stage AS stage, count(g) AS goals
        ORDER BY goals DESC
    """)
    print(f"  {'Stage':25s} {'Goals':>6s}")
    for r in rows:
        print(f"  {str(r['stage']):25s} {r['goals']:>6,}")

    # Multi-hop: player nationality via team
    print("\n## Multi-hop: Goal Scorers by Team Confederation\n")
    rows = q(client, """
        MATCH (g:Goal)-[:SCORED_BY]->(p:Player)-[:PLAYED_FOR]->(team:Team)
        WHERE g.own_goal = false
        RETURN team.confederation AS confederation, count(g) AS goals
        ORDER BY goals DESC LIMIT 10
    """)
    print(f"  {'Confederation':20s} {'Goals':>6s}")
    for r in rows:
        conf = str(r.get("confederation", "") or "")
        print(f"  {conf:20s} {r['goals']:>6,}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None

    if data_dir:
        print(f"Loading data from {data_dir}...")
        c = SamyamaClient.embedded()
        stats = load_football(c, data_dir=data_dir)
        print(f"\nLoad complete: {stats}")
        run_all(c)
    else:
        print("Usage: python scripts/run_queries.py <data-dir>")
        print("  or import and call run_all(client) with a pre-loaded client")
