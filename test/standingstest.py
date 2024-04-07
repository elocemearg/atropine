#!/usr/bin/python3

"""
Test that the countdowntourney.get_standings_from_round_onwards() and
countdowntourney.get_standings() functions behave as they should.
"""

import sys
import os
import random

# Test must be run from the directory above "test"
# i.e.
# ./test/tourneytest.py
sys.path.append(os.path.join(os.getcwd(), "py"))

import countdowntourney

from tourneytest import apply_scenario

class TestFailedException(Exception):
    pass

player_names = [
    "Aaron", "Abigail", "Alex", "Alice", "Barry", "Bert", "Bob", "Bort",
    "Cathy", "Cedric", "Charlie", "Colin", "Craig", "Cyril", "Dave", "Derek",
    "Donna", "Doug", "Edward", "Egbert", "Ethelred", "Eustace", "Eve", "Fay",
    "Felicity", "Frank", "Fred", "Gavin", "George", "Grace", "Grant", "Hannah",
    "Harry", "Henry", "Horace", "Hubert", "Ian", "Ingrid", "Ivan", "James",
    "Jerry", "John", "Joseph", "Joshua", "Juliet", "Kate", "Keith", "Kerry",
    "Kevin", "Larry", "Laura", "Lewis", "Linda", "Mark", "Margaret", "Marie",
    "Marvin", "Maurice", "Mel", "Mike", "Molly", "Nancy", "Neil", "Nick",
    "Nigel", "Norman", "Oliver", "Oscar", "Pam", "Pat", "Paul", "Peter",
    "Philip", "Quentin", "Ralph", "Ray", "Richard", "Robert", "Robin", "Ronald",
    "Ruby", "Russell", "Sally", "Sarah", "Sean", "Simon", "Stacey", "Steve",
    "Terry", "Tim", "Tom", "Tony", "Trevor", "Ursula", "Val", "Vanessa",
    "Victoria", "Wally", "Wilfred", "Will", "Xavier", "Yvonne", "Zack", "Zoe"
]

scenarios = [
    {
        "name" : "perroundstandings",
        "full_name" : "CoFlompsbury",
        "venue" : "Flompsbury Village Hall",
        "date" : [ 2024, 4, 7 ],
        "num_rounds" : 3,
        "num_divisions" : 1,
        "init_num_players" : 15,
    },
    {
        "name" : "perroundstandingsdiv",
        "full_name" : "CoDivisioned",
        "venue" : "Divisional Pub Function Room",
        "date" : [ 2024, 4, 7 ],
        "num_rounds" : 4,
        "num_divisions" : 2,
        "init_num_players" : 31
    },
    {
        "name" : "perroundstandingsbig",
        "full_name" : "CoPopulous",
        "venue" : "Massive Arena",
        "date" : [ 2024, 4, 7 ],
        "num_rounds" : 5,
        "num_divisions" : 3,
        "init_num_players" : 100
    }
]

def get_player_name(index):
    if index >= len(player_names):
        return "Player %d" % (index + 1)
    else:
        return player_names[index]

def random_score_from_rating(rating):
    if rating == 0:
        return 0
    else:
        return max(int(random.normalvariate(45 * rating / 1500.0, 12)), 0)

def set_random_score(game, rating1, rating2):
    s1 = random_score_from_rating(rating1)
    s2 = random_score_from_rating(rating2)
    tb = False
    if s1 == s2:
        if random.random() < 0.5:
            s1 += 10
        else:
            s2 += 10
        tb = True
    game.set_score(s1, s2, tb)

def random_rating():
    return 1000 + random.random() * 1000

def round_standings_add(round_standings, player_name, field, increment):
    if player_name not in round_standings:
        round_standings[player_name] = {}
    player_stats = round_standings[player_name]
    player_stats[field] = player_stats.get(field, 0) + increment

def check_standings_field(expected_standings, starting_round, latest_round_no, player_name, field_name, observed_value, context):
    expected_value = 0
    if starting_round <= 0:
        starting_round = 1
    for r in range(starting_round, latest_round_no + 1):
        round_standings = expected_standings.get(r, {})
        player_stats = round_standings.get(player_name, {})
        expected_value += player_stats.get(field_name, 0)

    if expected_value != observed_value:
        print("check_standings_field() failed. Rounds %d-%d, player \"%s\", field \"%s\", expected %d, observed %d." % (starting_round, latest_round_no, player_name, field_name, expected_value, observed_value))
        print("Context: %s" % (context))
        raise TestFailedException()
    return True

def check_standings(tourney, division, played_games, latest_round_no):
    players = tourney.get_players_from_division(division)

    # Calculate the expected standings table for each round between 1 and latest_round_no
    # { round_no -> { name -> { <standings field> -> number } } }
    expected_standings = {}

    for game in played_games:
        round_no = game.get_round_no()
        if round_no not in expected_standings:
            expected_standings[round_no] = {}
        expected_round_standings = expected_standings[round_no]
        names = game.get_player_names()

        score = game.get_score()
        for pi in (0, 1):
            round_standings_add(expected_round_standings, names[pi], "played", 1)
            round_standings_add(expected_round_standings, names[pi], "wins", 1 if score[pi] > score[pi ^ 1] else 0)
            round_standings_add(expected_round_standings, names[pi], "draws", 1 if game.is_draw() else 0)
            # score is the game score, points is the number of points the
            # player will be credited with in the standings
            if game.is_tiebreak():
                points = (min(score), min(score))
            else:
                points = score
            round_standings_add(expected_round_standings, names[pi], "points", points[pi])
            round_standings_add(expected_round_standings, names[pi], "spread", points[pi] - points[pi ^ 1])
        round_standings_add(expected_round_standings, names[0], "playedfirst", 1)

    # Now ask the tourney what the standings are for each subsequence of rounds,
    # starting with [latest_round_no], then
    # [latest_round_no - 1, latest_round_no], etc.
    for starting_round in range(latest_round_no, -1, -1):
        if starting_round == 0:
            # Test the get_standings() function as well
            observed_standings = tourney.get_standings(division=division, calculate_qualification=False, rank_finals=False)
        else:
            observed_standings = tourney.get_standings_from_round_onwards(division, starting_round)

        # Make sure we have a standings row for every player in this division,
        # including the withdrawn players, and that we have no other rows.
        observed_name_list = sorted([ s.name for s in observed_standings ])
        expected_name_list = sorted([ p.get_name() for p in players ])
        if observed_name_list != expected_name_list:
            print("get_standings_from_round_onwards() returned incorrect player list.")
            print("Expected: " + str(expected_name_list))
            print("Observed: " + str(observed_name_list))
            raise TestFailedException()

        if starting_round < 0:
            context = "get_standings(division=%d), latest_round_no=%d" % (division, latest_round_no)
        else:
            context = "get_standings_from_round_onwards(division=%d, starting_round=%d), latest_round_no %d" % (division, starting_round, latest_round_no)
        for row in observed_standings:
            name = row.name
            check_standings_field(expected_standings, starting_round, latest_round_no, name, "played", row.played, context)
            check_standings_field(expected_standings, starting_round, latest_round_no, name, "wins", row.wins, context)
            check_standings_field(expected_standings, starting_round, latest_round_no, name, "draws", row.draws, context)
            check_standings_field(expected_standings, starting_round, latest_round_no, name, "points", row.points, context)
            check_standings_field(expected_standings, starting_round, latest_round_no, name, "spread", row.spread, context)
            check_standings_field(expected_standings, starting_round, latest_round_no, name, "playedfirst", row.played_first, context)
        #print("Checked %d standings rows" % (len(observed_standings)))

    # If we get here, get_standings() and get_standings_from_round_onwards() passed the test.

    return True


def test_scenario(test_name, scenario, verbose):
    # Create a new tourney and set up its initial details.
    tourney_name = "_" + test_name
    tourney_file = os.path.join("tourneys", "%s.db" % (tourney_name))
    if os.path.exists(tourney_file):
        os.unlink(tourney_file)
    tourney = countdowntourney.tourney_create(tourney_name, "tourneys")
    tourney.close()
    tourney = countdowntourney.tourney_open(tourney_name, "tourneys")

    if "full_name" in scenario:
        tourney.set_full_name(scenario["full_name"])
    if "venue" in scenario:
        tourney.set_venue(scenario["venue"])
    if "date" in scenario:
        tourney.set_event_date(scenario["date"][0], scenario["date"][1], scenario["date"][2])

    # Create players with random ratings.
    entered_players = [
        countdowntourney.EnteredPlayer(get_player_name(i), random_rating(),
            i * scenario["num_divisions"] // scenario["init_num_players"]) for i in range(scenario["init_num_players"])
    ]
    tourney.set_players(entered_players, auto_rating_behaviour=countdowntourney.RATINGS_MANUAL)

    # next_player_index: the index of the next name in player_names we should
    # use for any players we might subsequently add during the tourney.
    next_player_index = scenario["init_num_players"]

    print("Test: %s" % (test_name))
    print("Tourney %s created with %d players in %d divisions." % (tourney_name, len(entered_players), scenario["num_divisions"]))
    print("Running test with %d rounds..." % (scenario["num_rounds"]))

    played_games = []
    for rnd_index in range(scenario["num_rounds"]):
        round_no = rnd_index + 1

        # Start a round
        if verbose:
            print("Round %d" % (round_no))
        tourney.name_round(round_no, "Round %d" % (round_no))

        if round_no > 1:
            # Withdraw 0 or 1 players, then add at least that many players
            num_players_withdrawn = 0
            if random.random() < 0.5:
                withdrawn_player = random.choice(tourney.get_active_players())
                tourney.withdraw_player(withdrawn_player.get_name())
                num_players_withdrawn = 1
                if verbose:
                    print("Withdrew %s" % (withdrawn_player.get_name()))
            num_players_added = random.randint(num_players_withdrawn, 2)
            for i in range(num_players_added):
                new_player_name = get_player_name(next_player_index)
                new_player_division = random.randint(0, scenario["num_divisions"] - 1)
                tourney.add_player(new_player_name, random_rating(), division=new_player_division)
                if verbose:
                    print("Added %s to division %d" % (new_player_name, new_player_division))
                next_player_index += 1

        game_seq_within_round = 0
        last_used_table_number = 0
        # For each division, generate fixtures for this round.
        for div_index in range(scenario["num_divisions"]):
            # Generate random fixtures: we don't care about repeats.
            players = [ p for p in tourney.get_players_from_division(div_index) if not p.is_withdrawn() ]
            random.shuffle(players)
            tables = [ [] for x in range((len(players) + 2) // 3) ]
            fixtures = []
            pi = 0
            for x in range(3):
                for t in range(len(tables)):
                    if pi >= len(players):
                        p = tourney.get_auto_prune()
                    else:
                        p = players[pi]
                    tables[t].append(p)
                    pi += 1

            for (table_index, table) in enumerate(tables):
                for (i1, i2) in [ (0, 1), (1, 2), (2, 0) ]:
                    fixtures.append(countdowntourney.Game(round_no, game_seq_within_round, last_used_table_number + 1, div_index, "P", table[i1], table[i2]))
                    game_seq_within_round += 1
                last_used_table_number += 1
            tourney.merge_games(fixtures)

        # Check the per-round standings for each division, before games are played
        for div_index in range(scenario["num_divisions"]):
            check_standings(tourney, div_index, played_games, round_no)
        if verbose:
            print("Round %d: per-round standings correct before games played" % (round_no))

        # Now add random scores for the games. Scores are loosely based on the
        # players' randomly-assigned ratings.
        games_played_this_round = 0
        for div_index in range(scenario["num_divisions"]):
            games = tourney.get_games(round_no=round_no, division=div_index, game_type="P")
            for g in games:
                game_players = g.get_players()
                set_random_score(g, game_players[0].get_rating(), game_players[1].get_rating())
                played_games.append(g)
                games_played_this_round += 1
            tourney.merge_games(games)

        # Now check the per-round standings for each division again.
        for div_index in range(scenario["num_divisions"]):
            check_standings(tourney, div_index, played_games, round_no)
        if verbose:
            print("Round %d: per-round standings correct after %d games played in this round" % (round_no, games_played_this_round))

    tourney.close()
    print("Passed.")
    print("")
    return True

def main():
    verbose = ("-v" in sys.argv[1:])

    try:
        for scenario in scenarios:
            scenario_name = scenario["name"]
            if not test_scenario(scenario_name, scenario, verbose):
                sys.exit(1)
    except TestFailedException:
        print("Test failed. See diagnostic output above.")
        sys.exit(1)

    print("All %d test scenarios passed." % (len(scenarios)))
    sys.exit(0)

if __name__ == "__main__":
    main()
