"""Tests for football-kg MCP server — verifies auto-generated + custom tools.

Fixtures use the real DataHub-style World Cup column names (see test_loader.py).
"""

import asyncio
import json
import os
import sys
import tempfile

import pytest

from samyama import SamyamaClient
from samyama_mcp.config import ToolConfig
from samyama_mcp.server import SamyamaMCPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from etl.loader import load_football

TEAMS = "\n".join([
    "key_id,team_id,team_name,team_code,mens_team,womens_team,federation_name,region_name,"
    "confederation_id,confederation_name,confederation_code,mens_team_wikipedia_link,"
    "womens_team_wikipedia_link,federation_wikipedia_link",
    "1,T-30,Brazil,BRA,1,0,CBF,South America,CF-3,CONMEBOL,CONMEBOL,x,not applicable,x",
    "2,T-31,Germany,DEU,1,1,DFB,Europe,CF-6,UEFA,UEFA,x,x,x",
    "3,T-03,Argentina,ARG,1,0,AFA,South America,CF-3,CONMEBOL,CONMEBOL,x,not applicable,x",
]) + "\n"

STADIUMS = "\n".join([
    "key_id,stadium_id,stadium_name,city_name,country_name,stadium_capacity,"
    "stadium_wikipedia_link,city_wikipedia_link",
    "1,S-001,Maracana,Rio de Janeiro,Brazil,78838,x,x",
]) + "\n"

TOURNAMENTS = "\n".join([
    "key_id,tournament_id,tournament_name,year,start_date,end_date,host_country,winner,host_won,"
    "count_teams,group_stage,second_group_stage,final_round,round_of_16,quarter_finals,"
    "semi_finals,third_place_match,final",
    "1,WC-2014,2014 FIFA World Cup,2014,2014-06-12,2014-07-13,Brazil,Germany,0,32,"
    "1,0,0,1,1,1,1,1",
]) + "\n"

MATCHES = "\n".join([
    "key_id,tournament_id,tournament_name,match_id,match_name,stage_name,group_name,"
    "group_stage,knockout_stage,replayed,replay,match_date,match_time,stadium_id,stadium_name,"
    "city_name,country_name,home_team_id,home_team_name,home_team_code,away_team_id,"
    "away_team_name,away_team_code,score,home_team_score,away_team_score,"
    "home_team_score_margin,away_team_score_margin,extra_time,penalty_shootout,"
    "score_penalties,home_team_score_penalties,away_team_score_penalties,result,"
    "home_team_win,away_team_win,draw",
    "1,WC-2014,2014 FIFA World Cup,M-2014-62,Brazil vs Germany,semi-finals,not applicable,"
    "0,1,0,0,2014-07-08,17:00,S-001,Maracana,Rio de Janeiro,Brazil,T-30,Brazil,BRA,T-31,"
    "Germany,DEU,1-7,1,7,-6,6,0,0,0-0,0,0,away team win,0,1,0",
    "2,WC-2014,2014 FIFA World Cup,M-2014-64,Germany vs Argentina,final,not applicable,"
    "0,1,0,0,2014-07-13,16:00,S-001,Maracana,Rio de Janeiro,Brazil,T-31,Germany,DEU,T-03,"
    "Argentina,ARG,1-0,1,0,1,-1,1,0,0-0,0,0,home team win,1,0,0",
]) + "\n"

PLAYERS = "\n".join([
    "key_id,player_id,family_name,given_name,birth_date,female,goal_keeper,defender,"
    "midfielder,forward,count_tournaments,list_tournaments,player_wikipedia_link",
    "1,P-001,Klose,Miroslav,1978-06-09,0,0,0,0,1,4,\"2002, 2006, 2010, 2014\",x",
    "2,P-002,Ronaldinho,not applicable,1980-03-21,0,0,0,1,0,2,\"2002, 2006\",x",
]) + "\n"

SQUADS = "\n".join([
    "key_id,tournament_id,tournament_name,team_id,team_name,team_code,player_id,"
    "family_name,given_name,shirt_number,position_name,position_code",
    "1,WC-2014,2014 FIFA World Cup,T-31,Germany,DEU,P-001,Klose,Miroslav,11,forward,FWD",
    "2,WC-2014,2014 FIFA World Cup,T-30,Brazil,BRA,P-002,Ronaldinho,not applicable,10,midfielder,MID",
]) + "\n"

GOALS = "\n".join([
    "key_id,goal_id,tournament_id,tournament_name,match_id,match_name,match_date,stage_name,"
    "group_name,team_id,team_name,team_code,home_team,away_team,player_id,family_name,"
    "given_name,shirt_number,player_team_id,player_team_name,player_team_code,minute_label,"
    "minute_regulation,minute_stoppage,match_period,own_goal,penalty",
    "1,G-001,WC-2014,2014 FIFA World Cup,M-2014-62,Brazil vs Germany,2014-07-08,semi-finals,"
    "not applicable,T-31,Germany,DEU,0,1,P-001,Klose,Miroslav,11,T-31,Germany,DEU,23',23,0,"
    "first half,0,0",
    "2,G-002,WC-2014,2014 FIFA World Cup,M-2014-62,Brazil vs Germany,2014-07-08,semi-finals,"
    "not applicable,T-30,Brazil,BRA,0,1,P-002,Ronaldinho,not applicable,10,T-30,Brazil,BRA,"
    "90',90,0,second half,0,0",
    "3,G-003,WC-2014,2014 FIFA World Cup,M-2014-64,Germany vs Argentina,2014-07-13,final,"
    "not applicable,T-31,Germany,DEU,1,0,P-001,Klose,Miroslav,11,T-31,Germany,DEU,113',113,0,"
    "extra time,0,0",
]) + "\n"

MANAGERS = "\n".join([
    "key_id,manager_id,family_name,given_name,female,country_name,manager_wikipedia_link",
    "1,M-001,Loew,Joachim,0,Germany,x",
]) + "\n"


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def server():
    """Create a server with the synthetic fixture dataset — shared across all tests."""
    client = SamyamaClient.embedded()
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(os.path.join(tmpdir, "teams.csv"), TEAMS)
        _write(os.path.join(tmpdir, "stadiums.csv"), STADIUMS)
        _write(os.path.join(tmpdir, "tournaments.csv"), TOURNAMENTS)
        _write(os.path.join(tmpdir, "matches.csv"), MATCHES)
        _write(os.path.join(tmpdir, "players.csv"), PLAYERS)
        _write(os.path.join(tmpdir, "squads.csv"), SQUADS)
        _write(os.path.join(tmpdir, "goals.csv"), GOALS)
        _write(os.path.join(tmpdir, "managers.csv"), MANAGERS)
        load_football(client, data_dir=tmpdir)

    config_path = os.path.join(
        os.path.dirname(__file__), "..", "mcp_server", "config.yaml"
    )
    config = ToolConfig.from_yaml(config_path)
    return SamyamaMCPServer(client, server_name="Football KG Test", config=config)


def _call(server, tool_name, args=None):
    """Synchronously call an MCP tool and parse the JSON result."""
    async def _run():
        r = await server.mcp.call_tool(tool_name, args or {})
        return json.loads(r.content[0].text)
    return asyncio.run(_run())


# ── Tool Registration ────────────────────────────────────────────────

class TestToolRegistration:
    def test_has_generic_tools(self, server):
        tools = server.list_tools()
        assert "cypher_query" in tools
        assert "schema_info" in tools

    def test_has_node_tools(self, server):
        tools = server.list_tools()
        assert "search_player" in tools
        assert "count_match" in tools
        assert "get_team_by_name" in tools

    def test_has_edge_tools(self, server):
        tools = server.list_tools()
        assert "find_scored_by_connections" in tools
        assert "find_won_by_connections" in tools
        assert "traverse_played_for" in tools

    def test_has_algorithm_tools(self, server):
        tools = server.list_tools()
        assert "pagerank" in tools
        assert "shortest_path" in tools
        assert "communities" in tools

    def test_has_custom_tools(self, server):
        tools = server.list_tools()
        assert "top_goal_scorers" in tools
        assert "top_tournament_winners" in tools
        assert "highest_scoring_matches" in tools
        assert "busiest_stadiums" in tools
        assert "head_to_head" in tools
        assert "managers_by_country" in tools
        assert "squad_roster" in tools
        assert "group_stage_table" in tools

    def test_tool_count_at_least_50(self, server):
        assert len(server.list_tools()) >= 50


# ── Schema Info ──────────────────────────────────────────────────────

class TestSchemaInfo:
    def test_schema_has_all_labels(self, server):
        schema = _call(server, "schema_info")
        labels = {nt["label"] for nt in schema["node_types"]}
        assert {"Player", "Manager", "Goal", "Stadium", "Team", "Match", "Country", "Tournament"} <= labels

    def test_schema_has_edge_types(self, server):
        schema = _call(server, "schema_info")
        etypes = {et["type"] for et in schema["edge_types"]}
        assert "SCORED_IN" in etypes
        assert "SCORED_BY" in etypes
        assert "WON_BY" in etypes
        assert "PLAYED_FOR" in etypes

    def test_schema_totals_positive(self, server):
        schema = _call(server, "schema_info")
        assert schema["total_nodes"] > 0
        assert schema["total_edges"] > 0


# ── Auto-Generated Node Tools ────────────────────────────────────────

class TestNodeTools:
    def test_search_player(self, server):
        rows = _call(server, "search_player", {"query": "Klose", "limit": 5})
        assert any("Klose" in str(r.get("family_name", "")) for r in rows)

    def test_count_match(self, server):
        result = _call(server, "count_match")
        assert result["count"] == 2

    def test_get_team_by_name(self, server):
        result = _call(server, "get_team_by_name", {"value": "Germany"})
        assert result["name"] == "Germany"

    def test_get_team_not_found(self, server):
        result = _call(server, "get_team_by_name", {"value": "Nonexistent FC"})
        assert "error" in result


# ── Auto-Generated Edge Tools ────────────────────────────────────────

class TestEdgeTools:
    def test_find_played_for_connections(self, server):
        rows = _call(server, "find_played_for_connections", {
            "node_label": "Team",
            "node_property": "name",
            "node_value": "Germany",
            "direction": "incoming",
        })
        assert len(rows) > 0

    def test_find_scored_by_connections(self, server):
        rows = _call(server, "find_scored_by_connections", {
            "node_label": "Player",
            "node_property": "family_name",
            "node_value": "Klose",
        })
        assert len(rows) > 0


# ── Custom Tools ─────────────────────────────────────────────────────

class TestCustomTools:
    def test_top_goal_scorers(self, server):
        """Regression coverage: Ronaldinho is a mononym (given_name = 'not
        applicable' in the source data) — the query must not crash on NULL
        concatenation and must return his precomputed display name."""
        rows = _call(server, "top_goal_scorers", {"limit": 5})
        assert len(rows) > 0
        goals = [r["goals"] for r in rows]
        assert goals == sorted(goals, reverse=True)
        assert rows[0]["player"] == "Miroslav Klose"
        assert rows[0]["goals"] == 2
        assert any(r["player"] == "Ronaldinho" for r in rows)

    def test_top_tournament_winners(self, server):
        rows = _call(server, "top_tournament_winners", {"limit": 5})
        assert len(rows) > 0
        assert rows[0]["team"] == "Germany"
        assert rows[0]["titles"] == 1

    def test_highest_scoring_matches(self, server):
        rows = _call(server, "highest_scoring_matches", {"limit": 5})
        assert len(rows) > 0
        assert "total_goals" in rows[0]

    def test_busiest_stadiums(self, server):
        rows = _call(server, "busiest_stadiums", {"limit": 5})
        assert len(rows) > 0
        assert rows[0]["stadium"] == "Maracana"
        assert rows[0]["matches_hosted"] == 2

    def test_teams_by_confederation(self, server):
        rows = _call(server, "teams_by_confederation")
        assert len(rows) > 0
        conf = {r["confederation"] for r in rows}
        assert "CONMEBOL" in conf
        assert "UEFA" in conf

    def test_goals_by_stage(self, server):
        rows = _call(server, "goals_by_stage")
        assert len(rows) > 0
        assert "goals" in rows[0]

    def test_head_to_head(self, server):
        rows = _call(server, "head_to_head", {"team1": "Brazil", "team2": "Germany"})
        assert len(rows) == 1
        assert rows[0]["home"] == "Brazil"
        assert rows[0]["away"] == "Germany"

    def test_managers_by_country(self, server):
        rows = _call(server, "managers_by_country", {"country": "Germany"})
        assert len(rows) == 1
        assert rows[0]["manager"] == "Joachim Loew"

    def test_player_goal_log(self, server):
        rows = _call(server, "player_goal_log", {"player_name": "Klose"})
        assert len(rows) == 2

    def test_player_goal_log_mononym(self, server):
        rows = _call(server, "player_goal_log", {"player_name": "Ronaldinho"})
        assert len(rows) == 1

    def test_squad_roster(self, server):
        rows = _call(server, "squad_roster", {"team_name": "Germany", "tournament_id": "WC-2014"})
        assert len(rows) == 1
        assert rows[0]["player"] == "Miroslav Klose"
        assert rows[0]["shirt_number"] == 11


# ── Security ─────────────────────────────────────────────────────────

class TestSecurity:
    def test_cypher_query_rejects_write(self, server):
        result = _call(server, "cypher_query", {"cypher": "CREATE (n:Test)"})
        assert "error" in result

    def test_cypher_query_readonly_works(self, server):
        rows = _call(server, "cypher_query", {
            "cypher": "MATCH (n:Player) RETURN count(n) AS c"
        })
        assert rows[0]["c"] > 0
