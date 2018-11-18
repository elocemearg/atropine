#!/usr/bin/python3

import sys
import time

# Code to determine, given a standings table and a list of games yet to play,
# whether a player is guaranteed to finish at or above a certain position.


class QualificationTimeoutException(Exception):
    pass


print_logging = False
def log(s):
    if print_logging:
        sys.stderr.write(s + "\n")


def count_games_remaining(standings_row, unplayed_games, all_games_generated, num_games_per_player):
    name = standings_row["name"]
    if all_games_generated:
        count = 0;
        for game in unplayed_games:
            if name in game:
                count += 1
        return count
    else:
        return num_games_per_player - standings_row["played"]

def get_connected_group(node, edges, start_time, time_limit_sec, visited_nodes=None):
    if time.time() > start_time + time_limit_sec:
        raise QualificationTimeoutException();
    if visited_nodes is None:
        visited_nodes = set()
    this_visited_nodes = set(visited_nodes)
    this_visited_nodes.add(node)
    group = set()
    group.add(node)
    for e in edges:
        partner = None
        if e[0] == node:
            partner = e[1]
        elif e[1] == node:
            partner = e[0]
        if partner is not None and partner not in this_visited_nodes:
            group |= get_connected_group(partner, edges, start_time, time_limit_sec, this_visited_nodes)
    return group


def make_connected_subgraph_groups(nodes, edges, start_time, time_limit_sec):
    groups = []
    nodes_done = set()
    for n in nodes:
        if n in nodes_done:
            continue
        group = get_connected_group(n, edges, start_time, time_limit_sec)
        for nn in group:
            nodes_done.add(nn)
        groups.append(group)
    return groups


def get_combinations(possible_results, num_games):
    if num_games <= 0:
        yield []
    else:
        for result in possible_results:
            for remainder in get_combinations(possible_results, num_games - 1):
                yield [result] + remainder


def get_max_potential_overtakers(player_start_win_points, player_row, group, group_relevant_games, draws_allowed, start_time, time_limit_sec, limit=None):
    # Try every combination of results for the games in group_relevant_games,
    # and work out, for each scenario, how many of those players end up
    # overtaking or matching the player in player_row. Return the highest
    # such number.

    if draws_allowed:
        possible_results = [ (2, 0), (0, 2), (1, 1) ]
    else:
        possible_results = [ (2, 0), (0, 2) ]

    max_overtakers = None
    for win_combination in get_combinations(possible_results, len(group_relevant_games)):
        if time.time() > start_time + time_limit_sec:
            raise QualificationTimeoutException()
        player_end_win_points = player_start_win_points.copy()
        for idx in range(len(win_combination)):
            name1 = group_relevant_games[idx][0]
            name2 = group_relevant_games[idx][1]
            player_end_win_points[name1] = player_end_win_points.get(name1, 0) + win_combination[idx][0]
            player_end_win_points[name2] = player_end_win_points.get(name2, 0) + win_combination[idx][1]

        num_overtakers = 0
        for p in group:
            if player_end_win_points.get(p, 0) >= player_row["win_points"]:
                num_overtakers += 1

        if max_overtakers is None or num_overtakers > max_overtakers:
            max_overtakers = num_overtakers

            # If we've found an answer greater than or equal to "limit" then
            # stop searching and just return that. This is an optimisation to
            # stop us searching a huge list of combinations after the first
            # round of a seven-round round-robin, for example.
            if limit is not None and max_overtakers >= limit:
                break

    return max_overtakers

# standings: list of { "name" : <name>,
#                      "pos" : <current position>,
#                      "played" : <games played>,
#                      "win_points" : <2*wins + draws>
#                    }
# player_of_interest: name of the player we're asking about
# unplayed_games: list of (player_name, player_name)
# qual_threshold: a player "qualifies" if they finish in this position or higher
# all_games_generated: true if there are no more games in this division to be generated
# num_games_per_player: the number of games each player will play, unless all_games_generated is set
# draws_allowed: consider a draw as a possible result for an unplayed game

def player_has_qualified(standings, player_of_interest, unplayed_games,
        qual_threshold, all_games_generated, num_games_per_player,
        draws_allowed):
    start_time = time.time()
    time_limit_sec = 5.0

    player_row = None
    for row in standings:
        if row["name"] == player_of_interest:
            if row["pos"] > qual_threshold:
                # Fallen at the first hurdle - this player isn't above the
                # qualification threshold, so there's no guarantee they will
                # enter it.
                return False
            player_row = row
            break

    if player_row is None:
        # Player isn't on the standings table?
        return False

    # First, find the subset of players below or in the same position as this
    # player who could individually equal or exceed this player's win count.
    potential_overtakers = []
    for row in standings:
        if row["pos"] >= player_row["pos"] and row["name"] != player_row["name"]:
            games_remaining = count_games_remaining(row, unplayed_games, all_games_generated, num_games_per_player)
            if games_remaining > 0 and row["win_points"] + 2 * games_remaining >= player_row["win_points"]:
                potential_overtakers.append(row["name"])

    # If the number of potential overtakers is no more than the number of
    # qualification spots below our player, then our player will definitely
    # qualify.
    if len(potential_overtakers) <= qual_threshold - player_row["pos"]:
        log("Not enough potential overtakers to push %s below qualification threshold" % (player_of_interest))
        return True
    
    # Otherwise, our player still might be guaranteed qualification if some of
    # the potential overtakers have to play each other. For example, if we're
    # in first place having played all our games, but the players in second and
    # third place have one win less than us with one game to play, then if they
    # both win their last game they can both overtake us. However if their last
    # game is against each other, only one of them can overtake us so we're
    # guaranteed at least second place.

    # This is where it gets a bit tricky.
    
    # We have a list of all unplayed games. Remove the ones that aren't between
    # two relevant players
    relevant_games = []
    for game in unplayed_games:
        if game[0] in potential_overtakers and game[1] in potential_overtakers:
            relevant_games.append(game)

    # Count how many "relevant" games each potential overtaker has to play
    player_relevant_games = dict()
    for (name1, name2) in relevant_games:
        player_relevant_games[name1] = player_relevant_games.get(name1, 0) + 1
        player_relevant_games[name2] = player_relevant_games.get(name2, 0) + 1

    # Now, make a graph out of the potential overtakers, where each node is a
    # potential overtaker, and each edge is an unplayed game between two
    # potential overtakers. Each connected subgraph can produce a determinable
    # maximum number of overtakers.
    # Potential overtakers who don't have to play any other potential overtakers
    # are isolated nodes on the graph.

    groups = make_connected_subgraph_groups(potential_overtakers, relevant_games, start_time, time_limit_sec)

    standings_dict = dict()
    for row in standings:
        standings_dict[row["name"]] = row

    player_start_win_points = dict()
    for p in potential_overtakers:
        # We'll say that a player's win count is the number of wins they
        # already have, plus one win for every "non-relevant" game, whether
        # generated or not.
        player_win_points = standings_dict[p]["win_points"]
        games_remaining = count_games_remaining(standings_dict[p], unplayed_games, all_games_generated, num_games_per_player)
        log("%s: games remaining %d" % (p, games_remaining))
        player_win_points += games_remaining * 2
        player_win_points -= player_relevant_games.get(p, 0) * 2
        player_start_win_points[p] = player_win_points
    log("groups: " + str(groups))

    max_potential_overtakers = 0
    overtakers_needed_for_non_qual = 1 + qual_threshold - player_row["pos"]
    for group in groups:
        group_relevant_games = []
        for game in relevant_games:
            if game[0] in group and game[1] in group:
                group_relevant_games.append(game)

        # How many potential overtakers can this group serve up?
        max_potential_overtakers += get_max_potential_overtakers(
                player_start_win_points, player_row, group,
                group_relevant_games, draws_allowed,
                start_time, time_limit_sec,
                overtakers_needed_for_non_qual - max_potential_overtakers)
        log("group " + str(group) + (", max_potential_overtakers %d" % (max_potential_overtakers)))

    # Now, we've got the maximal number of people who could, simultaneously,
    # overtake our player of interest. If this is no more than the number of
    # qualification spots below our player, then our player has qualified.
    if max_potential_overtakers >= overtakers_needed_for_non_qual:
        return False
    else:
        return True


#possible_results = sys.argv[1].split(" ")
#for combo in get_combinations(possible_results, int(sys.argv[2])):
#    print combo

#nodes = set()
#edges = []
#for arg in sys.argv[1:]:
#    n = map(int, arg.split(","))
#    if len(n) == 1:
#        nodes.add(n[0])
#    else:
#        nodes.add(n[0])
#        nodes.add(n[1])
#        edges.append((n[0], n[1]))
#
#groups = make_connected_subgraph_groups(nodes, edges)
#
#for group in groups:
#    print " ".join(map(str, group))

if __name__ == "__main__":
    eight_names = [ "Alice", "Bob", "Charlie", "Dave", "Eve", "Fred", "George", "Harry" ]
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

    test_num = 0
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

        print("Test %d" % (test_num))

        failed = False
        for row in standings:
            name = row["name"]
            qualified = player_has_qualified(standings, name,
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
            tests_passed += 1

        test_num += 1

    sys.exit(1 if tests_failed > 0 else 0)
