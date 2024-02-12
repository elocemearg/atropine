#!/usr/bin/python3

"""
randomfixgentest - test the Random and Random from Seeded Pots generators

Test that the random fixture generators generate fixtures subject to certain
constraints, such as avoiding all-newbie tables and avoiding rematches.
"""

import sys
import os

sys.path.append("py")
sys.path.append("generators")
sys.path.append(os.path.join("webroot", "cgi-bin"))

import countdowntourney
import fixgen_random
import fixgen_random_seeded

tests = [
    {
        "name" : "No all-newbie tables",
        "dbname" : "_randomtest1",
        "players" : [
            # Players whose name contains the string "Newbie" are automatically
            # set as newbies by main()
            "Alan", "Brian Newbie", "Catherine", "David", "Edward Newbie", "Fred Newbie", "Greg Newbie", "Hannah",
        ],
        "tablesize" : 3,
        "avoidallnewbietables" : True
    },
    {
        "name" : "No all-newbie tables, with five non-newbies and ten newbies",
        "dbname" : "_randomtest2",
        "players" : [
            "Alan", "Brian Newbie", "Catherine", "David", "Edward Newbie", "Fred Newbie", "Greg Newbie", "Hannah", "Ian Newbie", "Julie Newbie", "Ken Newbie", "Larry", "Mike Newbie", "Nancy Newbie", "Oscar Newbie"
        ],
        "tablesize" : 3,
        "avoidallnewbietables" : True,
        "avoidrematches" : False,
    },
    {
        "name" : "No all-newbie tables, two players per table, half newbies",
        "dbname" : "_randomtest3",
        "players" : [
            "Alan", "Brian Newbie", "Catherine", "David", "Edward Newbie", "Fred Newbie", "Greg Newbie", "Hannah", "Ian Newbie", "Julie", "Ken"
        ],
        "tablesize" : 2,
        "avoidallnewbietables" : True
    },
    {
        "name" : "All-newbie tables allowed, more newbies than non-newbies",
        "dbname" : "_randomtest4",
        "players" : [
            "Alan", "Brian Newbie", "Catherine", "David", "Edward Newbie", "Fred Newbie", "Greg Newbie", "Hannah", "Ian Newbie", "Julie Newbie", "Ken Newbie"
        ],
        "tablesize" : 2,
        "avoidallnewbietables" : False
    },
    {
        "name" : "Two divisions, random draw in each, no all-newbie tables",
        "dbname" : "_randomtest5",
        "players" : [
            [ "Alan", "Brian Newbie", "Catherine", "David", "Edward Newbie", "Fred Newbie", "Greg", "Hannah", "Ian Newbie", "Julie Newbie", "Ken Newbie" ],
            [ "Larry", "Mike Newbie", "Nancy", "Oscar", "Peter Newbie", "Quentin Newbie", "Robert Newbie", "Steve", "Thomas", "Ursula", "Victor Newbie" ]
        ],
        "tablesize" : 3,
        "avoidallnewbietables" : True
    },
    {
        "name" : "Round 2, avoid rematches",
        "dbname" : "_randomtest6",
        "players" : [
            [
                "Alan", "Brian Newbie", "Catherine", "David", "Edward Newbie", "Fred Newbie", "Greg", "Hannah", "Ian", "Julie", "Ken Newbie"
            ],
        ],
        # Say that in round 1, the tables were ABC, DEF, GHI, JKP.
        # "results" is a list of rounds. Each round is a list of results, and
        # each result is a tuple:
        #     (div_index, table_no, name1, score1, name2, score2).
        "results" : [
            [
                (0, 1, "Alan", 30, "Brian Newbie", 45),
                (0, 1, "Brian Newbie", 51, "Catherine", 70),
                (0, 1, "Catherine", 54, "Alan", 44),
                (0, 2, "David", 52, "Edward Newbie", 32),
                (0, 2, "Edward Newbie", 40, "Fred Newbie", 47),
                (0, 2, "Fred Newbie", 63, "David", 57),
                (0, 3, "Greg", 66, "Hannah", 54),
                (0, 3, "Hannah", 49, "Ian", 43),
                (0, 3, "Ian", 58, "Greg", 37),
                (0, 4, "Julie", 64, "Ken Newbie", 28),
                (0, 4, "Ken Newbie", 67, "Prune", 0),
                (0, 4, "Prune", 0, "Julie", 70)
            ]
        ],
        "avoidallnewbietables" : False,
        "avoidrematches" : True,
        "tablesize" : 3
    },
    {
        "name" : "Round 3, avoid rematches, only one combination possible",
        "dbname" : "_randomtest7",
        "players" : [
            [ "Alan", "Brian", "Catherine", "David" ]
        ],
        "results" : [
            [
                (0, 1, "Alan", 50, "Brian", 60),
                (0, 2, "Catherine", 48, "David", 66)
            ],
            [
                (0, 1, "Alan", 40, "Catherine", 60),
                (0, 2, "Brian", 96, "David", 77),
            ]
        ],
        "avoidrematches" : True,
        "tablesize" : 2,
        "expectedgroups" : [
            [
                [ "Alan", "David" ], [ "Brian", "Catherine" ]
            ]
        ]
    },
]

randomness_tests = [
    # Randomness test 1.
    #
    # We'll run the random fixture generator a large number of times, and check
    # the valid possible outcomes appear a roughly equal number of times.
    #
    # Let's count the number of combinations, ignoring order of tables or order
    # of players within a table.
    #
    # Three of Alan, Catherine, David and Hannah must be on different tables.
    # The potential positions of the non-newbies are:
    #   AC, D, H
    #   AD, C, H
    #   AH, C, D
    #   CD, A, H
    #   CH, A, D
    #   DH, A, C
    #   (6 combinations)
    #
    # Assume the two non-newbies are on the leftmost table.
    # For each of the six possibilities above, the remaining five newbies can
    # be in the following configurations:
    # Six combinations with B on the first table:
    #   B, EF, GI
    #   B, EG, FI
    #   B, EI, FG
    #   B, GI, EF
    #   B, FI, EG
    #   B, FG, EI
    # (B, EF, GI) is different from (B, GI, EF) because GI and EF are put with
    # different non-newbies.
    # Similarly, there are 6 combinations with E on the first table, 6 with F
    # on the first table, 6 with G on the first table and 6 with I on the first
    # table, totalling 30 combinations.
    #
    # 30 * 6 = 180 possible combinations for these 9 players on 3 tables of 3.

    {
        "name" : "Randomness test 1",
        "dbname" : "_randomnesstest1",
        "players" : [
            "Alan", "Brian Newbie", "Catherine", "David", "Edward Newbie", "Fred Newbie", "Greg Newbie", "Hannah", "Ian Newbie"
        ],
        "avoidallnewbietables" : True,
        "num_combinations" : 180,
        "tablesize" : 3,
        "fixgen" : fixgen_random
    },

    # Randomness test 2.
    #
    # We use the seeded fixture generator this time, with the same players and
    # newbie statuses as in the previous test. The set of valid outputs from
    # this test is therefore a subset of the valid outputs of the previous test.
    #
    # Alan, Brian and Catherine are in pot A, so they can't be on the same
    # table. This means the valid placings of non-newbies are:
    #   AD, C, H
    #   AH, C, D
    #   CD, A, H
    #   CH, A, D
    #   DH, A, C
    #
    # Taking each of these in turn, let's enumerate the combinations of the
    # newbies. Pot A is A,B,C, pot B is D,E,F, pot C is G,H,I.
    #   AD-  C--  --H
    #     G   EI  BF
    #     G   FI  BE
    #     I   EG  BF
    #     I   FG  BE
    #
    #   A-H  C--  -D-
    #    E    FG  B I
    #    E    FI  B G
    #    F    EG  B I
    #    F    EI  B G
    #
    #   CD-  A--  --H
    #     G   EI  BF
    #     G   FI  BE
    #     I   EG  BF
    #     I   FG  BE
    #
    #   C-H  A--  -D-
    #    E    FG  B I
    #    E    FI  B G
    #    F    EG  B I
    #    F    EI  B G
    #
    #   -DH  A--  C--
    #   B     EG   FI
    #   B     EI   FG
    #   B     FG   EI
    #   B     FI   EG
    #
    # Each of the five non-newbie combinations has four possibilities for the
    # non-newbies, which gives 20 acceptable combinations in total.
    {
        "name" : "Randomess test 2",
        "dbname" : "_randomnesstest2",
        "players" : [
            "Alan", "Brian Newbie", "Catherine", "David", "Edward Newbie", "Fred Newbie", "Greg Newbie", "Hannah", "Ian Newbie"
        ],
        "avoidallnewbietables" : True,
        "num_combinations" : 20,
        "tablesize" : 3,
        "fixgen" : fixgen_random_seeded
    }
]

def setup_tourney(test):
    # Create a tourney, first removing any existing tourney by this name
    tourney_db_dir = os.path.join("..", "tourneys")

    dbname = test["dbname"]
    table_size = test["tablesize"]

    db_path = os.path.join(tourney_db_dir, dbname + ".db")
    if os.path.exists(db_path):
        os.unlink(db_path)

    tourney = countdowntourney.tourney_create(dbname, tourney_db_dir)

    # Add our list of players
    entered_players = []
    # If test["players"] is a list of strings, then there's only one
    # division. Otherwise it's expected to be a list of lists of strings.
    if type(test["players"][0]) == str:
        div_players = [ test["players"] ]
    else:
        div_players = test["players"]

    for (div_index, players) in enumerate(div_players):
        for name in players:
            entered_players.append(countdowntourney.EnteredPlayer(name, None, division=div_index))
    tourney.set_players(entered_players, auto_rating_behaviour=countdowntourney.RATINGS_GRADUATED)

    # Set players' newbie status
    for ep in entered_players:
        if ep.get_name().find("Newbie") != -1:
            tourney.set_player_newbie(ep.get_name(), True)

    players_by_name = {}
    for p in tourney.get_players(include_prune=True):
        players_by_name[p.get_name()] = p

    # Add any already-played results
    current_round_no = 1
    existing_games = []
    for round_results in test.get("results", []):
        for (round_seq, result) in enumerate(round_results):
            (div_index, table_no, name1, score1, name2, score2) = result
            g = countdowntourney.Game(current_round_no, round_seq, table_no,
                            div_index, "P", players_by_name[name1],
                            players_by_name[name2], score1, score2)
            existing_games.append(g)
        current_round_no += 1
    if existing_games:
        tourney.merge_games(existing_games)

    # Read settings from the test definition...
    # The random fixture generator wants the "constraint" setting - it can
    # either avoid all-newbie tables or avoid rematches, but not both. The
    # random from seeded pots fixture generator doesn't have the facility
    # to avoid rematches but it looks for the "avoidallnewbietables" bool.
    avoid_all_newbie_tables = test.get("avoidallnewbietables", True)
    avoid_rematches = test.get("avoidrematches", False)
    settings = {}
    if avoid_all_newbie_tables:
        settings["constraint"] = "avoidallnewbietables"
        settings["avoidallnewbietables"] = "1"
    elif avoid_rematches:
        settings["constraint"] = "avoidrematches"
        settings["avoidrematches"] = "1"
    else:
        settings["constraint"] = "none"
    for (div_index, players) in enumerate(div_players):
        settings["d%d_groupsize" % div_index] = test["tablesize"]

    return (tourney, settings, div_players)

def is_one_from_each_pot(player_names, player_name_to_pot, num_pots):
    # Ensure each group has one player from each pot
    pots_present = [ False for i in range(num_pots) ]
    for name in player_names:
        pot = player_name_to_pot[name]
        if pots_present[pot]:
            return False
        pots_present[pot] = True
    if False in pots_present:
        return False
    return True

def main():
    # cd to the directory containing this script.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    num_failures = 0

    for (test_idx, test) in enumerate(tests):
        failed = False
        print("Test %d (%s)... " % (test_idx + 1, test["name"]), end="")
        (tourney, settings, div_players) = setup_tourney(test)
        table_size = test["tablesize"]
        current_round_no = len(test.get("results", [])) + 1

        # Player name to the pot they'd be placed in by the Random from Seeded
        # Pots generator, within their division.
        player_name_to_pot = {}

        div_rounds = {}
        div_info = {}
        for div_index in range(len(div_players)):
            # Work out how many tables, pots and players per pot we should have
            num_tables = (len(div_players[div_index]) + table_size - 1) // table_size
            num_pots = table_size
            pot_size = num_tables
            for (i, pname) in enumerate(div_players[div_index]):
                player_name_to_pot[pname] = i // pot_size
            player_name_to_pot["Prune"] = num_pots - 1

            div_rounds[div_index] = current_round_no

            div_info[div_index] = {
                    "num_tables" : num_tables,
                    "num_pots" : num_pots,
                    "pot_size" : pot_size
            }

        # Now call the fixture generators and check that we get something
        # that fits the requirements.
        for fg in [ fixgen_random, fixgen_random_seeded ]:
            generated_groups = fg.generate(tourney, settings, div_rounds)

            rounds = generated_groups.get_rounds()
            assert(len(rounds) == 1)
            div_groups = rounds[0].get_divisions()
            assert(len(div_groups) == len(div_info))

            # Check each division of returned results
            for div_index in div_info:
                num_pots = div_info[div_index]["num_pots"]
                pot_size = div_info[div_index]["pot_size"]
                num_tables = div_info[div_index]["num_tables"]
                groups = div_groups[div_index].get_groups()
                expected_groups = test.get("expected_groups", None)
                if expected_groups:
                    expected_groups = expected_groups[div_index]

                # Check that each group has the right number of players in it
                for g in groups:
                    if len(g) != table_size:
                        print("failed: group (%s) is not %d players." % (", ".join([p.get_name() for p in g]), table_size))
                        failed = True

                if expected_groups:
                    # A particular arrangement is expected. Check that what we
                    # have matches the expected output, but we don't care about
                    # order of the groups or order of players within the groups.
                    sorted_expected_groups = []
                    for group in expected_groups:
                        sorted_expected_groups.append(tuple(sorted(group)))
                    sorted_expected_groups = sorted(sorted_expected_groups)

                    sorted_groups = []
                    for group in groups:
                        sorted_groups.append(tuple(sorted([ p.get_name() for p in group ])))
                    sorted_groups = sorted(sorted_groups)

                    if len(sorted_groups) != len(sorted_expected_groups):
                        print("failed: expected %d groups, got %d" % (len(sorted_expected_groups), len(sorted_groups)))
                        failed = True
                    else:
                        for i in range(len(sorted_groups)):
                            if sorted_groups[i] != sorted_expected_groups[i]:
                                print("failed: expected group %s, got group %s" % (str(sorted_expected_groups[i]), str(sorted_groups[i])))
                                failed = True

                if test.get("avoidallnewbietables", False):
                    # Check that every group has at least one non-newbie,
                    # counting Prune as a newbie.
                    for group in groups:
                        for player in group:
                            if not player.is_newbie() and not player.is_prune():
                                break
                        else:
                            print("failed: group (%s) has no non-newbies in it." % (", ".join([p.get_name() for p in group])))
                            failed = True
                            break
                if fg == fixgen_random_seeded:
                    for group in groups:
                        if not is_one_from_each_pot([ p.get_name() for p in group ], player_name_to_pot, num_pots):
                            print("failed: group (%s) does not have a player from each pot." % (", ".join([p.get_name() for p in group])))
                            failed = True
                            break
        if failed:
            num_failures += 1
        else:
            print("passed.")

    # Randomness tests: run the random fixture generator a large number of times
    # and make sure we get all possible combinations roughly equally.
    print("Randomness tests. These will take some time...")
    for test in randomness_tests:
        test_idx += 1
        failed = False
        print("Test %d (%s)" % (test_idx + 1, test["name"]))
        (tourney, settings, div_players) = setup_tourney(test)

        num_trials_per_combination = 1000
        num_trials = test["num_combinations"] * num_trials_per_combination

        combination_freqs = {}
        fg = test["fixgen"]
        table_size = test["tablesize"]
        player_name_to_pot = {}
        if fg == fixgen_random_seeded:
            for players in div_players:
                pot_size = len(players) // table_size
                for (i, p) in enumerate(players):
                    player_name_to_pot[p] = i // pot_size

        for trial in range(num_trials):
            if trial % 1000 == 0:
                sys.stderr.write(" %6d/%d trials done...\r" % (trial, num_trials))
            generated_groups = fg.generate(tourney, settings, div_rounds)
            rounds = generated_groups.get_rounds()
            assert(len(rounds) == 1)
            div_groups = rounds[0].get_divisions()
            assert(len(div_groups) == 1)

            # Get a list of lists of names, rather than Player objects
            groups = div_groups[0].get_groups()
            player_name_groups = []
            # Sort each individual group by name, then sort the list of groups.
            for g in groups:
                player_name_groups.append(sorted([ p.get_name() for p in g ]))
            sorted_groups = sorted(player_name_groups)

            # Flatten the list of lists and convert it to a tuple.
            combination = []
            for g in sorted_groups:
                combination += g
            combination = tuple(combination)
            combination_freqs[combination] = combination_freqs.get(combination, 0) + 1
        sys.stderr.write(" %6d/%d trials done.  \n" % (num_trials, num_trials))

        # Check we got every valid combination, and nothing more
        if len(combination_freqs) != test["num_combinations"]:
            print("Failed: expected %d distinct combinations, got %d" % (test["num_combinations"], len(combination_freqs)))
            failed = True

        if not failed:
            # Check that the number of times we got each combination is
            # roughly equal. We'll arbitrarily allow the least
            # frequently-occuring combination to have a frequency no less than
            # two-thirds the expected frequency, and the most frequently
            # occuring combination to have a frequency no more than
            # four-thirds the expected frequency.
            tolerance = num_trials_per_combination // 3
            min_freq = min([ combination_freqs[c] for c in combination_freqs])
            max_freq = max([ combination_freqs[c] for c in combination_freqs])
            if min_freq < num_trials_per_combination - tolerance or max_freq > num_trials_per_combination + tolerance:
                print("Failed: min_freq %d, max_freq %d, expected to be within %d of %d" % (min_freq, max_freq, tolerance, num_trials_per_combination))
                failed = True

        if not failed:
            # Check that each distinct combination satisfies the requirements:
            # every table must have at least one non-newbie.
            for combination in combination_freqs:
                groups = []
                i = 0
                assert(len(combination) % table_size == 0)
                while i < len(combination):
                    groups.append(combination[i:(i+table_size)])
                    i += table_size
                for group in groups:
                    for pname in group:
                        if pname.find("Newbie") < 0:
                            break
                    else:
                        # No non-newbie on this table!
                        print("Failed: combination %s has an all-newbie table." % (str(combination)))
                        failed = True
                        break
                    if fg == fixgen_random_seeded:
                        # Ensure each group contains exactly one player from each pot.
                        if not is_one_from_each_pot(group, player_name_to_pot, table_size):
                            print("Failed: group %s does not have one player from each pot." % (", ".join(group)))
                            failed = True
                            break

        if failed:
            num_failures += 1
        else:
            print("Passed (got %d distinct combinations from %d trials, min_freq %d, max_freq %d)" % (len(combination_freqs), num_trials, min_freq, max_freq))

    if num_failures == 0:
        print("All tests passed.")
        sys.exit(0)
    else:
        print("%d tests failed." % (num_failures))
        sys.exit(1)

if __name__ == "__main__":
    main()
