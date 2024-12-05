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

# Mess about creating divisions then put things back the way they were
def division_diversion(tourney):
    tourney_name = tourney.get_name()

    # Create three divisions
    make_request("divsetup", tourney_name, [], {
        "setdivcount" : "Set number of divisions",
        "divcount" : "3"
    })

    assert_equal(tourney.get_num_divisions(), 3)

    # Divide the players into divisions.
    # Division A (0): Sleve McDichael and Kevin Nogilny.
    # Division B (1): Darryl Archideld and Todd Bonzalez.
    # Division C (2): Bobson Dugnutt and Willie Dustice.
    # Also name the divisions Apple, Banana and Cherry.
    params = {
        "newdivname0" : "Apple",
        "newdivname1" : "Banana",
        "newdivname2" : "Cherry",
        "setdivplayers" : "Save new division details"
    }
    divs = [ ["Sleve McDichael", "Kevin Nogilny"],
             ["Darryl Archideld", "Todd Bonzalez"],
             ["Bobson Dugnutt", "Willie Dustice"] ]
    for (div_index, div) in enumerate(divs):
        for player_name in div:
            input_name = "player%d_div" % (tourney.get_player_from_name(player_name).get_id())
            params[input_name] = str(div_index)
    make_request("divsetup", tourney_name, [], params)

    # Check the players are in the right divisions
    for (div_index, div) in enumerate(divs):
        for player_name in div:
            assert_equal(tourney.get_player_from_name(player_name).get_division(), div_index, player_name)

    # Check the division names are correct
    for (div_index, div_name) in enumerate([ "Apple", "Banana", "Cherry" ]):
        assert_equal(tourney.get_division_name(div_index), div_name)

    # Now undo all this and put everyone in the same division again.
    make_request("divsetup", tourney_name, [], {
        "setdivcount" : "Set number of divisions",
        "divcount" : "1"
    })

    # Check everyone's in division 0
    assert_equal(tourney.get_num_divisions(), 1)
    for div in divs:
        for name in div:
            assert_equal(tourney.get_player_from_name(name).get_division(), 0, name)

def make_fixture_edit_params_from_games(games):
    params = {}
    for g in games:
        round_no = g.get_round_no()
        seq = g.get_round_seq()
        p = g.get_players()
        params["gamep1_%d_%d" % (round_no, seq)] = p[0].get_name()
        params["gamep2_%d_%d" % (round_no, seq)] = p[1].get_name()
        params["gametype_%d_%d" % (round_no, seq)] = g.get_game_type()
    return params

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

    division_diversion(tourney)

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

    # Assign teams to the players
    teams = tourney.get_teams()
    name_to_id = {}
    for p in tourney.get_players():
        name_to_id[p.get_name()] = p.get_id()

    params = {
            "playerteamsubmit" : "Submit"
    }
    for (pname, team_index) in [
            ("Sleve McDichael", 0), ("Mike Truk", 1),
            ("Darryl Archideld", 0), ("Kevin Nogilny", 0),
            ("Willie Dustice", 0), ("Todd Bonzalez", 1),
            ("Bobson Dugnutt", 1) ]:
        params["player%d" % (name_to_id[pname])] = teams[team_index].get_id()
    make_request("teamsetup", tourney_name, [], params)

    # Team scores should be 1-0 to teams[0]
    team_scores = tourney.get_team_scores()
    for (team, score) in team_scores:
        if team.get_id() == teams[0].get_id():
            assert_equal(score, 1)
        elif team.get_id() == teams[1].get_id():
            assert_equal(score, 0)
        else:
            print("Unexpected team_id: %d" % (team.get_id()), file=sys.stderr)
            assert_equal(1, 0)

    # Clear team assignments
    make_request("teamsetup", tourney_name, [], { "clearteams" : "Clear Teams" })

    # Team scores should now be 0-0
    team_scores = tourney.get_team_scores()
    for (team_id, score) in team_scores:
        assert_equal(score, 0)


    # Test player.py. Withdraw Bobson Dugnutt...
    make_request("player", tourney_name, [ str(name_to_id["Bobson Dugnutt"]) ], { "withdrawplayer" : "Withdraw Bobson Dugnutt" })

    # Add Onson Sweemey
    make_request("player", tourney_name, [], {
        "newplayersubmit" : "Create Player",
        "setname" : "Onson Sweemey",
        "setrating" : "1000",
        "setdivision" : "0",
        "setwithdrawn" : "0",
        "setavoidprune" : "0",
        "setrequiresaccessibletable" : "0",
        "setpreferredtable" : "1", # Let's say Onson prefers table 1
        "setnewbie" : "1" # and is a newbie
    })

    # Add Jeromy Gride
    make_request("player", tourney_name, [], {
        "newplayersubmit" : "Create Player",
        "setname" : "Jeromy Gride",
        "setrating" : "1150",
        "setdivision" : "0",
        "setwithdrawn" : "0",
        "setavoidprune" : "1",
        "setrequiresaccessibletable" : "0",
        "setpreferredtable" : None,
        "setnewbie" : "0"
    })

    # Check players
    for p in tourney.get_players():
        name = p.get_name()
        if name == "Onson Sweemey":
            assert_equal(p.get_preferred_table(), 1)
            assert_equal(p.is_newbie(), True)
            name_to_id[name] = p.get_id()
        elif name == "Jeromy Gride":
            assert_equal(p.is_avoiding_prune(), True)
            assert_equal(p.get_preferred_table(), None)
            assert_equal(p.is_newbie(), False)
            assert_equal(p.get_rating(), 1150)
            name_to_id[name] = p.get_id()
        elif name == "Bobson Dugnutt":
            assert_equal(p.is_withdrawn(), True)

    assert_equal("Onson Sweemey" in name_to_id, True)
    assert_equal("Jeromy Gride" in name_to_id, True)

    # Reinstate Bobson Dugnutt
    make_request("player", tourney_name, [ str(name_to_id["Bobson Dugnutt"]) ], { "reinstateplayer" : "Reinstate Bobson Dugnutt" })
    p = tourney.get_player_from_name("Bobson Dugnutt")
    assert_equal(p.is_withdrawn(), False)

    tourney.close()

    # Round 2
    tourney = countdowntourney.tourney_open(tourney_name)
    add_fixtures(tourney, 2, [
        (1, "Sleve McDichael", "Darryl Archideld"),
        (2, "Kevin Nogilny", "Willie Dustice"),
        (3, "Pruney McPruneface", "Todd Bonzalez"),
        (4, "Bobson Dugnutt", "Mike Truk")
    ])

    games = tourney.get_games(round_no=2)
    assert_equal(len(games), 4)

    # Test fixtureedit.py.
    # Delete the Pruney game. This is seq=3 in this round - within a round,
    # game sequence numbers are automatically numbered from 1.
    params = make_fixture_edit_params_from_games(games)
    params["save"] = "Save Changes"
    params["deletegame_2_3"] = "1"
    make_request("fixtureedit", tourney_name, [ "2" ], params)

    games = tourney.get_games(round_no=2)
    assert_equal(len(games), 3)

    # Add a game between Onson Sweemey and Jeromy Gride (seq = 5)
    params = make_fixture_edit_params_from_games(games)
    params["save"] = "Save Changes"
    params["addgame_div0"] = "1"
    params["addgame_p1_div0"] = "Onson Sweemey"
    params["addgame_p2_div0"] = "Jeromy Gride"
    params["addgame_type_div0"] = "P"
    params["addgame_table_div0"] = "3"
    make_request("fixtureedit", tourney_name, [ "2" ], params)

    games = tourney.get_games(round_no=2)
    assert_equal(len(games), 4)

    # Add a game between Todd Bonzalez and Prune (seq = 6)
    params = make_fixture_edit_params_from_games(games)
    params["save"] = "Save Changes"
    params["addgame_div0"] = "1"
    params["addgame_p1_div0"] = "Todd Bonzalez"
    params["addgame_p2_div0"] = "Pruney McPruneface"
    params["addgame_type_div0"] = "P"
    params["addgame_table_div0"] = "5"
    make_request("fixtureedit", tourney_name, [ "2" ], params)

    games = tourney.get_games(round_no=2)
    assert_equal(len(games), 5)

    # Change our mind - we want Onson Sweemey to play Prune, and Jeromy Gride
    # to play Todd Bonzalez
    params = make_fixture_edit_params_from_games(games)
    params["save"] = "Save Changes"
    params["gamep1_2_5"] = "Onson Sweemey"
    params["gamep2_2_5"] = "Pruney McPruneface"
    params["gamep1_2_6"] = "Jeromy Gride"
    params["gamep2_2_6"] = "Todd Bonzalez"
    make_request("fixtureedit", tourney_name, [ "2" ], params)

    # Fetch the edited list of games, order by table number
    games = tourney.get_games(round_no=2)
    assert_equal(len(games), 5)
    games.sort(key=lambda x : x.get_table_no())
    expected_games = [
            # table number, p1, p2
            (1, "Sleve McDichael", "Darryl Archideld"),
            (2, "Kevin Nogilny", "Willie Dustice"),
            (3, "Onson Sweemey", "Pruney McPruneface"),
            (4, "Bobson Dugnutt", "Mike Truk"),
            (5, "Jeromy Gride", "Todd Bonzalez")
    ]

    # Check the games are as expected
    for gi in range(len(games)):
        g = games[gi]
        p = g.get_players()
        e = expected_games[gi]
        assert_equal(p[0].get_name(), e[1])
        assert_equal(p[1].get_name(), e[2])
        assert_equal(g.get_table_no(), e[0])
        assert_equal(g.get_game_type(), "P")

    # Post round 2 results
    post_result(tourney, 2, "Sleve McDichael", 75, "Darryl Archideld", 49)
    post_result(tourney, 2, "Kevin Nogilny", 41, "Willie Dustice", 47)
    post_result(tourney, 2, "Onson Sweemey", 59, "Pruney McPruneface", 0)
    post_result(tourney, 2, "Bobson Dugnutt", 69, "Mike Truk", 30)
    post_result(tourney, 2, "Jeromy Gride", 43, "Todd Bonzalez", 56)

    # Check that all games are complete
    games = tourney.get_games(round_no=2)
    for g in games:
        assert_equal(g.is_complete(), True)

    # Standings table should look like this:
    expected_standings = [
            # position, name, played, wins, points
            (1, "Sleve McDichael",  2, 2, 135),
            (2, "Willie Dustice",   2, 2, 116),
            (3, "Todd Bonzalez",    2, 2, 111),
            (4, "Bobson Dugnutt",   2, 1, 124),
            (5, "Kevin Nogilny",    2, 1, 113),
            (6, "Onson Sweemey",    1, 1,  59),
            (7, "Darryl Archideld", 2, 0,  93),
            (8, "Mike Truk",        2, 0,  80),
            (9, "Jeromy Gride",     1, 0,  43),
    ]

    # Check standings table is correct
    standings = tourney.get_standings()
    assert_equal(len(standings), len(expected_standings))
    for i in range(len(standings)):
        so = standings[i]
        se = expected_standings[i]
        context = "standings[%d], name %s" % (i, se[1])
        assert_equal(so.position, se[0], context)
        assert_equal(so.name, se[1], context)
        assert_equal(so.played, se[2], context)
        assert_equal(so.wins, se[3], context)
        assert_equal(so.points, se[4], context)

    tourney.close()

if __name__ == "__main__":
    main()
