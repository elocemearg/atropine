#!/usr/bin/python3

# Test the Swiss Army Blunderbuss fixture generator (swissN.py) and make
# sure it comes up with some reasonable fixtures.

import sys
import os

sys.path.append("py")

import countdowntourney
import swissN
import swissNtest
import json

DEFAULT_LIMIT_MS = 30000
#swissN.ENABLE_PENALTY_CAP_OPTIMISATION = False
#swissN.ENABLE_RESULTS_CACHE_OPTIMISATION = False

def test_scenario(scenario_file):
    with open(scenario_file) as f:
        scenario = json.load(f)

    # scenario["players"] is a list of [name, rating] pairs.
    players = []
    for p in scenario["players"]:
        players.append(countdowntourney.Player(p[0], p[1]))

    name_to_player = {}
    for p in players:
        name_to_player[p.get_name()] = p

    already_played_names = set()

    # scenario["games"] is a list of:
    # [ round, table, division, p1, score1, p2, score2, tiebreak ]
    games = []
    round_seq_max = {}
    for g in scenario["games"]:
        round_no = g[0]
        table_no = g[1]
        division = g[2]
        name1 = g[3]
        score1 = g[4]
        name2 = g[5]
        score2 = g[6]
        tiebreak = g[7]
        p1 = name_to_player[name1]
        p2 = name_to_player[name2]
        round_seq = round_seq_max.get(round_no, 0) + 1
        cdgame = countdowntourney.Game(round_no, round_seq, table_no, division, 'P', p1, p2)
        cdgame.set_score(score1, score2, tiebreak)
        already_played_names.add((name1, name2))
        already_played_names.add((name2, name1))
        games.append(cdgame)

    # Calculate the standings table, given the games played so far. Some of
    # these players might not be in the round we're generating - these will
    # be listed in test["withdrawn"].
    standings = swissNtest.calculate_standings(games, players)
    name_to_wins = {}
    name_to_pos = {}
    for s in standings:
        name_to_wins[s.name] = s.wins + s.draws * 0.5
        name_to_pos[s.name] = s.position

    test = scenario["test"]
    withdrawn_players = test.get("withdrawn", [])

    # Active players: the players we want the fixture generator to include
    # in the round we're about to ask it to generate.
    active_players = [ p for p in players if p.get_name() not in withdrawn_players ]
    group_size = test["group_size"]
    init_max_win_diff = test.get("init_max_win_diff", 2)
    limit_ms = test.get("limit_ms", DEFAULT_LIMIT_MS)

    # Call the business end of the swissN fixture generator
    (weight, groups) = swissN.swissN(games, active_players, standings,
            group_size, rank_by_wins=True, limit_ms=limit_ms,
            init_max_win_diff=init_max_win_diff);

    if not groups:
        print("Unable to find any acceptable groupings in the time limit.")
        return False

    exp_max_win_diff = test.get("exp_max_win_diff", None)
    exp_max_pos_diff = test.get("exp_max_pos_diff", None)
    exp_rematches = test.get("exp_rematches", 0)
    exp_max_penalty = test.get("exp_max_penalty", None)

    # Sanity check that every player we passed to swissN() appears exactly once.
    unseen_players = set([p.get_name() for p in active_players])
    for g in groups:
        for p in g:
            if p.get_name() not in unseen_players:
                print("Player \"%s\" appears twice in the output!" % (p.get_name()))
                return False
            unseen_players.remove(p.get_name())
    if unseen_players:
        print("The following players have not been given a group:")
        print(", ".join(unseen_players))
        return False

    # Check the max win difference, max position difference, and total number
    # of rematches in all the fixtures suggested by swissN().
    num_rematches = 0
    max_win_diff = 0
    max_pos_diff = 0
    for g in groups:
        for (pi1, p1) in enumerate(g):
            for pi2 in range(pi1 + 1, len(g)):
                p2 = g[pi2]
                if (p1.get_name(), p2.get_name()) in already_played_names:
                    num_rematches += 1
                win_diff = abs(name_to_wins[p1.get_name()] - name_to_wins[p2.get_name()])
                pos_diff = abs(name_to_pos[p1.get_name()] - name_to_pos[p2.get_name()])
                max_win_diff = max(max_win_diff, win_diff)
                max_pos_diff = max(max_pos_diff, pos_diff)

    if exp_max_penalty is not None:
        if weight - exp_max_penalty >= 0.000001:
            print("Total penalty %f, expected <= %f" % (weight, exp_max_penalty))
            return False

    if exp_max_win_diff is not None:
        if max_win_diff > exp_max_win_diff:
            print("Max win difference %g, expected <= %g" % (max_win_diff, exp_max_win_diff))
            return False

    if exp_max_pos_diff is not None:
        if max_pos_diff > exp_max_pos_diff:
            print("Max position difference %d, expected <= %d" % (max_pos_diff, exp_max_pos_diff))
            return False

    if exp_rematches is not None:
        if num_rematches > exp_rematches:
            print("Rematches %d, expected <= %d" % (num_rematches, exp_rematches))
            return False

    return True

def main():
    # Get to a known place - the directory containing this script.
    os.chdir(os.path.dirname(os.path.abspath(__file__)));

    # Each scenario file contains a list of players and ratings, and a list
    # of already-played games. There is also an object "test" which can have
    # the following values:
    # {
    #     "test" : {
    #          (parameters for the test)
    #          "group_size" : (required: number of players per table)
    #          "limit_ms" : (max milliseconds to let swissN() run for)
    #
    #          (properties we require from the generated fixtures)
    #          "exp_max_win_diff" : (max permissible win difference on a table in the generated fixtures)
    #          "exp_max_pos_diff" : (max permissible position difference on a table in the generated fixtures)
    #          "exp_max_rematches" : (max rematches allowed, usually 0)
    #          "exp_max_penalty" : (max permissible weight, or penalty, for the set of fixtures generated)
    #          "withdrawn" : (list of player names which should not be given to the fixture generator]
    #     }
    # }

    scenario_files = [
            # COLIN 2022 after R2, we're generating R3.
            # Names anonymised.
            # This is known to fail if we disable the optimisations - it
            # doesn't find the best grouping in the time.
            "colin2022_after_r2.json",

            # 24 players including two Prunes, generate R3 after two rounds
            # of Lincoln style fixtures.
            "r3_22players_2prunes.json",

            # Generate R3 after two rounds (4 games each) in a larger event.
            "r3_45players.json",

            # Generate round 5 after 4 rounds of two-to-a-table.
            "r5_pairs.json"
    ]
    num_passed = 0
    num_failed = 0
    for scenario_file in scenario_files:
        filename = os.path.join("swisstestscenarios", scenario_file)
        test_name = scenario_file
        if '.' in test_name:
            test_name = test_name[0:(test_name.rindex("."))]
        print("Test %s..." % (test_name))
        result = test_scenario(filename)
        if result:
            print("%s passed." % (test_name))
            num_passed += 1
        else:
            print("%s FAILED." % (test_name))
            num_failed += 1
            break
    print("%d tests run, %d tests failed." % (num_passed + num_failed, num_failed))
    sys.exit(1 if num_failed > 0 else 0)

if __name__ == "__main__":
    main()
