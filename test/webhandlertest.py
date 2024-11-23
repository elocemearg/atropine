#!/usr/bin/python3

"""
Test the page-serving handlers under py/dynamicpages. Intended to catch
problems where a change stops a page from working and it isn't noticed.
We don't verify the HTML that's returned, we just make sure that valid
requests have the expected effects on the tourney and that they don't
throw exceptions.
"""

import sys
import os
import importlib
import json

if os.name == "nt":
    if "APPDATA" in os.environ:
        tourneys_dir = os.path.join(os.getenv("APPDATA"), "Atropine", "tourneys")
    else:
        tourneys_dir = "."
else:
    if "HOME" in os.environ:
        tourneys_dir = os.path.join(os.getenv("HOME"), ".atropine", "tourneys")
    else:
        tourneys_dir = "."

base_dir = "."

sys.path.append(os.path.join(base_dir, "py"))
sys.path.append(os.path.join(base_dir, "py", "dynamicpages"))
sys.path.append(os.path.join(base_dir, "py", "servicehandlers"))
sys.path.append(os.path.join(base_dir, "generators"))

import httpresponse
import countdowntourney
import fieldstorage

page_modules = {}
for python_file in os.listdir(os.path.join(base_dir, "py", "dynamicpages")):
    if python_file.endswith(".py"):
        module_name = python_file[:-3]
        page_modules[module_name] = importlib.import_module(module_name)

os.environ["TOURNEYSPATH"] = tourneys_dir

class TestFailedException(Exception):
    def __init__(self, description):
        self.description = description

class MockHTTPRequestHandler(object):
    def __init__(self, page_name, tourney_name, extra_components, query_string):
        self.path = "/atropine/" + ("global" if not tourney_name else tourney_name) + "/" + page_name
        if extra_components:
            self.path += "/".join(extra_components)
        self.query_string = query_string

    def is_client_from_localhost(self):
        return True

def make_request(page_name, tourney_name, extra_components, names_values, request_method="POST"):
    response = httpresponse.HTTPResponse()
    if tourney_name:
        tourney = countdowntourney.tourney_open(tourney_name)
    else:
        tourney = None

    query_string = ""
    if request_method == "GET" and names_values:
        query_string = "?" + "&".join([urllib.parse.quote_plus(name) + "=" + urllib.parse.quote_plus(str(names_values[name])) for name in names_values ])

    form = fieldstorage.FieldStorage(content_type="application/x-www-form-urlencoded", request_method=request_method, query_string=query_string, post_data=b'')
    for name in names_values:
        form.set(name, str(names_values[name]))

    http_req_mock = MockHTTPRequestHandler(page_name, tourney_name, extra_components, query_string)
    page_modules[page_name].handle(http_req_mock, response, tourney, request_method, form, query_string, extra_components)
    #print (response.get_string())
    if tourney:
        tourney.close()

def assert_equal(observed, expected, context=""):
    if expected != observed:
        raise TestFailedException("(%s) Expected [%s], observed [%s]" % (context, str(expected), str(observed)))

def add_fixtures(tourney, round_number, fixtures, division=0):
    start_seq = tourney.get_max_game_seq_in_round(round_number)
    if start_seq is not None:
        start_seq += 1
    else:
        start_seq = 1

    game_seq = start_seq
    json_fixtures = []
    for (table_number, name1, name2) in fixtures:
        json_fixtures.append({
            "round_no" : round_number,
            "table_no" : table_number,
            "round_seq" : game_seq,
            "division" : division,
            "game_type" : "P",
            "p1" : name1,
            "p2" : name2,
            "s1" : None,
            "s2" : None
        })
        game_seq += 1

    json_fixture_lump = {
        "fixtures" : json_fixtures,
        "rounds" : [ { "name" : "Round %d" % (round_number), "round" : round_number } ]
    }

    params = {}
    params["jsonfixtureplan"] = json.dumps(json_fixture_lump)
    params["accept"] = "Accept Fixtures"
    params["generator"] = "fixgen_manual"
    
    make_request("fixturegen", tourney.get_name(), ["fixgen_manual"], params)

def post_result(tourney, round_number, name1, score1, name2, score2, tb=False):
    # Post what would be posted to games.py when the user enters a result
    params = {
        "entryname1" : name1,
        "entryname2" : name2,
        "entryscore1" : score1,
        "entryscore2" : score2,
    }
    if tb:
        params["entrytiebreak"] = "1"
    params["entrysubmit"] = "Submit"
    make_request("games", tourney.get_name(), [str(round_number)], params)

def main():
    tourney_name = "_webhandlertest"

    # Remove the _webhandlertest tourney if we already have it
    try:
        os.unlink(os.path.join(os.getenv("TOURNEYSPATH"), tourney_name + ".db"))
    except FileNotFoundError as e:
        pass

    # Create the _webhandlertest tourney
    make_request("home", None, [], {
        "name" : tourney_name,
        "longtourneyname" : "Web Handler Test",
        "displayshape" : "0",
        "createtourney" : "Create Tourney"
    })

    # Set the players
    make_request("tourneysetup", tourney_name, [], {
        "playerlist" : """Sleve McDichael
Darryl Archideld
Kevin Nogilny
Bobson Dugnutt
Willie Dustice
Todd Bonzalez
""",
        "autoratingbehaviour" : "2",
        "playerlistsubmit" : "Save Player List"
    })

    # Set other information about the tourney
    make_request("tourneysetup", tourney_name, [], {
        "fullname": "Web Handler Test",
        "venue": "Blitherington, Whatshire",
        "dateyear": "2024",
        "datemonth": "11",
        "dateday": "23",
        "accessibletables": "",
        "accessibletablesdefault": "0",
        "div0_lastround" : "3",
        "div0_numgamesperplayer" : "3",
        "div0_qualplaces" : "2",
        "rulessubmit" : "Save Changes"
    })

    tourney = countdowntourney.tourney_open(tourney_name)
    assert_equal(len(tourney.get_players()), 6)

    # Add a new player, let's say they're a newbie
    make_request("player", tourney_name, [], {
        "newplayersubmit" : "Create Player",
        "setname" : "Mike Truk",
        "setrating" : "1234",
        "setpreferredtable" : "0",
        "setnewbie" : "1"
    })

    # Modify Sleve McDichael's rating to reflect his elevated status
    sleve = tourney.get_player_from_name("Sleve McDichael")
    make_request("player", tourney_name, [ str(sleve.get_id()) ], {
        "editplayer" : "Save Changes",
        "setrating" : "1500.1"
    })

    # Set a custom prune name, keep the other advanced settings as the default
    make_request("tourneysetupadvanced", tourney_name, [], {
        "submit" : "Save Changes",
        "rank" : "0",
        "rankfinals" : "1",
        "prunename" : "Pruney McPruneface",
        "tournamentratingbonus" : "50",
        "tournamentratingdiffcap" : "40"
    })

    assert_equal(len(tourney.get_players()), 7)
    assert_equal(tourney.get_auto_prune_name(), "Pruney McPruneface")

    # Add fixtures - do this via fixturegen.py
    add_fixtures(tourney, 1, [
        (1, "Sleve McDichael", "Mike Truk"),
        (2, "Darryl Archideld", "Kevin Nogilny"),
        (3, "Willie Dustice", "Pruney McPruneface"),
        (4, "Todd Bonzalez", "Bobson Dugnutt")
    ])

    games = tourney.get_games(round_no=1)
    assert_equal(len(games), 4)

    # Post results with games.py
    post_result(tourney, 1, "Sleve McDichael", 60, "Mike Truk", 50)
    post_result(tourney, 1, "Darryl Archideld", 44, "Kevin Nogilny", 72)
    post_result(tourney, 1, "Willie Dustice", 69, "Pruney McPruneface", 0)
    post_result(tourney, 1, "Todd Bonzalez", 65, "Bobson Dugnutt", 55, True)

    tourney.close()

if __name__ == "__main__":
    main()
