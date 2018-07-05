#!/usr/bin/python

import sys
import cgi
import cgitb
import json
import cgicommon

def send_error_reply(description):
    reply = dict()
    reply["success"] = False
    reply["description"] = description
    json.dump(reply, sys.stdout)

def get_standings(tourney, form):
    num_divs = tourney.get_num_divisions()
    reply = dict()
    reply["success"] = True
    
    rank_method = tourney.get_rank_method()
    if rank_method == countdowntourney.RANK_WINS_POINTS:
        rank_fields = ["wins", "points"]
    elif rank_method == countdowntourney.RANK_WINS_SPREAD:
        rank_fields = ["wins", "spread"]
    elif rank_method == countdowntourney.RANK_POINTS:
        rank_fields = ["points"]
    else:
        rank_fields = None

    reply["rank_fields"] = rank_fields

    div_standings_list = []
    for div in range(num_divs):
        standings = []
        div_standings = tourney.get_standings(div)
        for s in div_standings:
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
            standing["withdrawn"] = p.is_withdrawn()
            standings.append(standing)
        div_dict = dict()
        div_dict["div_num"] = div
        div_dict["div_name"] = tourney.get_division_name(div)
        div_dict["div_short_name"] = tourney.get_short_division_name(div)
        div_dict["standings"] = standings
        div_standings_list.append(div_dict)

    reply["divisions"] = div_standings_list

    return reply

def get_games(tourney, form):
    round_no = form.getfirst("round")
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
        for g in games:
            game_dict = dict()
            names = g.get_player_names()
            game_dict["name1"] = names[0]
            game_dict["name2"] = names[1]
            game_dict["score1"] = g.s1
            game_dict["score2"] = g.s2
            game_dict["tb"] = g.tb
            game_dict["table"] = g.table_no
            games_per_table[(g.round_no, g.table_no)] = games_per_table.get((g.round_no, g.table_no), 0) + 1
            game_dict["seq"] = g.seq
            game_dict["round"] = g.round_no
            game_dict["complete"] = g.is_complete()
            game_dict["score_text"] = g.format_score()
            games_this_div.append(game_dict)

        if len(games_per_table) > 0:
            max_games_per_table = max([ games_per_table[x] for x in games_per_table ])
        else:
            max_games_per_table = 0
        div_dict = dict()
        div_dict["div_num"] = div
        div_dict["div_name"] = tourney.get_division_name(div)
        div_dict["div_short_name"] = tourney.get_short_division_name(div)
        div_dict["games"] = games_this_div
        div_dict["max_games_per_table"] = max_games_per_table
        div_games.append(div_dict)
    reply["divisions"] = div_games

    return reply

def get_structure(tourney, form):
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
    
    return reply

def get_game_logs(tourney, form):
    logs = tourney.get_logs_since()
    
    reply = dict()
    reply["success"] = True

    reply_logs = []
    for l in logs:
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
            "superseded" : bool(l[13])
        })

    reply["logs"] = reply_logs
    return reply

def get_teleost_state(tourney, form):
    reply = dict()
    reply["success"] = True
    reply["current_mode"] = tourney.get_effective_teleost_mode()
    opts = tourney.get_teleost_options(reply["current_mode"])
    reply_opts = dict()
    for opt in opts:
        reply_opts[opt.name] = opt.value
    reply["options"] = reply_opts
    return reply

def get_all(tourney, form):
    reply = dict()
    for request in valid_requests:
        if request != "all" and request != "default":
            reply[request] = valid_requests[request](tourney, form)
    reply["success"] = True
    return reply

def get_info_required_by_mode(tourney, form):
    reply = dict()
    # Give the user the teleost state and the general tournament structure
    # (divisions and rounds) plus anything required for the current
    # teleost mode.
    reply["teleost"] = get_teleost_state(tourney, form)
    reply["structure"] = get_structure(tourney, form)
    requests = countdowntourney.get_teleost_mode_services_to_fetch(reply["teleost"]["current_mode"])
    for request in requests:
        if request != "default" and request in valid_requests:
            reply[request] = valid_requests[request](tourney, form)
    reply["success"] = True
    return reply

cgitb.enable()

print "Content-Type: application/json; charset=utf-8"
print ""

form = cgi.FieldStorage()
tourney_name = form.getfirst("tourney")
request = form.getfirst("request")

valid_requests = dict()
valid_requests["standings"] = get_standings
valid_requests["games"] = get_games
valid_requests["logs"] = get_game_logs
valid_requests["structure"] = get_structure
valid_requests["teleost"] = get_teleost_state
valid_requests["all"] = get_all
valid_requests["default"] = get_info_required_by_mode

cgicommon.set_module_path()

import countdowntourney

if tourney_name is None:
    send_error_reply("Bad request: no tourney name specified.")
    sys.exit(0)

if request is None:
    # Information we fetch depends on current mode
    request = "default"

if request not in valid_requests:
    send_error_reply("Bad request: request type \"%s\" is not recognised." % (request))
    sys.exit(0)

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
    reply_object = valid_requests[request](tourney, form)

except countdowntourney.TourneyException as e:
    send_error_reply(e.description)
    sys.exit(0)

json.dump(reply_object, sys.stdout, indent=4)

sys.exit(0)
