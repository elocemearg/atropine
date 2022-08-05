#!/usr/bin/python3

import sys
import json
import countdowntourney
import uploadercli

valid_requests = dict()

def get_standings(tourney, options):
    num_divs = tourney.get_num_divisions()
    reply = dict()
    reply["success"] = True

    rank_method = tourney.get_rank_method()
    rank_fields = rank_method.get_rank_fields()
    reply["rank_fields"] = rank_fields

    player_to_team_colour = dict()
    if tourney.are_players_assigned_teams():
        players = tourney.get_players()
        for player in players:
            player_to_team_colour[player.get_name()] = player.get_team_colour_tuple()

    div_standings_list = []
    for div in range(num_divs):
        standings = []
        div_standings = tourney.get_standings(div, True)
        for s in div_standings:
            team_colour = player_to_team_colour.get(s.name, None)
            if team_colour is not None:
                team_colour = list(team_colour)

            p = tourney.get_player_from_name(s.name)
            standing = dict()
            standing["position"] = s.position
            standing["name"] = s.name
            standing["played"] = s.played
            standing["wins"] = s.wins
            standing["points"] = s.points
            standing["draws"] = s.draws
            standing["spread"] = s.spread
            standing["rating"] = s.rating
            standing["team_colour"] = team_colour
            standing["withdrawn"] = p.is_withdrawn()
            standing["qualified"] = s.qualified
            standing["finals_points"] = s.finals_points
            standing["finals_form"] = s.finals_form
            standing["secondary_rank_values"] = s.get_secondary_rank_values()
            standing["secondary_rank_value_strings"] = s.get_secondary_rank_value_strings()
            standings.append(standing)
        div_dict = dict()
        div_dict["div_num"] = div
        div_dict["div_name"] = tourney.get_division_name(div)
        div_dict["div_short_name"] = tourney.get_short_division_name(div)
        div_dict["standings"] = standings
        div_standings_list.append(div_dict)

    reply["secondary_rank_headings"] = rank_method.get_secondary_rank_headings(short=True)
    reply["divisions"] = div_standings_list

    return reply

def get_games(tourney, options):
    round_no = options.get("round")
    if round_no is not None:
        try:
            round_no = int(round_no)
        except ValueError:
            raise countdowntourney.TourneyException("Invalid round number.")

    reply = dict()
    reply["success"] = True

    num_divs = tourney.get_num_divisions()
    div_games = []
    for div in range(num_divs):
        games = tourney.get_games(round_no=round_no, division=div)
        games_this_div = []
        games_per_table = dict()
        rounds_seen = set()
        for g in games:
            teams = g.get_team_colours()
            for i in range(len(teams)):
                if teams[i] is not None:
                    teams[i] = list(teams[i])
            game_dict = dict()
            names = g.get_player_names()
            game_dict["name1"] = names[0]
            game_dict["name2"] = names[1]
            game_dict["score1"] = g.s1
            game_dict["score2"] = g.s2
            game_dict["teamcolour1"] = teams[0]
            game_dict["teamcolour2"] = teams[1]
            game_dict["tb"] = g.tb
            game_dict["table"] = g.table_no
            games_per_table[(g.round_no, g.table_no)] = games_per_table.get((g.round_no, g.table_no), 0) + 1
            game_dict["seq"] = g.seq
            game_dict["round"] = g.round_no
            game_dict["complete"] = g.is_complete()
            game_dict["score_text"] = g.format_score()
            game_dict["type"] = g.get_game_type()
            rounds_seen.add(g.round_no)
            games_this_div.append(game_dict)

        max_games_per_table_per_round = dict()
        for round_seen in sorted(rounds_seen):
            games_per_table_this_round = dict()
            for x in games_per_table:
                if x[0] == round_seen:
                    games_per_table_this_round[x[1]] = games_per_table[(round_seen, x[1])]
            if len(games_per_table_this_round) > 0:
                max_games_per_table = max([ games_per_table_this_round[x] for x in games_per_table_this_round ])
            else:
                max_games_per_table = 0
            max_games_per_table_per_round[round_seen] = max_games_per_table
        else:
            max_games_per_table = 0
        div_dict = dict()
        div_dict["div_num"] = div
        div_dict["div_name"] = tourney.get_division_name(div)
        div_dict["div_short_name"] = tourney.get_short_division_name(div)
        div_dict["games"] = games_this_div
        div_dict["max_games_per_table_per_round"] = max_games_per_table_per_round
        div_games.append(div_dict)
    reply["divisions"] = div_games

    return reply

def get_structure(tourney, options):
    reply = dict()
    reply["success"] = True

    num_divs = tourney.get_num_divisions()

    divs = []
    for div in range(num_divs):
        divs.append( { "name" : tourney.get_division_name(div),
                       "num" : div,
                       "short_name" : tourney.get_short_division_name(div)
                    })

    reply["divisions"] = divs

    rounds = tourney.get_rounds()
    reply["rounds"] = rounds

    if tourney.are_players_assigned_teams():
        teams = tourney.get_team_scores()
        team_list = []
        for (team, score) in teams:
            team_list.append({
                "id" : team.get_id(),
                "name" : team.get_name(),
                "colour" : list(team.get_colour_tuple()),
                "score" : score
            })
        reply["teams"] = team_list
    else:
        reply["teams"] = None

    return reply

def get_game_logs(tourney, options):
    logs = tourney.get_logs_since()

    player_to_team_colour = dict()
    if tourney.are_players_assigned_teams():
        players = tourney.get_players()
        for player in players:
            player_to_team_colour[player.get_name()] = player.get_team_colour_tuple()

    reply = dict()
    reply["success"] = True

    reply_logs = []
    for l in logs:
        tc1 = player_to_team_colour.get(l[6], None)
        if tc1 is not None:
            tc1 = list(tc1)
        tc2 = player_to_team_colour.get(l[8], None)
        if tc2 is not None:
            tc2 = list(tc2)

        reply_logs.append({
            "seq" : l[0],
            "ts" : l[1],
            "round_no" : l[2],
            "round_seq" : l[3],
            "table_no" : l[4],
            "game_type" : l[5],
            "p1" : l[6],
            "s1" : l[7],
            "p2" : l[8],
            "s2" : l[9],
            "tb" : l[10],
            "log_type" : l[11],
            "div_num" : l[12],
            "superseded" : bool(l[13]),
            "tc1" : tc1,
            "tc2" : tc2,
            "comment" : l[14]
        })

    reply["logs"] = reply_logs
    return reply

def get_tuff_luck(tourney, options):
    reply = dict()
    reply["success"] = True

    # If numlosinggames is silly, negative or nonexistent, then default to 3
    num_losing_games = options.get("numlosinggames")
    if num_losing_games is None:
        num_losing_games = 3
    else:
        try:
            num_losing_games = int(num_losing_games)
        except ValueError:
            num_losing_games = 3
    if num_losing_games < 0:
        num_losing_games = 3

    tuffness_list = tourney.get_players_tuff_luck(num_losing_games)

    tuffness_reply = []
    pos = 0
    joint = 0
    prev_tuffness = None

    for (player, wins, tuffness, margin_list) in tuffness_list:
        name = player.get_name()

        if prev_tuffness is not None and tuffness == prev_tuffness:
            joint += 1
        else:
            pos += 1 + joint
            joint = 0

        reply_entry = {
                "pos" : pos,
                "name" : name,
                "tuffness" : tuffness,
                "margins" : margin_list
        }
        tuffness_reply.append(reply_entry)
        prev_tuffness = tuffness

    reply["table"] = tuffness_reply
    return reply

def get_overachievers(tourney, options):
    reply = dict()
    reply["success"] = True

    divisions = []

    num_divisions = tourney.get_num_divisions()
    for div_index in range(num_divisions):
        division_element = dict()
        division_element["div_num"] = div_index
        division_element["div_name"] = tourney.get_division_name(div_index)

        overachievers_list = tourney.get_players_overachievements(div_index)

        entry_list = []
        pos = 0
        joint = 0
        prev_diff = None

        for entry in overachievers_list:
            name = entry[0].get_name()
            seed = entry[1]
            rank = entry[2]
            diff = entry[3]
            if prev_diff is not None and prev_diff == diff:
                joint += 1
            else:
                pos += 1 + joint
                joint = 0

            reply_entry = {
                    "pos" : pos,
                    "name" : name,
                    "seed" : seed,
                    "rank" : rank,
                    "diff" : diff
            }
            entry_list.append(reply_entry)
            prev_diff = diff

        division_element["table"] = entry_list
        divisions.append(division_element)

    reply["divisions"] = divisions
    return reply


def get_teleost_state(tourney, options):
    reply = dict()
    reply["success"] = True

    mode = -1
    if "mode" in options:
        try:
            mode = int(options.get("mode"))
        except ValueError:
            mode = -1

    if mode > 0:
        reply["current_mode"] = int(options.get("mode"))
    elif mode == 0:
        # If we were in auto mode, which mode would we be showing now
        reply["current_mode"] = tourney.get_auto_effective_teleost_mode()
    else:
        reply["current_mode"] = tourney.get_effective_teleost_mode()
    opts = tourney.get_teleost_options(reply["current_mode"])
    reply_opts = dict()
    for opt in opts:
        reply_opts[opt.name] = opt.value
    reply["options"] = reply_opts
    reply["banner_text"] = tourney.get_banner_text()

    font_profile_id = tourney.get_display_font_profile_id()
    font_css = countdowntourney.DISPLAY_FONT_PROFILES[font_profile_id]["cssfile"]
    reply["font_css"] = font_css
    return reply

def get_high_scores(tourney, options):
    reply = dict()
    reply["success"] = True

    num_divs = tourney.get_num_divisions()

    game_sets = [ tourney.get_highest_winning_scores(10),
                  tourney.get_highest_losing_scores(10),
                  tourney.get_highest_combined_scores(10) ]

    set_names = [ "highest_winning_scores",
                  "highest_losing_scores",
                  "highest_combined_scores"
                ]

    for idx in range(len(game_sets)):
        reply_set = []
        for game in game_sets[idx]:
            names = [game["name1"], game["name2"]]
            round_num = game["round_num"]
            if num_divs > 1:
                div_short_name = tourney.get_short_division_name(game["division"])
            else:
                div_short_name = None;

            reply_set.append( {
                    "round_num" : round_num,
                    "div_short_name" : div_short_name,
                    "name1" : names[0],
                    "name2" : names[1],
                    "score1" : game["score1"],
                    "score2" : game["score2"],
                    "tb" : game["tb"]
                }
            )
        reply[set_names[idx]] = reply_set

    return reply

def get_info_required_by_mode(tourney, options):
    reply = dict()
    # Give the user the teleost state and the general tournament structure
    # (divisions and rounds) plus anything required for the current
    # teleost mode.
    reply["teleost"] = get_teleost_state(tourney, options)
    reply["structure"] = get_structure(tourney, options)
    requests = countdowntourney.get_teleost_mode_services_to_fetch(reply["teleost"]["current_mode"])
    for request in requests:
        if request != "default" and request in valid_requests:
            reply[request] = valid_requests[request](tourney, options)
    reply["success"] = True
    return reply

def get_tourney_details(tourney, options):
    return {
            "success" : True,
            "full_name" : tourney.get_full_name(),
            "venue" : tourney.get_venue(),
            "event_date" : tourney.get_event_date_string()
    }

def get_state_for_upload(tourney):
    requests = {
            "teleost" : get_teleost_state,
            "structure" : get_structure,
            "logs" : get_game_logs,
            "games" : get_games,
            "standings" : get_standings,
            "tourney" : get_tourney_details,
    }

    state = {}
    for req in requests:
        state[req] = requests[req](tourney, {})
    state["success"] = True

    return state

def get_all(tourney, options):
    reply = dict()
    for request in valid_requests:
        if request != "all" and request != "default" and request != "uploader":
            reply[request] = valid_requests[request](tourney, options)
    reply["success"] = True
    return reply

def get_uploader_status(tourney, options):
    try:
        reply = {}
        reply["success"] = True
        uploader_state = uploadercli.get_tourney_upload_state(tourney.get_name())
        if uploader_state and "password" in uploader_state:
            del uploader_state["password"]
        reply["uploader_state"] = uploader_state
        return reply
    except uploadercli.UploaderClientException as e:
        reply["success"] = False
        reply["message"] = str(e)
        return reply

valid_requests["standings"] = get_standings
valid_requests["games"] = get_games
valid_requests["logs"] = get_game_logs
valid_requests["tuffluck"] = get_tuff_luck
valid_requests["overachievers"] = get_overachievers
valid_requests["structure"] = get_structure
valid_requests["teleost"] = get_teleost_state
valid_requests["highscores"] = get_high_scores
valid_requests["tourney"] = get_tourney_details
valid_requests["all"] = get_all
valid_requests["default"] = get_info_required_by_mode
valid_requests["uploader"] = get_uploader_status

