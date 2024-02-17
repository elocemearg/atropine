#!/usr/bin/python3

import itertools
import random
import time

class RandomDrawTimeoutException(Exception):
    pass

# Our recursive function, called by the front-end function draw().
#
# players must be a set of integers - each integer represents a player. These
# are the players yet to be assigned to a group.
#
# group_sizes is a list of required group sizes. It must be in ascending order.
#
# allowed_opponents is a list of sets. For each pair of players (x, y),
#    the set allowed_opponents[x] contains y iff x may play y.
#    The sets are expected to be symmetrical:
#    (y in allowed_opponents[x] == x in allowed_opponents[y]) for all x, y.
#
# expiry_time: throw a FixtureGeneratorException if we don't find a valid
# solution before time.time() >= expiry_time. Use None (the default) to disable.
#
# group_sizes_pos tells us how far we are through the problem.
#    group_sizes[group_sizes_pos] is the size of the next group to generate.
#    Everything before group_sizes_pos is ignored.
#
# len(players) must equal sum(group_sizes[group_sizes_pos:]).
#
# return value will be the list of lists of player numbers, but the lists will
# be in reverse order to group_sizes.
def draw_aux(players, group_sizes, allowed_opponents, expiry_time=None, group_sizes_pos=0):
    # Base case. No players? No tables.
    if group_sizes_pos >= len(group_sizes):
        return []

    # We can assume group_sizes[group_sizes_pos] is a smallest group in the
    # remaining part of the list, because a precondition is that this list is
    # sorted ascending.

    # Choose the player p in players with the smallest set allowed_opponents[p].
    # This is the player most restricted in who they play - the player with the
    # fewest permitted opponents. Break ties randomly, by choosing the first
    # lowest we find in a randomly-permuted list.
    players_list = list(players)
    random.shuffle(players_list)
    fewest_opps = None
    p_with_fewest_opps = None
    for p in players_list:
        if fewest_opps is None or len(allowed_opponents[p]) < fewest_opps:
            fewest_opps = len(allowed_opponents[p])
            p_with_fewest_opps = p

    next_group_size = group_sizes[group_sizes_pos]
    if fewest_opps < next_group_size - 1:
        # There is at least one player who has fewer than largest_group_size-1
        # permissible opponents, therefore we can't put this player in any
        # group and there is no solution.
        return None

    p = p_with_fewest_opps
    # Try every possible combination of permitted opponents for p until we
    # find a complete solution that works or we've tried all the combinations.
    for p_opps in itertools.combinations(allowed_opponents[p], next_group_size - 1):
        # Have we run out of time?
        if expiry_time is not None and time.time() > expiry_time:
            raise RandomDrawTimeoutException()
        # Ensure all the players in p_opps are allowed to play each other
        skip = False
        for (x, y) in itertools.combinations(p_opps, 2):
            if y not in allowed_opponents[x] or x not in allowed_opponents[y]:
                skip = True
                break
        if skip:
            # p_opps isn't allowed - it contains at least two players who
            # aren't allowed to play each other.
            continue

        # Put p and p_opps in a group
        candidate_group = [ p ] + list(p_opps)

        # Update players and allowed_opponents: these players no longer need
        # to be assigned to a group, and nobody else is allowed to play them
        for x in candidate_group:
            players.discard(x)

        # Remember the changes we're about to make to allowed_opponents, just
        # in case we have to backtrack them...
        allowed_opponents_removed = {}
        for x in players:
            for y in candidate_group:
                if y in allowed_opponents[x]:
                    allowed_opponents[x].remove(y)
                    if x not in allowed_opponents_removed:
                        allowed_opponents_removed[x] = set()
                    allowed_opponents_removed[x].add(y)

            # If this reduced any player's number of allowed opponents to
            # less than next_group_size - 1, then candidate_group is not a
            # candidate because this player can't fit in any group.
            if len(allowed_opponents[x]) < next_group_size - 1:
                break
        else:
            # We didn't break out of the inner for-loop above.
            # Take candidate_group as part of our solution, and recurse to
            # solve the rest.
            remaining_groups = draw_aux(players, group_sizes, allowed_opponents, expiry_time, group_sizes_pos + 1)
            if remaining_groups is not None:
                # We have a complete solution! Return it.
                remaining_groups.append(candidate_group)
                return remaining_groups

        # If we get here, either the recursive call returned None or we broke
        # out of the for-loop above. Either way, our choice of candidate group
        # didn't work, so put players and allowed_opponents back how they were
        # and try the next combination.
        for x in candidate_group:
            players.add(x)
        for x in allowed_opponents_removed:
            allowed_opponents[x] |= allowed_opponents_removed[x]

    # If we get here, we tried every combination and found no solution.
    return None


def draw(group_sizes, invalid_pairs, random_attempts_before_search=100, search_time_limit_ms=None):
    """
    draw(): randomly divide players into equal groups, subject to constraints

    group_sizes: the sizes of the desired groups, as an ascending-sorted list.
    The total number of players is the sum of the elements of this list. For
    example, [3, 3, 3, 3] will return four groups of three, and the players
    will be represented by the numbers 0 to 11 inclusive. A ValueError will be
    raised if the list is not sorted in ascending order.

    invalid_pairs: a collection of pairs (x, y), where x and y are all in the
    range [0, sum(group_sizes)). A valid solution will not put x and y in the
    same group. This is how you tell the function that the players represented
    by x and y have already played each other. The caller only needs to include
    (x, y) one way round; (x, y) and (y, x) are equivalent.

    random_attempts_before_search: try up to this many random arrangements
    hoping for one that happens to fit the constraints, before defaulting to a
    random but systematic search, for which some overall outcomes might be
    more probable than others. If a random arrangement succeeds, it will be
    returned and every permitted outcome is as likely as any other.

    search_time_limit_ms: raise a RandomDrawTimeoutException if the search
    takes longer than this many milliseconds.

    return value: (solution, search_required).
        solution: a list of lists of numbers in the range [0, num_players).
        The returned list will have the same number of elements as group_sizes,
        and each element i will have group_sizes[i] numbers in it.
        search_required: True if we tried random_attempts_before_search random
        permutations and none of them were valid, requiring a systematic search.
        False if one of the random attempts found a valid solution.
    """

    num_players = sum(group_sizes)

    # For each player, build a set of players they're allowed to play
    allowed_opponents = []
    for p in range(num_players):
        # Start with the set of all players
        opps = set(range(num_players))

        # No player can play themselves.
        opps.remove(p)

        allowed_opponents.append(opps)

    # Remove from these sets the players each player can't play.
    for (x, y) in invalid_pairs:
        # x can't play y
        allowed_opponents[x].discard(y)
        # y can't play x
        allowed_opponents[y].discard(x)

    # First, just try choosing an arrangement entirely at random and check if
    # this passes the constraints. This is slightly fairer than randomizing the
    # order and doing a search, as explained below.
    permutation = list(range(num_players))
    for random_attempt in range(random_attempts_before_search):
        random.shuffle(permutation)
        valid = True
        groups = []
        group_start = 0
        for group_size in group_sizes:
            group = permutation[group_start:(group_start + group_size)]
            for (x, y) in itertools.combinations(group, 2):
                if y not in allowed_opponents[x]:
                    # This random attempt is not valid
                    valid = False
                    break
            if not valid:
                break
            groups.append(group)
            group_start += group_size
        if valid:
            return (groups, False)

    # Random crapshoot didn't work - it's time for a systematic search.
    # This is slightly less fair, because not every valid outcome is always
    # equally likely. For example, we might have a 50/50 decision to make, and
    # one branch leads to 100 valid solutions and the other branch leads to 10.
    # Each individual solution on the second branch will be 10 times more
    # likely to be selected than each individual solution on the left.

    # draw_aux() doesn't actually do anything random, so we'll choose
    # a random mapping from [0, n) -> [0, n) to start with.
    random.shuffle(permutation)

    # Rewrite allowed_opponents with the mapping x -> permutation[x]. We'll
    # do the inverse of this on the returned groups.
    new_allowed_opponents = [ None for x in range(len(permutation)) ]
    for x in range(len(allowed_opponents)):
        new_allowed_opponents[permutation[x]] = set()
        for y in allowed_opponents[x]:
            new_allowed_opponents[permutation[x]].add(permutation[y])
    allowed_opponents = new_allowed_opponents

    # Remember the inverse of this permutation.
    permutation_inverse = [ None for i in range(num_players) ]
    for (i, x) in enumerate(permutation):
        permutation_inverse[x] = i

    # Now call our recursive function
    players = set(range(num_players))
    if search_time_limit_ms:
        expiry_time = time.time() + search_time_limit_ms / 1000
    else:
        expiry_time = None
    solution = draw_aux(players, group_sizes, allowed_opponents, expiry_time)

    if solution is not None:
        # Decode the returned player numbers using permutation_inverse, so the
        # player numbers here refer to the same player numbers the caller
        # meant in invalid_pairs.
        solution = [ [ permutation_inverse[x] for x in group ] for group in solution ]

        # Put the lists in the same order as the group sizes
        solution.reverse()

    return (solution, True)

