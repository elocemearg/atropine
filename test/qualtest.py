#!/usr/bin/python3

# Test player_has_qualified() in qualification.py.

import sys

sys.path.append("py")

import qualification

eight_names = [ "Alice", "Bob", "Charlie", "Dave", "Eve", "Fred", "George", "Harry" ]

# A series of test definitions, with the correct answer in test["qualified"]
# in each case.
tests = [
    {
        # Nobody has qualified
        "standings" : [
            # pos, name, played, wins, draws
            [1, "Alice", 6, 5, 0],
            [2, "Bob", 5, 4, 0],
            [3, "Charlie", 5, 4, 0],
            [4, "Dave", 6, 4, 0 ],
            [5, "Eve", 6, 3, 0 ],
            [6, "Fred", 6, 2, 0 ]
        ],
        "unplayed_games" : [],
        "qual_places" : 2,
        "games_per_player" : 6,
        "draws_allowed" : False,
        "all_games_generated" : False,
        "qualified" : []
    },
    {
        # Same as before but Bob and Charlie have to play each other.
        # Either one of them can overtake Alice, but they can't both do so,
        # therefore Alice has qualified
        "standings" : [
            [1, "Alice", 6, 5, 0],
            [2, "Bob", 5, 4, 0],
            [3, "Charlie", 5, 4, 0],
            [4, "Dave", 6, 4, 0 ],
            [5, "Eve", 6, 3, 0 ],
            [6, "Fred", 6, 2, 0 ]
        ],
        "unplayed_games" : [ [ "Bob", "Charlie" ]],
        "qual_places" : 2,
        "games_per_player" : 6,
        "draws_allowed" : False,
        "all_games_generated" : False,
        "qualified" : [ "Alice" ]
    },
    {
        # Neither Bob nor Alice can be caught
        "standings" : [
            [1, "Alice", 6, 5, 1],
            [2, "Bob", 5, 5, 1],
            [3, "Charlie", 5, 4, 0],
            [4, "Dave", 6, 4, 0 ],
            [5, "Eve", 6, 3, 0 ],
            [6, "Fred", 6, 2, 0 ]
        ],
        "unplayed_games" : [],
        "qual_places" : 2,
        "games_per_player" : 6,
        "draws_allowed" : True,
        "all_games_generated" : False,
        "qualified" : [ "Alice", "Bob" ]
    }
    ,{
        # unplayed_games are the only unplayed games left, so it should
        # ignore the "played" attribute in the standings (let's say Eve
        # joined late)
        "standings" : [
            [1, "Alice", 6, 6, 0],
            [2, "Bob", 5, 5, 0],
            [3, "Charlie", 5, 5, 0],
            [4, "Dave", 5, 3, 0 ],
            [5, "Eve", 3, 3, 0 ],
            [6, "Fred", 6, 2, 0 ]
        ],
        "unplayed_games" : [ [ "Bob", "Charlie" ], [ "Dave", "Eve" ] ],
        "qual_places" : 2,
        "games_per_player" : 6,
        "draws_allowed" : False,
        "all_games_generated" : True,
        "qualified" : [ "Alice" ]
    }
    ,{
        # If draws weren't possible, one of Bob or Charlie could overtake
        # Alice but they couldn't both, so Alice is safe. But they are, so
        # they can both overtake Alice.
        "standings" : [
            [1, "Alice", 6, 5, 0],
            [2, "Bob", 5, 4, 1],
            [3, "Charlie", 5, 4, 1],
            [4, "Dave", 5, 3, 0 ],
            [5, "Eve", 5, 3, 0 ],
            [6, "Fred", 6, 2, 0 ]
        ],
        "unplayed_games" : [ [ "Bob", "Charlie" ], [ "Dave", "Eve" ] ],
        "qual_places" : 2,
        "games_per_player" : 6,
        "draws_allowed" : True,
        "all_games_generated" : True,
        "qualified" : []
    }
    ,{
        # Same as above, but this time draws aren't possible (even though
        # Bob and Charlie seem to have managed one) so Bob and Charlie
        # can't both overtake Alice.
        "standings" : [
            [1, "Alice", 6, 5, 0],
            [2, "Bob", 5, 4, 1],
            [3, "Charlie", 5, 4, 1],
            [4, "Dave", 5, 3, 0 ],
            [5, "Eve", 5, 3, 0 ],
            [6, "Fred", 6, 2, 0 ]
        ],
        "unplayed_games" : [ [ "Bob", "Charlie" ], [ "Dave", "Eve" ] ],
        "qual_places" : 2,
        "games_per_player" : 6,
        "draws_allowed" : False,
        "all_games_generated" : True,
        "qualified" : [ "Alice" ]
    }
    ,{
        "standings" : [
            [1, "Inglenook", 4, 4, 0],
            [2, "Frederico", 4, 4, 0],
            [3, "Sevensley", 4, 3, 0],
            [4, "Eyebergine", 4, 3, 0],
            [5, "Salzburg", 4, 3, 0],
            [6, "Infumbula", 4, 3, 0],
            [7, "Compton Spongeworthy", 4, 3, 0],
            [8, "Compton Pauncefoot", 4, 3, 0],
            [9, "Catherley", 3, 3, 0],
            [10, "Mick", 4, 2, 1],
            [11, "Vampira", 4, 2, 1],
            [12, "Amberbrick", 4, 2, 0],
            [13, "Cymbelina", 3, 2, 0],
            [14, "Peaches", 3, 2, 0],
            [15, "Demerara", 3, 2, 0],
            [16, "Flugelhorn", 3, 2, 0],
            [17, "Flangeby", 3, 2, 0],
            [18, "Sincerity", 3, 2, 0],
            [19, "Bun", 3, 2, 0],
            [20, "Roderick", 3, 2, 0],
            [21, "Cat", 3, 1, 2],
            [22, "Patrick", 3, 1, 0],
            [23, "Jacquard", 3, 1, 0],
            [24, "Trilby", 3, 1, 0],
            [25, "Verdigris", 3, 1, 0],
            [26, "Poltroon", 3, 1, 0],
            [27, "Wumpus", 3, 1, 0],
            [28, "Ethelred", 3, 0, 1],
            [29, "Arrows", 3, 0, 0],
            [30, "Blancmange", 3, 0, 0],
            [31, "Solomon", 3, 0, 0],
            [32, "Flopsbourne", 3, 0, 0],
            [33, "Egbert", 3, 0, 0]
        ],
        "unplayed_games" : [ [ "Cymbelina", "Peaches" ],
                             [ "Catherley", "Demerara" ],
                             [ "Flugelhorn", "Flangeby" ],
                             [ "Sincerity", "Patrick" ],
                             [ "Bun", "Roderick" ],
                             [ "Cat", "Jacquard" ],
                             [ "Trilby", "Verdigris" ],
                             [ "Ethelred", "Arrows" ],
                             [ "Poltroon", "Blancmange" ],
                             [ "Flopsbourne", "Solomon" ],
                             [ "Wumpus", "Egbert" ] ],
        "qual_places" : 2,
        "games_per_player" : 4,
        "draws_allowed" : True,
        "all_games_generated" : True,
        "qualified" : ["Inglenook"]
    },
    {
        # One round into a seven-game round robin. We should get this
        # result quickly rather than looking at every possible
        # combination of future results from the seven possible
        # overtakers below the leader.
        # If this takes several minutes to run then the optimisation
        # (the "limit" parameter to get_max_potential_overtakers())
        # hasn't worked.
        "standings" : [
            [ 1, "Alice", 1, 1, 0 ],
            [ 2, "Bob", 1, 1, 0 ],
            [ 3, "Charlie", 1, 1, 0],
            [ 4, "Dave", 1, 1, 0],
            [ 5, "Eve", 1, 0, 0],
            [ 6, "Fred", 1, 0, 0],
            [ 7, "George", 1, 0, 0],
            [ 8, "Harry", 1, 0, 0]
        ],
        "unplayed_games" : [ [ eight_names[x], eight_names[y] ]
                for x in range(8)
                for y in range(8)
                if y > x and x + 4 != y ],
        "qual_places" : 2,
        "games_per_player" : 7,
        "draws_allowed" : True,
        "all_games_generated" : True,
        "qualified" : []
    },
    {
        # Another round robin tournament, after round 4 of 7
        "standings" : [
            [ 1, "Alice",   4, 4, 0 ],
            [ 2, "Dave",    4, 2, 0 ],
            [ 3, "Fred",    4, 2, 0 ],
            [ 4, "Charlie", 4, 2, 0 ],
            [ 5, "Harry",   4, 2, 0 ],
            [ 6, "Bob",     4, 2, 0 ],
            [ 7, "Eve",     4, 1, 0 ],
            [ 8, "George",  4, 1, 0 ]
        ],
        "unplayed_games" : [
                # R5
                [ "Alice", "Harry" ],
                [ "George", "Dave" ],
                [ "Fred", "Charlie" ],
                [ "Eve", "Bob" ],
                # R6
                [ "Alice", "George" ],
                [ "Fred", "Harry" ],
                [ "Eve", "Dave" ],
                [ "Bob", "Charlie" ],
                # R7
                [ "Alice", "Fred" ],
                [ "Eve", "George" ],
                [ "Bob", "Harry" ],
                [ "Charlie", "Dave" ]
        ],
        "qual_places" : 2,
        "games_per_player" : 7,
        "draws_allowed" : True,
        "all_games_generated" : True,
        "qualified" : []
    },
    {
        # Same round robin tournament, after round 5 of 7
        "standings" : [
            [ 1, "Alice",   5, 5, 0 ],
            [ 3, "Fred",    5, 3, 0 ],
            [ 2, "Dave",    5, 2, 0 ],
            [ 4, "Charlie", 5, 2, 0 ],
            [ 5, "Harry",   5, 2, 0 ],
            [ 6, "Bob",     5, 2, 0 ],
            [ 7, "Eve",     5, 2, 0 ],
            [ 8, "George",  5, 2, 0 ]
        ],
        "unplayed_games" : [
                # R6
                [ "Alice", "George" ],
                [ "Fred", "Harry" ],
                [ "Eve", "Dave" ],
                [ "Bob", "Charlie" ],
                # R7
                [ "Alice", "Fred" ],
                [ "Eve", "George" ],
                [ "Bob", "Harry" ],
                [ "Charlie", "Dave" ]
        ],
        "qual_places" : 2,
        "games_per_player" : 7,
        "draws_allowed" : True,
        "all_games_generated" : True,
        "qualified" : [ "Alice" ]
    },
    {
        # Same round robin tournament after a different round 5 of 7
        "standings" : [
            [ 1, "Alice",   5, 5, 0 ],
            [ 2, "Dave",    5, 3, 0 ],
            [ 3, "Charlie", 5, 3, 0 ],
            [ 4, "Fred",    5, 2, 0 ],
            [ 5, "Harry",   5, 2, 0 ],
            [ 6, "Bob",     5, 2, 0 ],
            [ 7, "Eve",     5, 2, 0 ],
            [ 8, "George",  5, 1, 0 ]
        ],
        "unplayed_games" : [
                # R6
                [ "Alice", "George" ],
                [ "Fred", "Harry" ],
                [ "Eve", "Dave" ],
                [ "Bob", "Charlie" ],
                # R7
                [ "Alice", "Fred" ],
                [ "Eve", "George" ],
                [ "Bob", "Harry" ],
                [ "Charlie", "Dave" ]
        ],
        "qual_places" : 2,
        "games_per_player" : 7,
        "draws_allowed" : True,
        "all_games_generated" : True,
        "qualified" : [ "Alice" ]
    },
]

def main():
    test_num = 1
    tests_failed = 0
    tests_passed = 0
    for test in tests:
        standings = []
        for row in test["standings"]:
            standings.append({
                "pos" : row[0],
                "name" : row[1],
                "played" : row[2],
                "win_points" : row[3] * 2 + row[4]
            })

        unplayed_games = test["unplayed_games"]

        qual_threshold = test.get("qual_places", 2)
        num_games_per_player = test.get("num_games_per_player", 6)
        all_games_generated = test.get("all_games_generated", False)
        draws_allowed = test.get("draws_allowed", False)
        expected_qualifiers = test["qualified"]

        print("Running test %d..." % (test_num))

        failed = False
        for row in standings:
            name = row["name"]
            qualified = qualification.player_has_qualified(standings, name,
                    unplayed_games, qual_threshold, all_games_generated,
                    num_games_per_player, draws_allowed)
            if qualified and name not in expected_qualifiers:
                print("Test %d: %s wrongly marked as qualified." % (test_num, name))
                failed = True
            elif not qualified and name in expected_qualifiers:
                print("Test %d: %s wrongly not marked as qualified." % (test_num, name))
                failed = True

        if failed:
            tests_failed += 1
            break
        else:
            print("Test %d passed." % (test_num))
            tests_passed += 1

        test_num += 1

    if tests_failed == 0:
        print("All tests passed.")
    sys.exit(1 if tests_failed > 0 else 0)

if __name__ == "__main__":
    main()
