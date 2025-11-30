#!/usr/bin/python3

"""
roundrobinfixgentest - test the Round Robin fixture generator

Test that the round robin fixture generator produces a match between every
possible pair of players, and that no player plays as P1 or P2 more than twice
in a row.
"""

import sys
import os

sys.path.append("py")
sys.path.append("generators")
sys.path.append(os.path.join("py", "dynamicpages"))

import countdowntourney
import fixgen_round_robin

tests = [
        {
            "name" : "Single division, 8 players",
            "dbname" : "_roundrobin1",
            "players" : [ "Alice", "Bob", "Charlie", "David", "Eve", "Fred", "Grace", "Harry" ]
        },
        {
            "name" : "Single division, 7 players",
            "dbname" : "_roundrobin2",
            "players" : [ "Alice", "Bob", "Charlie", "David", "Eve", "Fred", "Grace" ]
        },
        {
            "name" : "Two divisions, 8 players and 7 players",
            "dbname" : "_roundrobin3",
            "players" : [
                [ "Alice", "Bob", "Charlie", "David", "Eve", "Fred", "Grace", "Harry" ],
                [ "Ian", "Juliet", "Kate", "Larry", "Mike", "Neil", "Oscar" ]
            ]
        },
        {
            "name" : "Two divisions, 8 players and 16 players",
            "dbname" : "_roundrobin4",
            "players" : [
                [ "Alice", "Bob", "Charlie", "David", "Eve", "Fred", "Grace", "Harry" ],
                [ "Ian", "Juliet", "Kate", "Larry", "Mike", "Neil", "Oscar", "Peter", "Quentin", "Robert", "Sarah", "Tom", "Ursula", "Victor", "Will", "Xavier" ]
            ]
        },
]

def setup_tourney(test):
    # Create a tourney, first removing any existing tourney by this name
    tourney_db_dir = os.path.join("..", "tourneys")

    dbname = test["dbname"]
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
    tourney.set_players(entered_players, auto_rating_behaviour=countdowntourney.RATINGS_UNIFORM)

    return (tourney, div_players)

def main():
    # cd to the directory containing this script.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    num_failures = 0

    for (test_idx, test) in enumerate(tests):
        failed = False
        print("")
        print("Test %d (%s)... " % (test_idx + 1, test["name"]))
        (tourney, div_players) = setup_tourney(test)

        settings = {}
        div_rounds = { div_index : 1 for div_index in range(len(div_players)) }
        generated_groups = fixgen_round_robin.generate(tourney, settings, div_rounds)
        tourney.close()
        generated_rounds = generated_groups.get_rounds()
        for div_index in range(len(div_players)):
            # If there are N players, the number of rounds generated is
            # expected to be N-1 if N is even, and N if N is odd. In the latter
            # case, one player sits out every round.
            # The round robin generator only generates two-to-a-table fixtures,
            # so each generated "group" must only contain two players.
            round_groups = []
            for round_index in range(len(generated_rounds)):
                div_groups = generated_rounds[round_index].get_divisions()
                # div_groups contains a set of groups for each division for
                # which we are generating fixtures in this round.
                # Look for the set corresponding to the division we're
                # interested in, and add those fixtures to round_groups.
                for div_group in div_groups:
                    if div_group.get_division() == div_index:
                        observed_groups = div_group.get_groups()
                        round_groups.append(observed_groups)
                        # Check each group has exactly two players
                        for g in observed_groups:
                            assert(len(g) == 2)
                        break

            # round_groups now contains, for each round, the fixture groups
            # for division div_index.
            # round_groups[x] contains the fixture groups for round_index x.

            # List of lists of player names
            players = div_players[div_index]

            # Ensure everyone in this division plays everyone else
            expected_matches = set()
            for pi1 in range(len(players)):
                for pi2 in range(pi1 + 1, len(players)):
                    # Add the pair to expected_matches in alphabetical order,
                    # because we don't care who's P1/P2 in any specific match.
                    name1 = players[pi1]
                    name2 = players[pi2]
                    if name1 > name2:
                        (name1, name2) = (name2, name1)
                    expected_matches.add((name1, name2))

            # Count the number of times each player plays first and second.
            # They should only differ by 1.
            # Also remember how many times in a row a player has been first
            # or second - no player should find themselves on the same side of
            # the first/second coin more than twice in a row.
            p1_counts = {}  # name -> count
            p2_counts = {}  # name -> count
            streak = {}  # name -> (1/2, count)

            # Look at what matches were generated in this division...
            print("Division %s" % (chr(ord('A') + div_index)))
            for (round_index, groups) in enumerate(round_groups):
                round_number = round_index + 1
                print("Round %d" % (round_number))
                for group in groups:
                    p1 = group[0].get_name()
                    p2 = group[1].get_name()
                    print("    %s v %s" % (p1, p2))
                    p1_counts[p1] = p1_counts.get(p1, 0) + 1
                    p2_counts[p2] = p2_counts.get(p2, 0) + 1
                    for p in [p1, p2]:
                        seat = 1 if p == p1 else 2
                        if p in streak and streak[p][0] == seat:
                            streak[p] = (seat, streak[p][1] + 1)
                            if len(players) % 2 == 0:
                                if streak[p][1] > 2:
                                    print("Player \"%s\" is P%d more than twice in a row!" % (p, seat))
                                    failed = True
                            else:
                                # If a player sits out a round because there
                                # are an odd number of players, each player is
                                # expected to alternate between P1 and P2.
                                if streak[p][1] > 1:
                                    print("Player \"%s\" is P%d twice in a row when there are an odd number of players!" % (p, seat))
                                    failed = True
                        else:
                            streak[p] = (seat, 1)
                    key = (p1, p2) if p1 < p2 else (p2, p1)
                    if key not in expected_matches:
                        print("Not expecting matchup %s v %s: did we already do this one?" % (p1, p2))
                        failed = True
                    else:
                        expected_matches.remove(key)
                print("")

            # Ensure all the matches we were expecting were generated
            if len(expected_matches) != 0:
                print("The following matchups were not seen in the generated fixtures:")
                for (p1, p2) in expected_matches:
                    print("    %s v %s" % (p1, p2))
                failed = True

            # Check nobody played on the same side of the scoresheet too many
            # times in a row (more than twice if an even number of players,
            # more than once if an odd number of players).
            print("P1/P2 counts:")
            for p in players:
                p1c = p1_counts.get(p, 0)
                p2c = p2_counts.get(p, 0)
                print("%s: %d & %d" % (p, p1c, p2c))
                if len(players) % 2 == 0:
                    # For each player, their P1 and P2 count must be 1 apart
                    # and must sum to num_players - 1
                    if abs(p1c - p2c) != 1 or p1c + p2c != len(players) - 1:
                        print("Player \"%s\" has unexpected P1 and P2 counts: %d and %d" % (p, p1c, p2c))
                        failed = True
                else:
                    # Each player's P1 and P2 count must be the same, and must
                    # sum to num_players - 1.
                    if p1c != p2c or p1c + p2c != len(players) - 1:
                        print("Player \"%s\" has unexpected P1 and p2 counts: %d and %d" % (p, p1c, p2c))
                        failed = True
            print("")

        if failed:
            num_failures += 1
        else:
            print("Passed.")
    if num_failures > 0:
        print("%d tests failed." % (num_failures))
        sys.exit(1)
    else:
        print("All tests passed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
