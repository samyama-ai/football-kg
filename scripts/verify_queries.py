"""Verify graph statistics and showcase query results after a full load."""

import sys
import gc
sys.path.insert(0, ".")
from samyama import SamyamaClient
from etl.loader import load_football

GRAPH = "default"


def q(client, cypher):
    r = client.query_readonly(cypher, GRAPH)
    return [dict(zip(r.columns, row)) for row in r.records]


def verify(client):
    print("=" * 60, flush=True)
    print("VERIFYING FOOTBALL-KG NUMBERS", flush=True)
    print("=" * 60, flush=True)

    print("\n--- GRAPH STATS ---", flush=True)
    for label in ["Player", "Manager", "Referee", "Goal", "Booking", "Substitution", "PenaltyKick",
                  "Stadium", "Team", "Match", "Country", "Tournament"]:
        rows = q(client, f"MATCH (n:{label}) RETURN count(n) AS c")
        print(f"  {label}: {rows[0]['c']:,}", flush=True)
    gc.collect()

    total_edges = q(client, "MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
    print(f"  Total edges: {total_edges:,}", flush=True)
    gc.collect()

    print("\n--- TOP GOAL SCORERS ---", flush=True)
    rows = q(client, """
        MATCH (g:Goal)-[:SCORED_BY]->(p:Player)
        WHERE g.own_goal = false
        RETURN p.name AS player, count(g) AS goals
        ORDER BY goals DESC LIMIT 5
    """)
    for r in rows:
        print(f"  {r['player']}: {r['goals']} goals", flush=True)
    gc.collect()

    print("\n--- TOURNAMENT WINNERS ---", flush=True)
    rows = q(client, """
        MATCH (t:Tournament)-[:WON_BY]->(team:Team)
        RETURN team.name AS team, count(t) AS titles
        ORDER BY titles DESC LIMIT 5
    """)
    for r in rows:
        print(f"  {r['team']}: {r['titles']} titles", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("VERIFICATION COMPLETE", flush=True)


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    print(f"Loading data from {data_dir}...", flush=True)
    c = SamyamaClient.embedded()
    stats = load_football(c, data_dir=data_dir)
    print(f"\nLoad complete: {stats}", flush=True)
    verify(c)
