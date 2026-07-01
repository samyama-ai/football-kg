"""
Football Knowledge Graph ETL Loader
====================================
Loads FIFA World Cup data (men's + women's) from the real DataHub-style
World Cup CSV export into a Samyama property graph. Creates Tournament,
Team, Match, Player, Manager, Referee, Goal, Booking, Substitution,
PenaltyKick, Stadium and Country nodes plus relationship edges for
tournament results, squads, match events and standings.

Schema: 12 node labels, 19 edge types.
  Tournament{tournament_id,name,year,start_date,end_date,host_country,winner,host_won,count_teams}
  Team{team_id,name,code,confederation,confederation_code,region,mens_team,womens_team}
  Match{match_id,name,date,time,stage,group_name,home_score,away_score,result,
        extra_time,penalty_shootout,home_score_penalties,away_score_penalties}
  Stadium{stadium_id,name,city,country,capacity}
  Player{player_id,name,family_name,given_name,birth_date,female,position,count_tournaments}
  Manager{manager_id,name,family_name,given_name,female,country}
  Referee{referee_id,name,family_name,given_name,female,country,confederation}
  Goal{goal_id,minute,minute_stoppage,own_goal,penalty,period}
  Booking{booking_id,minute,period,yellow_card,red_card,second_yellow_card,sending_off}
  Substitution{substitution_id,minute,period,going_off,coming_on}
  PenaltyKick{penalty_kick_id,converted}
  Country{name}

  (:Match)-[:IN_TOURNAMENT]->(:Tournament)
  (:Match)-[:HOME_TEAM]->(:Team)
  (:Match)-[:AWAY_TEAM]->(:Team)
  (:Match)-[:PLAYED_AT]->(:Stadium)
  (:Tournament)-[:HOSTED_BY]->(:Country)
  (:Tournament)-[:WON_BY]->(:Team)
  (:Team)-[:FINISHED]->(:Tournament)          {position}
  (:Team)-[:IN_GROUP]->(:Tournament)          {group_name,position,played,wins,draws,losses,
                                                goals_for,goals_against,goal_difference,points,advanced}
  (:Player)-[:PLAYED_FOR]->(:Team)            {tournament_id,position,shirt_number}
  (:Goal)-[:SCORED_IN]->(:Match)
  (:Goal)-[:SCORED_BY]->(:Player)
  (:Goal)-[:FOR_TEAM]->(:Team)
  (:Booking)-[:IN_MATCH]->(:Match)
  (:Booking)-[:BOOKED]->(:Player)
  (:Substitution)-[:IN_MATCH]->(:Match)
  (:Substitution)-[:INVOLVES]->(:Player)
  (:PenaltyKick)-[:IN_MATCH]->(:Match)
  (:PenaltyKick)-[:TAKEN_BY]->(:Player)
  (:Manager)-[:FROM]->(:Country)
  (:Referee)-[:FROM]->(:Country)

Required files in --data-dir (plain .csv):
  tournaments.csv   teams.csv    stadiums.csv   matches.csv
  players.csv       squads.csv   goals.csv      managers.csv
Optional:
  referees.csv   bookings.csv   substitutions.csv   penalty_kicks.csv
  tournament_standings.csv   group_standings.csv

Data source: https://datahub.io/collections/football (DataHub World Cup Datasets)
License: PDDL (Open Data Commons Public Domain Dedication and License)

Usage:
    python -m etl.loader --data-dir data --max-tournaments 5
    python -m etl.loader --data-dir data
"""

import csv
import os
import time
from samyama import SamyamaClient

GRAPH = "default"

NULLS = {"", "not applicable", "not available", "n/a"}

# _batch_create_nodes / _batch_create_edges each build one query per call.
# Keep batches well under the graph engine's query-parser limits — squads.csv
# and substitutions.csv alone are 10-14K rows.
BATCH_SIZE = 300


# ---------------------------------------------------------------------------
# Cypher helpers
# ---------------------------------------------------------------------------

def _escape(value) -> str:
    if value is None:
        return ""
    return str(value).replace('"', '').replace("\n", " ").replace("\r", "")


def _q(val) -> str:
    return f'"{_escape(val)}"'


def _prop_str(props: dict) -> str:
    parts = []
    for key, val in props.items():
        if val is None:
            continue
        if isinstance(val, bool):
            parts.append(f"{key}: {'true' if val else 'false'}")
        elif isinstance(val, (int, float)):
            parts.append(f"{key}: {val}")
        else:
            parts.append(f'{key}: {_q(val)}')
    return "{" + ", ".join(parts) + "}"


def _match_to_where(var_name, match_str):
    """Convert 'prop: "value"' to 'var.prop = "value"' for WHERE clause.

    Index scans only trigger with WHERE, not inline MATCH properties.
    """
    return f"{var_name}.{match_str.replace(': ', ' = ', 1)}"


def _batch_create_nodes(client, nodes):
    """Create nodes in chunked CREATE queries. Each node: (label, props)."""
    for start in range(0, len(nodes), BATCH_SIZE):
        chunk = nodes[start:start + BATCH_SIZE]
        if not chunk:
            continue
        parts = [f"(:{label} {_prop_str(props)})" for label, props in chunk]
        client.query(f"CREATE {', '.join(parts)}", GRAPH)


def _batch_create_edges(client, edges):
    """Create edges between EXISTING nodes in chunked MATCH...WHERE...CREATE queries.

    Each edge: (src_label, src_match_str, rel_type, tgt_label, tgt_match_str, props_or_None)
    Deduplicates MATCH patterns within a chunk so each unique node is matched once.
    """
    for start in range(0, len(edges), BATCH_SIZE):
        chunk = edges[start:start + BATCH_SIZE]
        if not chunk:
            continue
        var_map = {}
        match_parts = []
        where_parts = []
        create_parts = []

        for src_label, src_match, rel, tgt_label, tgt_match, props in chunk:
            src_key = (src_label, src_match)
            tgt_key = (tgt_label, tgt_match)

            if src_key not in var_map:
                vname = f"n{len(var_map)}"
                var_map[src_key] = vname
                match_parts.append(f"({vname}:{src_label})")
                where_parts.append(_match_to_where(vname, src_match))

            if tgt_key not in var_map:
                vname = f"n{len(var_map)}"
                var_map[tgt_key] = vname
                match_parts.append(f"({vname}:{tgt_label})")
                where_parts.append(_match_to_where(vname, tgt_match))

            src_var = var_map[src_key]
            tgt_var = var_map[tgt_key]
            prop_part = f" {_prop_str(props)}" if props else ""
            create_parts.append(f"({src_var})-[:{rel}{prop_part}]->({tgt_var})")

        q = (f"MATCH {', '.join(match_parts)} "
             f"WHERE {' AND '.join(where_parts)} "
             f"CREATE {', '.join(create_parts)}")
        client.query(q, GRAPH)


# ---------------------------------------------------------------------------
# CSV parsing helpers
# ---------------------------------------------------------------------------

def _open_csv(path):
    f = open(path, "r", encoding="utf-8", newline="")
    return csv.DictReader(f), f


def _s(row, key):
    val = row.get(key)
    if val is None:
        return None
    val = val.strip()
    return val if val and val.lower() not in NULLS else None


def _i(row, key):
    val = _s(row, key)
    try:
        return int(float(val)) if val is not None else None
    except ValueError:
        return None


def _f(row, key):
    val = _s(row, key)
    try:
        return float(val) if val is not None else None
    except ValueError:
        return None


def _b(row, key):
    val = _s(row, key)
    if val is None:
        return False
    return val.strip() in ("1", "true", "True", "yes")


def _s0(row, key):
    """Like _s(), but defaults to '' instead of None. Use for properties that
    feed CONTAINS-based search tools — the engine errors on CONTAINS against a
    NULL property (same class of bug as NULL string concatenation), so
    frequently-searched text fields need a non-NULL fallback."""
    return _s(row, key) or ""


def _split_countries(raw):
    """host_country can list multiple co-hosts as a comma-separated string."""
    if not raw:
        return []
    return [c.strip() for c in raw.split(",") if c.strip()]


# ---------------------------------------------------------------------------
# Registry (dedup tracking, no queries)
# ---------------------------------------------------------------------------

class Registry:
    def __init__(self):
        self.countries: set[str] = set()
        self.stadiums: set[str] = set()
        self.teams: set[str] = set()
        self.team_name: dict[str, str] = {}     # team_id -> name
        self.name_to_team: dict[str, str] = {}   # name.lower() -> team_id
        self.tournaments: set[str] = set()
        self.matches: set[str] = set()
        self.players: set[str] = set()
        self.managers: set[str] = set()
        self.referees: set[str] = set()
        self.played_for: set[str] = set()        # "player|team|tournament"


def _ensure_country(reg, name, new_nodes):
    if not name:
        return
    key = name.lower()
    if key in reg.countries:
        return
    reg.countries.add(key)
    new_nodes.append(("Country", {"name": name}))


# ---------------------------------------------------------------------------
# Phase loaders
# ---------------------------------------------------------------------------

def _load_stadiums(client, data_dir, reg, counts):
    path = os.path.join(data_dir, "stadiums.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    new_nodes, country_nodes = [], []
    for row in reader:
        sid = _s(row, "stadium_id")
        if not sid or sid in reg.stadiums:
            continue
        reg.stadiums.add(sid)
        country = _s(row, "country_name")
        _ensure_country(reg, country, country_nodes)
        new_nodes.append(("Stadium", {
            "stadium_id": sid,
            "name": _s(row, "stadium_name"),
            "city": _s(row, "city_name"),
            "country": country,
            "capacity": _i(row, "stadium_capacity"),
        }))
    f.close()
    _batch_create_nodes(client, country_nodes)
    _batch_create_nodes(client, new_nodes)
    counts["stadiums"] = len(reg.stadiums)


def _load_teams(client, data_dir, reg, counts):
    path = os.path.join(data_dir, "teams.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    new_nodes = []
    for row in reader:
        tid = _s(row, "team_id")
        if not tid or tid in reg.teams:
            continue
        reg.teams.add(tid)
        name = _s(row, "team_name")
        reg.team_name[tid] = name
        if name:
            reg.name_to_team[name.lower()] = tid
        new_nodes.append(("Team", {
            "team_id": tid,
            "name": name,
            "code": _s(row, "team_code"),
            "confederation": _s(row, "confederation_name"),
            "confederation_code": _s(row, "confederation_code"),
            "region": _s(row, "region_name"),
            "mens_team": _b(row, "mens_team"),
            "womens_team": _b(row, "womens_team"),
        }))
    f.close()
    _batch_create_nodes(client, new_nodes)
    counts["teams"] = len(reg.teams)


def _load_tournaments(client, data_dir, reg, counts):
    path = os.path.join(data_dir, "tournaments.csv")
    if not os.path.exists(path):
        return []
    reader, f = _open_csv(path)
    new_nodes, country_nodes, edges = [], [], []
    tournament_ids = []
    for row in reader:
        tid = _s(row, "tournament_id")
        if not tid or tid in reg.tournaments:
            continue
        reg.tournaments.add(tid)
        tournament_ids.append(tid)

        host_country_raw = _s(row, "host_country")
        winner_name = _s(row, "winner")
        new_nodes.append(("Tournament", {
            "tournament_id": tid,
            "name": _s(row, "tournament_name"),
            "year": _i(row, "year"),
            "start_date": _s(row, "start_date"),
            "end_date": _s(row, "end_date"),
            "host_country": host_country_raw,
            "winner": winner_name,
            "host_won": _b(row, "host_won"),
            "count_teams": _i(row, "count_teams"),
        }))

        for host in _split_countries(host_country_raw):
            _ensure_country(reg, host, country_nodes)
            edges.append(("Tournament", f"tournament_id: {_q(tid)}", "HOSTED_BY",
                           "Country", f"name: {_q(host)}", None))

        winner_team_id = reg.name_to_team.get(winner_name.lower()) if winner_name else None
        if winner_team_id:
            edges.append(("Tournament", f"tournament_id: {_q(tid)}", "WON_BY",
                           "Team", f"team_id: {_q(winner_team_id)}", None))
    f.close()
    _batch_create_nodes(client, country_nodes)
    _batch_create_nodes(client, new_nodes)
    _batch_create_edges(client, edges)
    counts["tournaments"] = len(reg.tournaments)
    return tournament_ids


def _load_matches(client, data_dir, reg, counts, tournament_filter=None, max_matches=0):
    path = os.path.join(data_dir, "matches.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    new_nodes, edges = [], []
    loaded = 0
    for row in reader:
        if max_matches and loaded >= max_matches:
            break
        mid = _s(row, "match_id")
        if not mid or mid in reg.matches:
            continue
        tournament_id = _s(row, "tournament_id")
        if tournament_filter is not None and tournament_id not in tournament_filter:
            continue
        reg.matches.add(mid)

        home_team_id = _s(row, "home_team_id")
        away_team_id = _s(row, "away_team_id")
        stadium_id = _s(row, "stadium_id")

        new_nodes.append(("Match", {
            "match_id": mid,
            "name": _s(row, "match_name"),
            "date": _s(row, "match_date"),
            "time": _s(row, "match_time"),
            "stage": _s(row, "stage_name"),
            "group_name": _s(row, "group_name"),
            "home_score": _i(row, "home_team_score"),
            "away_score": _i(row, "away_team_score"),
            "result": _s(row, "result"),
            "extra_time": _b(row, "extra_time"),
            "penalty_shootout": _b(row, "penalty_shootout"),
            "home_score_penalties": _i(row, "home_team_score_penalties"),
            "away_score_penalties": _i(row, "away_team_score_penalties"),
        }))

        mm = f"match_id: {_q(mid)}"
        if tournament_id and tournament_id in reg.tournaments:
            edges.append(("Match", mm, "IN_TOURNAMENT", "Tournament", f"tournament_id: {_q(tournament_id)}", None))
        if home_team_id and home_team_id in reg.teams:
            edges.append(("Match", mm, "HOME_TEAM", "Team", f"team_id: {_q(home_team_id)}", None))
        if away_team_id and away_team_id in reg.teams:
            edges.append(("Match", mm, "AWAY_TEAM", "Team", f"team_id: {_q(away_team_id)}", None))
        if stadium_id and stadium_id in reg.stadiums:
            edges.append(("Match", mm, "PLAYED_AT", "Stadium", f"stadium_id: {_q(stadium_id)}", None))

        loaded += 1
        if len(new_nodes) >= BATCH_SIZE:
            _batch_create_nodes(client, new_nodes)
            new_nodes = []
        if len(edges) >= BATCH_SIZE:
            _batch_create_edges(client, edges)
            edges = []
    _batch_create_nodes(client, new_nodes)
    _batch_create_edges(client, edges)
    f.close()
    counts["matches"] = len(reg.matches)


def _full_name(given_name, family_name):
    """Some players are known by a single (mononym) name — e.g. Brazilian
    players such as 'Adriano' or 'Ademir' — where the source data marks
    given_name as 'not applicable'. Concatenating NULL + string errors out
    in Cypher, so a display name is precomputed here instead."""
    if given_name and family_name:
        return f"{given_name} {family_name}"
    return family_name or given_name


def _position_from_flags(row):
    labels = []
    if _b(row, "goal_keeper"):
        labels.append("Goalkeeper")
    if _b(row, "defender"):
        labels.append("Defender")
    if _b(row, "midfielder"):
        labels.append("Midfielder")
    if _b(row, "forward"):
        labels.append("Forward")
    return ", ".join(labels) if labels else None


def _load_players(client, data_dir, reg, counts):
    """players.csv is the master player registry — one row per player, with
    count_tournaments already aggregated by the source dataset."""
    path = os.path.join(data_dir, "players.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    new_nodes = []
    for row in reader:
        pid = _s(row, "player_id")
        if not pid or pid in reg.players:
            continue
        reg.players.add(pid)
        given_name, family_name = _s(row, "given_name"), _s(row, "family_name")
        display_name = _full_name(given_name, family_name)
        given_name0, family_name0 = _s0(row, "given_name"), _s0(row, "family_name")
        new_nodes.append(("Player", {
            "player_id": pid,
            "name": display_name,
            "family_name": family_name0,
            "given_name": given_name0,
            "birth_date": _s(row, "birth_date"),
            "female": _b(row, "female"),
            "position": _position_from_flags(row),
            "count_tournaments": _i(row, "count_tournaments"),
        }))
        if len(new_nodes) >= BATCH_SIZE:
            _batch_create_nodes(client, new_nodes)
            new_nodes = []
    _batch_create_nodes(client, new_nodes)
    f.close()
    counts["players"] = len(reg.players)


def _load_squads(client, data_dir, reg, counts, tournament_filter=None):
    """squads.csv is the per-tournament roster: one row per player per team
    per tournament. Creates PLAYED_FOR edges carrying tournament context."""
    path = os.path.join(data_dir, "squads.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    edges = []
    edge_count = 0
    for row in reader:
        tournament_id = _s(row, "tournament_id")
        if tournament_filter is not None and tournament_id not in tournament_filter:
            continue
        pid = _s(row, "player_id")
        tid = _s(row, "team_id")
        if not pid or not tid or pid not in reg.players or tid not in reg.teams:
            continue
        key = f"{pid}|{tid}|{tournament_id}"
        if key in reg.played_for:
            continue
        reg.played_for.add(key)
        edges.append(("Player", f"player_id: {_q(pid)}", "PLAYED_FOR", "Team", f"team_id: {_q(tid)}", {
            "tournament_id": tournament_id,
            "position": _s(row, "position_name"),
            "shirt_number": _i(row, "shirt_number"),
        }))
        edge_count += 1
        if len(edges) >= BATCH_SIZE:
            _batch_create_edges(client, edges)
            edges = []
    _batch_create_edges(client, edges)
    f.close()
    counts["squad_entries"] = edge_count


def _load_managers(client, data_dir, reg, counts):
    path = os.path.join(data_dir, "managers.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    new_nodes, country_nodes, edges = [], [], []
    for row in reader:
        mid = _s(row, "manager_id")
        if not mid or mid in reg.managers:
            continue
        reg.managers.add(mid)
        country = _s(row, "country_name")
        _ensure_country(reg, country, country_nodes)
        given_name, family_name = _s(row, "given_name"), _s(row, "family_name")
        display_name = _full_name(given_name, family_name)
        given_name0, family_name0 = _s0(row, "given_name"), _s0(row, "family_name")
        new_nodes.append(("Manager", {
            "manager_id": mid,
            "name": display_name,
            "family_name": family_name0,
            "given_name": given_name0,
            "female": _b(row, "female"),
            "country": country,
        }))
        if country:
            edges.append(("Manager", f"manager_id: {_q(mid)}", "FROM", "Country", f"name: {_q(country)}", None))
    f.close()
    _batch_create_nodes(client, country_nodes)
    _batch_create_nodes(client, new_nodes)
    _batch_create_edges(client, edges)
    counts["managers"] = len(reg.managers)


def _load_referees(client, data_dir, reg, counts):
    path = os.path.join(data_dir, "referees.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    new_nodes, country_nodes, edges = [], [], []
    for row in reader:
        rid = _s(row, "referee_id")
        if not rid or rid in reg.referees:
            continue
        reg.referees.add(rid)
        country = _s(row, "country_name")
        _ensure_country(reg, country, country_nodes)
        given_name, family_name = _s(row, "given_name"), _s(row, "family_name")
        display_name = _full_name(given_name, family_name)
        given_name0, family_name0 = _s0(row, "given_name"), _s0(row, "family_name")
        new_nodes.append(("Referee", {
            "referee_id": rid,
            "name": display_name,
            "family_name": family_name0,
            "given_name": given_name0,
            "female": _b(row, "female"),
            "country": country,
            "confederation": _s(row, "confederation_name"),
        }))
        if country:
            edges.append(("Referee", f"referee_id: {_q(rid)}", "FROM", "Country", f"name: {_q(country)}", None))
    f.close()
    _batch_create_nodes(client, country_nodes)
    _batch_create_nodes(client, new_nodes)
    _batch_create_edges(client, edges)
    counts["referees"] = len(reg.referees)


def _load_goals(client, data_dir, reg, counts):
    """Goal nodes correlate to their Match/Player/Team via a synthetic
    per-row unique key (_seq): the graph engine does not persist a
    brand-new node when its CREATE pattern is chained directly after a
    MATCH clause, so node creation and edge creation are two queries."""
    path = os.path.join(data_dir, "goals.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    node_batch, edge_batch = [], []
    seq = 0
    goal_count = 0

    def flush():
        nonlocal node_batch, edge_batch
        if node_batch:
            _batch_create_nodes(client, node_batch)
            node_batch = []
        if edge_batch:
            _batch_create_edges(client, edge_batch)
            edge_batch = []

    for row in reader:
        match_id = _s(row, "match_id")
        if not match_id or match_id not in reg.matches:
            continue
        player_id = _s(row, "player_id")
        team_id = _s(row, "player_team_id") or _s(row, "team_id")

        seq += 1
        goal_id = _s(row, "goal_id") or f"g{seq}"
        node_batch.append(("Goal", {
            "goal_id": goal_id,
            "_seq": seq,
            "minute": _i(row, "minute_regulation"),
            "minute_stoppage": _i(row, "minute_stoppage"),
            "own_goal": _b(row, "own_goal"),
            "penalty": _b(row, "penalty"),
            "period": _s(row, "match_period"),
        }))
        edge_batch.append(("Goal", f"_seq: {seq}", "SCORED_IN", "Match", f"match_id: {_q(match_id)}", None))
        if player_id and player_id in reg.players:
            edge_batch.append(("Goal", f"_seq: {seq}", "SCORED_BY", "Player", f"player_id: {_q(player_id)}", None))
        if team_id and team_id in reg.teams:
            edge_batch.append(("Goal", f"_seq: {seq}", "FOR_TEAM", "Team", f"team_id: {_q(team_id)}", None))

        goal_count += 1
        if len(node_batch) >= BATCH_SIZE or len(edge_batch) >= BATCH_SIZE:
            flush()
    flush()
    f.close()
    counts["goals"] = goal_count


def _load_events(client, path, reg, label, id_col, rel_player, extra_props_fn):
    """Shared loader for Booking/Substitution/PenaltyKick — each row is one
    event tied to an existing Match and (optionally) an existing Player."""
    if not os.path.exists(path):
        return 0
    reader, f = _open_csv(path)
    node_batch, edge_batch = [], []
    seq = 0
    count = 0

    def flush():
        nonlocal node_batch, edge_batch
        if node_batch:
            _batch_create_nodes(client, node_batch)
            node_batch = []
        if edge_batch:
            _batch_create_edges(client, edge_batch)
            edge_batch = []

    for row in reader:
        match_id = _s(row, "match_id")
        if not match_id or match_id not in reg.matches:
            continue
        seq += 1
        props = {id_col: _s(row, id_col), "_seq": seq}
        props.update(extra_props_fn(row))
        node_batch.append((label, props))
        edge_batch.append((label, f"_seq: {seq}", "IN_MATCH", "Match", f"match_id: {_q(match_id)}", None))

        player_id = _s(row, "player_id")
        if player_id and player_id in reg.players:
            edge_batch.append((label, f"_seq: {seq}", rel_player, "Player", f"player_id: {_q(player_id)}", None))

        count += 1
        if len(node_batch) >= BATCH_SIZE or len(edge_batch) >= BATCH_SIZE:
            flush()
    flush()
    f.close()
    return count


def _load_bookings(client, data_dir, reg, counts):
    counts["bookings"] = _load_events(
        client, os.path.join(data_dir, "bookings.csv"), reg, "Booking", "booking_id", "BOOKED",
        lambda row: {
            "minute": _i(row, "minute_regulation"),
            "period": _s(row, "match_period"),
            "yellow_card": _b(row, "yellow_card"),
            "red_card": _b(row, "red_card"),
            "second_yellow_card": _b(row, "second_yellow_card"),
            "sending_off": _b(row, "sending_off"),
        },
    )


def _load_substitutions(client, data_dir, reg, counts):
    counts["substitutions"] = _load_events(
        client, os.path.join(data_dir, "substitutions.csv"), reg, "Substitution", "substitution_id", "INVOLVES",
        lambda row: {
            "minute": _i(row, "minute_regulation"),
            "period": _s(row, "match_period"),
            "going_off": _b(row, "going_off"),
            "coming_on": _b(row, "coming_on"),
        },
    )


def _load_penalty_kicks(client, data_dir, reg, counts):
    counts["penalty_kicks"] = _load_events(
        client, os.path.join(data_dir, "penalty_kicks.csv"), reg, "PenaltyKick", "penalty_kick_id", "TAKEN_BY",
        lambda row: {"converted": _b(row, "converted")},
    )


def _load_tournament_standings(client, data_dir, reg, counts):
    path = os.path.join(data_dir, "tournament_standings.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    edges = []
    count = 0
    for row in reader:
        tid = _s(row, "team_id")
        tournament_id = _s(row, "tournament_id")
        if not tid or tid not in reg.teams or tournament_id not in reg.tournaments:
            continue
        edges.append(("Team", f"team_id: {_q(tid)}", "FINISHED", "Tournament", f"tournament_id: {_q(tournament_id)}", {
            "position": _i(row, "position"),
        }))
        count += 1
        if len(edges) >= BATCH_SIZE:
            _batch_create_edges(client, edges)
            edges = []
    _batch_create_edges(client, edges)
    f.close()
    counts["tournament_standings"] = count


def _load_group_standings(client, data_dir, reg, counts):
    path = os.path.join(data_dir, "group_standings.csv")
    if not os.path.exists(path):
        return
    reader, f = _open_csv(path)
    edges = []
    count = 0
    for row in reader:
        tid = _s(row, "team_id")
        tournament_id = _s(row, "tournament_id")
        if not tid or tid not in reg.teams or tournament_id not in reg.tournaments:
            continue
        edges.append(("Team", f"team_id: {_q(tid)}", "IN_GROUP", "Tournament", f"tournament_id: {_q(tournament_id)}", {
            "group_name": _s(row, "group_name"),
            "position": _i(row, "position"),
            "played": _i(row, "played"),
            "wins": _i(row, "wins"),
            "draws": _i(row, "draws"),
            "losses": _i(row, "losses"),
            "goals_for": _i(row, "goals_for"),
            "goals_against": _i(row, "goals_against"),
            "goal_difference": _i(row, "goal_difference"),
            "points": _i(row, "points"),
            "advanced": _b(row, "advanced"),
        }))
        count += 1
        if len(edges) >= BATCH_SIZE:
            _batch_create_edges(client, edges)
            edges = []
    _batch_create_edges(client, edges)
    f.close()
    counts["group_standings"] = count


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_football(
    client: SamyamaClient,
    data_dir: str = "data",
    max_tournaments: int = 0,
    max_matches: int = 0,
) -> dict:
    """
    Load FIFA World Cup data from the DataHub-style CSV export into Samyama.

    Args:
        client: SamyamaClient instance.
        data_dir: Directory containing tournaments.csv, teams.csv, stadiums.csv,
                  matches.csv, players.csv, squads.csv, goals.csv, managers.csv,
                  and optionally referees.csv, bookings.csv, substitutions.csv,
                  penalty_kicks.csv, tournament_standings.csv, group_standings.csv.
        max_tournaments: Max tournaments to load (0 = all). Filters matches and
                         squads to those tournaments.
        max_matches: Max matches to load (0 = all). Applied within the
                     tournament filter, useful for quick tests.

    Returns:
        Dict with counts of all created entities.
    """
    indexes = [
        ("Country", "name"), ("Stadium", "stadium_id"), ("Stadium", "name"),
        ("Team", "team_id"), ("Team", "name"),
        ("Tournament", "tournament_id"), ("Tournament", "name"),
        ("Match", "match_id"), ("Match", "name"),
        ("Player", "player_id"), ("Player", "name"),
        ("Manager", "manager_id"), ("Manager", "name"),
        ("Referee", "referee_id"), ("Referee", "name"),
        ("Goal", "_seq"), ("Booking", "_seq"), ("Substitution", "_seq"), ("PenaltyKick", "_seq"),
    ]
    for label, prop in indexes:
        try:
            client.query(f"CREATE INDEX ON :{label}({prop})", GRAPH)
        except Exception:
            pass
    print(f"Created {len(indexes)} indexes", flush=True)

    reg = Registry()
    counts = {
        "stadiums": 0, "teams": 0, "tournaments": 0, "matches": 0, "players": 0,
        "squad_entries": 0, "managers": 0, "referees": 0, "goals": 0,
        "bookings": 0, "substitutions": 0, "penalty_kicks": 0,
        "tournament_standings": 0, "group_standings": 0,
    }
    t0 = time.time()

    print("Phase 1/9: Loading stadiums ...", flush=True)
    _load_stadiums(client, data_dir, reg, counts)

    print("Phase 2/9: Loading teams ...", flush=True)
    _load_teams(client, data_dir, reg, counts)

    print("Phase 3/9: Loading tournaments ...", flush=True)
    tournament_ids = _load_tournaments(client, data_dir, reg, counts)
    tournament_filter = set(tournament_ids[:max_tournaments]) if max_tournaments else None

    print("Phase 4/9: Loading matches ...", flush=True)
    _load_matches(client, data_dir, reg, counts, tournament_filter=tournament_filter, max_matches=max_matches)

    print("Phase 5/9: Loading players and squads ...", flush=True)
    _load_players(client, data_dir, reg, counts)
    _load_squads(client, data_dir, reg, counts, tournament_filter=tournament_filter)

    print("Phase 6/9: Loading managers and referees ...", flush=True)
    _load_managers(client, data_dir, reg, counts)
    _load_referees(client, data_dir, reg, counts)

    print("Phase 7/9: Loading goals ...", flush=True)
    _load_goals(client, data_dir, reg, counts)

    print("Phase 8/9: Loading bookings, substitutions and penalty kicks ...", flush=True)
    _load_bookings(client, data_dir, reg, counts)
    _load_substitutions(client, data_dir, reg, counts)
    _load_penalty_kicks(client, data_dir, reg, counts)

    print("Phase 9/9: Loading standings ...", flush=True)
    _load_tournament_standings(client, data_dir, reg, counts)
    _load_group_standings(client, data_dir, reg, counts)

    elapsed = time.time() - t0
    counts["countries"] = len(reg.countries)
    counts["nodes"] = (
        counts["stadiums"] + counts["teams"] + counts["tournaments"] + counts["matches"]
        + counts["players"] + counts["managers"] + counts["referees"] + counts["goals"]
        + counts["bookings"] + counts["substitutions"] + counts["penalty_kicks"] + counts["countries"]
    )

    print(f"\n{'='*60}", flush=True)
    print(f"Football KG load complete in {elapsed:.1f}s", flush=True)
    print(f"{'='*60}", flush=True)
    for k, v in counts.items():
        print(f"  {k:<21s} {v}", flush=True)
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Load DataHub World Cup data into Samyama")
    ap.add_argument("--data-dir", default="data", help="Path to World Cup CSV files")
    ap.add_argument("--max-tournaments", type=int, default=0, help="Max tournaments (0=all)")
    ap.add_argument("--max-matches", type=int, default=0, help="Max matches (0=all)")
    ap.add_argument("--url", default=None, help="Samyama server URL (omit for embedded)")
    args = ap.parse_args()

    c = SamyamaClient.connect(args.url) if args.url else SamyamaClient.embedded()
    load_football(c, data_dir=args.data_dir, max_tournaments=args.max_tournaments,
                  max_matches=args.max_matches)
