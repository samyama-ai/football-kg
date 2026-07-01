"""Tests for the football ETL loader against embedded Samyama.

Fixture columns mirror the real DataHub-style World Cup export headers
(team_name/team_code/host_country/etc, not the simplified names used in
earlier drafts of this loader).
"""

import os
import tempfile

import pytest
from samyama import SamyamaClient

from etl.loader import load_football

TEAMS = "\n".join([
    "key_id,team_id,team_name,team_code,mens_team,womens_team,federation_name,region_name,"
    "confederation_id,confederation_name,confederation_code,mens_team_wikipedia_link,"
    "womens_team_wikipedia_link,federation_wikipedia_link",
    "1,T-30,Brazil,BRA,1,0,CBF,South America,CF-3,CONMEBOL,CONMEBOL,x,not applicable,x",
    "2,T-31,Germany,DEU,1,1,DFB,Europe,CF-6,UEFA,UEFA,x,x,x",
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
]) + "\n"

# One normal player, one mononym player (given_name = 'not applicable', as with
# real Brazilian players like Ronaldinho) — exercises the null-safe name fix.
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
]) + "\n"

MANAGERS = "\n".join([
    "key_id,manager_id,family_name,given_name,female,country_name,manager_wikipedia_link",
    "1,M-001,Loew,Joachim,0,Germany,x",
]) + "\n"

REFEREES = "\n".join([
    "key_id,referee_id,family_name,given_name,female,country_name,confederation_id,"
    "confederation_name,confederation_code,referee_wikipedia_link",
    "1,R-001,Rizzoli,Nicola,0,Italy,CF-6,UEFA,UEFA,x",
]) + "\n"

BOOKINGS = "\n".join([
    "key_id,booking_id,tournament_id,tournament_name,match_id,match_name,match_date,"
    "stage_name,group_name,team_id,team_name,team_code,home_team,away_team,player_id,"
    "family_name,given_name,shirt_number,minute_label,minute_regulation,minute_stoppage,"
    "match_period,yellow_card,red_card,second_yellow_card,sending_off",
    "1,B-001,WC-2014,2014 FIFA World Cup,M-2014-62,Brazil vs Germany,2014-07-08,semi-finals,"
    "not applicable,T-30,Brazil,BRA,0,1,P-002,Ronaldinho,not applicable,10,10',10,0,"
    "first half,1,0,0,0",
]) + "\n"

SUBSTITUTIONS = "\n".join([
    "key_id,substitution_id,tournament_id,tournament_name,match_id,match_name,match_date,"
    "stage_name,group_name,team_id,team_name,team_code,home_team,away_team,player_id,"
    "family_name,given_name,shirt_number,minute_label,minute_regulation,minute_stoppage,"
    "match_period,going_off,coming_on",
    "1,S-001,WC-2014,2014 FIFA World Cup,M-2014-62,Brazil vs Germany,2014-07-08,semi-finals,"
    "not applicable,T-31,Germany,DEU,0,1,P-001,Klose,Miroslav,11,88',88,0,second half,1,0",
]) + "\n"

PENALTY_KICKS = "\n".join([
    "key_id,penalty_kick_id,tournament_id,tournament_name,match_id,match_name,match_date,"
    "stage_name,group_name,team_id,team_name,team_code,home_team,away_team,player_id,"
    "family_name,given_name,shirt_number,converted",
    "1,PK-001,WC-2014,2014 FIFA World Cup,M-2014-62,Brazil vs Germany,2014-07-08,semi-finals,"
    "not applicable,T-31,Germany,DEU,0,1,P-001,Klose,Miroslav,11,1",
]) + "\n"

TOURNAMENT_STANDINGS = "\n".join([
    "key_id,tournament_id,tournament_name,position,team_id,team_name,team_code",
    "1,WC-2014,2014 FIFA World Cup,1,T-31,Germany,DEU",
    "2,WC-2014,2014 FIFA World Cup,4,T-30,Brazil,BRA",
]) + "\n"

GROUP_STANDINGS = "\n".join([
    "key_id,tournament_id,tournament_name,stage_number,stage_name,group_name,position,"
    "team_id,team_name,team_code,played,wins,draws,losses,goals_for,goals_against,"
    "goal_difference,points,advanced",
    "1,WC-2014,2014 FIFA World Cup,1,group stage,Group A,1,T-30,Brazil,BRA,3,2,1,0,7,2,5,7,1",
    "2,WC-2014,2014 FIFA World Cup,1,group stage,Group G,1,T-31,Germany,DEU,3,2,1,0,7,1,6,7,1",
]) + "\n"


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


@pytest.fixture(scope="module")
def loaded_graph():
    """Load the synthetic fixture dataset into an embedded graph."""
    c = SamyamaClient.embedded()
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(os.path.join(tmpdir, "teams.csv"), TEAMS)
        _write(os.path.join(tmpdir, "stadiums.csv"), STADIUMS)
        _write(os.path.join(tmpdir, "tournaments.csv"), TOURNAMENTS)
        _write(os.path.join(tmpdir, "matches.csv"), MATCHES)
        _write(os.path.join(tmpdir, "players.csv"), PLAYERS)
        _write(os.path.join(tmpdir, "squads.csv"), SQUADS)
        _write(os.path.join(tmpdir, "goals.csv"), GOALS)
        _write(os.path.join(tmpdir, "managers.csv"), MANAGERS)
        _write(os.path.join(tmpdir, "referees.csv"), REFEREES)
        _write(os.path.join(tmpdir, "bookings.csv"), BOOKINGS)
        _write(os.path.join(tmpdir, "substitutions.csv"), SUBSTITUTIONS)
        _write(os.path.join(tmpdir, "penalty_kicks.csv"), PENALTY_KICKS)
        _write(os.path.join(tmpdir, "tournament_standings.csv"), TOURNAMENT_STANDINGS)
        _write(os.path.join(tmpdir, "group_standings.csv"), GROUP_STANDINGS)
        stats = load_football(c, data_dir=tmpdir)
    return c, stats


def _q(client, cypher):
    r = client.query_readonly(cypher, "default")
    return [dict(zip(r.columns, row)) for row in r.records]


class TestTeams:
    def test_teams_created(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["teams"] == 2
        rows = _q(c, "MATCH (t:Team) RETURN t.name ORDER BY t.name")
        names = [r["t.name"] for r in rows]
        assert "Brazil" in names
        assert "Germany" in names

    def test_team_confederation(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, 'MATCH (t:Team {code: "DEU"}) RETURN t.confederation, t.womens_team')
        assert rows[0]["t.confederation"] == "UEFA"
        assert rows[0]["t.womens_team"] is True


class TestStadium:
    def test_stadium_created(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["stadiums"] == 1
        rows = _q(c, "MATCH (s:Stadium) RETURN s.name, s.city, s.capacity")
        assert rows[0]["s.name"] == "Maracana"
        assert rows[0]["s.capacity"] == 78838


class TestTournament:
    def test_tournament_created(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["tournaments"] == 1
        rows = _q(c, "MATCH (t:Tournament) RETURN t.name, t.year, t.winner")
        assert rows[0]["t.year"] == 2014
        assert rows[0]["t.winner"] == "Germany"

    def test_hosted_by_edge(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (t:Tournament)-[:HOSTED_BY]->(c:Country) RETURN c.name")
        assert rows[0]["c.name"] == "Brazil"

    def test_won_by_edge(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (t:Tournament)-[:WON_BY]->(team:Team) RETURN team.name")
        assert rows[0]["team.name"] == "Germany"


class TestMatch:
    def test_match_created(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["matches"] == 1
        rows = _q(c, "MATCH (m:Match) RETURN m.stage, m.home_score, m.away_score, m.result")
        m = rows[0]
        assert m["m.stage"] == "semi-finals"
        assert m["m.home_score"] == 1
        assert m["m.away_score"] == 7

    def test_home_away_team_edges(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (m:Match)-[:HOME_TEAM]->(t:Team) RETURN t.name")
        assert rows[0]["t.name"] == "Brazil"
        rows = _q(c, "MATCH (m:Match)-[:AWAY_TEAM]->(t:Team) RETURN t.name")
        assert rows[0]["t.name"] == "Germany"

    def test_played_at_edge(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (m:Match)-[:PLAYED_AT]->(s:Stadium) RETURN s.name")
        assert rows[0]["s.name"] == "Maracana"

    def test_in_tournament_edge(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (m:Match)-[:IN_TOURNAMENT]->(t:Tournament) RETURN t.name")
        assert rows[0]["t.name"] == "2014 FIFA World Cup"


class TestPlayers:
    def test_players_created(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["players"] == 2

    def test_count_tournaments_from_source(self, loaded_graph):
        """count_tournaments comes straight from the source dataset, not computed here."""
        c, _ = loaded_graph
        rows = _q(c, 'MATCH (p:Player {player_id: "P-001"}) RETURN p.count_tournaments, p.name')
        assert rows[0]["p.count_tournaments"] == 4
        assert rows[0]["p.name"] == "Miroslav Klose"

    def test_mononym_player_name(self, loaded_graph):
        """A player with given_name = 'not applicable' (real-world mononyms like
        Ronaldinho) must get a null-safe display name, not crash concatenation.
        given_name is stored as '' rather than NULL — the engine also errors on
        CONTAINS against a NULL property, which would break search_player."""
        c, _ = loaded_graph
        rows = _q(c, 'MATCH (p:Player {player_id: "P-002"}) RETURN p.name, p.given_name, p.family_name')
        assert rows[0]["p.name"] == "Ronaldinho"
        assert rows[0]["p.given_name"] == ""
        assert rows[0]["p.family_name"] == "Ronaldinho"

    def test_concat_query_does_not_crash(self, loaded_graph):
        """Regression test: concatenating given_name + family_name directly in Cypher
        errors out when given_name is NULL — this is why loader precomputes p.name."""
        c, _ = loaded_graph
        rows = _q(c, "MATCH (p:Player) RETURN p.name AS n ORDER BY n")
        assert len(rows) == 2

    def test_played_for_edges_with_props(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, """
            MATCH (p:Player)-[pf:PLAYED_FOR]->(t:Team {name: "Germany"})
            RETURN p.name, pf.tournament_id, pf.shirt_number, pf.position
        """)
        assert rows[0]["p.name"] == "Miroslav Klose"
        assert rows[0]["pf.tournament_id"] == "WC-2014"
        assert rows[0]["pf.shirt_number"] == 11
        assert rows[0]["pf.position"] == "forward"


class TestManagers:
    def test_managers_created(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["managers"] == 1

    def test_manager_from_country(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (mgr:Manager)-[:FROM]->(c:Country) RETURN mgr.name, c.name")
        assert rows[0]["mgr.name"] == "Joachim Loew"
        assert rows[0]["c.name"] == "Germany"


class TestReferees:
    def test_referees_created(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["referees"] == 1

    def test_referee_from_country(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (r:Referee)-[:FROM]->(c:Country) RETURN r.name, c.name")
        assert rows[0]["r.name"] == "Nicola Rizzoli"
        assert rows[0]["c.name"] == "Italy"


class TestGoals:
    def test_goals_created(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["goals"] == 2

    def test_scored_by_and_in(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, """
            MATCH (g:Goal)-[:SCORED_BY]->(p:Player), (g)-[:SCORED_IN]->(m:Match)
            RETURN p.name AS scorer, g.minute AS minute
            ORDER BY g.minute
        """)
        assert len(rows) == 2
        assert rows[0]["scorer"] == "Miroslav Klose"
        assert rows[0]["minute"] == 23
        assert rows[1]["scorer"] == "Ronaldinho"
        assert rows[1]["minute"] == 90

    def test_for_team_edge(self, loaded_graph):
        c, _ = loaded_graph
        rows = _q(c, "MATCH (g:Goal)-[:FOR_TEAM]->(t:Team) RETURN t.name ORDER BY t.name")
        names = [r["t.name"] for r in rows]
        assert names == ["Brazil", "Germany"]


class TestMatchEvents:
    def test_bookings(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["bookings"] == 1
        rows = _q(c, "MATCH (b:Booking)-[:BOOKED]->(p:Player) RETURN p.name, b.yellow_card")
        assert rows[0]["p.name"] == "Ronaldinho"
        assert rows[0]["b.yellow_card"] is True

    def test_substitutions(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["substitutions"] == 1
        rows = _q(c, "MATCH (s:Substitution)-[:INVOLVES]->(p:Player) RETURN p.name, s.going_off")
        assert rows[0]["p.name"] == "Miroslav Klose"
        assert rows[0]["s.going_off"] is True

    def test_penalty_kicks(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["penalty_kicks"] == 1
        rows = _q(c, "MATCH (pk:PenaltyKick)-[:TAKEN_BY]->(p:Player) RETURN p.name, pk.converted")
        assert rows[0]["p.name"] == "Miroslav Klose"
        assert rows[0]["pk.converted"] is True


class TestStandings:
    def test_tournament_standings(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["tournament_standings"] == 2
        rows = _q(c, """
            MATCH (t:Team)-[f:FINISHED]->(:Tournament)
            RETURN t.name AS team, f.position AS position ORDER BY f.position
        """)
        assert rows[0]["team"] == "Germany"
        assert rows[0]["position"] == 1

    def test_group_standings(self, loaded_graph):
        c, stats = loaded_graph
        assert stats["group_standings"] == 2
        rows = _q(c, """
            MATCH (t:Team {name: "Brazil"})-[g:IN_GROUP]->(:Tournament)
            RETURN g.group_name AS group_name, g.points AS points, g.advanced AS advanced
        """)
        assert rows[0]["group_name"] == "Group A"
        assert rows[0]["points"] == 7
        assert rows[0]["advanced"] is True


class TestMultiHopQueries:
    def test_scorers_by_team(self, loaded_graph):
        """Multi-hop: goal scorers who played for Germany."""
        c, _ = loaded_graph
        rows = _q(c, """
            MATCH (g:Goal)-[:SCORED_BY]->(p:Player)-[:PLAYED_FOR]->(t:Team {name: "Germany"})
            RETURN p.name AS scorer
        """)
        assert len(rows) == 1
        assert rows[0]["scorer"] == "Miroslav Klose"

    def test_tournament_winner_hosted_by(self, loaded_graph):
        """Multi-hop: was the tournament winner also the host?"""
        c, _ = loaded_graph
        rows = _q(c, """
            MATCH (t:Tournament)-[:WON_BY]->(winner:Team), (t)-[:HOSTED_BY]->(host:Country)
            RETURN winner.name AS winner, host.name AS host
        """)
        assert rows[0]["winner"] == "Germany"
        assert rows[0]["host"] == "Brazil"
