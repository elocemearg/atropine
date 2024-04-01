#!/usr/bin/python3

import sys
import time
import countdowntourney
import random
import itertools

# Penalty applied to a game between two players who have already played each
# other, or between two prunes, or between a player and a prune where the
# player has already played another prune.
HUGE_PENALTY_EXPONENT = 10
HUGE_PENALTY = 10 ** HUGE_PENALTY_EXPONENT

# A fixture between two players with a difference in their standings position
# of pos_diff is given a penalty of POSITION_DIFFERENCE_PENALTY_BASE^pos_diff.
POSITION_DIFFERENCE_PENALTY_BASE = 1.6

# A fixture between two players with a difference in their win counts of
# win_diff is given a penalty of WIN_DIFFERENCE_PENALTY_BASE^win_diff.
# Let's treat a fixture with a win difference of 1 the same as a position
# difference of 4.
WIN_DIFFERENCE_PENALTY_BASE = POSITION_DIFFERENCE_PENALTY_BASE ** 4

# Maximum number of entries in swissN()'s cache of table penalties.
TABLE_PENALTY_CACHE_MAX_SIZE = 1000000

ENABLE_PENALTY_CAP_OPTIMISATION = True
ENABLE_RESULTS_CACHE_OPTIMISATION = True

# Consider this standings table, of people whose names happen to coincide with
# their standings position...
#
#                  W
# 10 Tenth         1
# 11 Eleventh      1
# 12 Twelfth       1
# 12 Also Twelfth  1
# 12 Twelfth Again 1
# 15 Fifteenth     1
#
# We would prefer something like:
# [ (Tenth, Eleventh, Twelfth), (Also Twelfth, Twelfth Again, Fifteenth) ]
# over something like:
# [ (Tenth, Eleventh, Fifteenth), (Twelfth, Also Twelfth, Twelfth Again) ]
#
# The latter puts all the twelfths on the same table but Fifteenth is put with
# players more distant in the standings. We want the latter to have a higher
# penalty.
#
# w = WIN_DIFFERENCE_PENALTY_BASE
# p = POSITION_DIFFERENCE_PENALTY_BASE
#
# The penalty for a table is the mean average of all pairs on the table.
#
# First arrangement:
# avg(p^1, p^2, p^1) + avg(p^0, p^3, p^3)
#    = avg(1.6, 2.56, 1.6) + avg(1, 4.096, 4.096)
#    = 1.92 + 3.064 = 4.984
#
# Second arrangement:
# avg(p^1, p^5, p^4) + avg(p^0, p^0, p^0)
#    = avg(1.6, 10.48576, 6.5536) + avg(1, 1, 1)
#    = 6.21312 + 1 = 7.21312
#
# So a POSITION_DIFFERENCE_PENALTY_BASE value of 1.6 favours the first
# arrangement, which is what we want.

class StandingsPlayer(object):
    def __init__(self, name, rating, wins, position, played, played_first, avoid_prune):
        self.name = name;
        self.rating = rating
        self.wins = wins
        self.position = position
        self.games_played = played
        self.games_played_first = played_first
        self.avoid_prune = avoid_prune

    def get_name(self):
        return self.name

    def get_rating(self):
        return self.rating

    def is_prune(self):
        return self.rating == 0

    def get_played_first_pc(self):
        if self.games_played == 0:
            # If this player hasn't played any games, give them a notional
            # played-first ratio of 50%.
            return 50.0
        else:
            return float(100 * self.games_played_first) / self.games_played

class UnknownPlayerException(BaseException):
    pass;

class IllegalNumberOfPlayersException(BaseException):
    pass;

class InvalidGroupSizeListException(BaseException):
    pass;

class PlayerNotInStandingsException(BaseException):
    description = "I've been asked to arrange fixtures for a player who isn't in the standings table. This is a bug."
    pass;


# Calculate number of penalty points associated with p1 playing p2, taking
# into account that they've played before num_played times, and p1's win count
# differs from p2's win count by win_diff (which is always non-negative).
# This is also called the "weighting".
def get_penalty(p1, p2, num_played, win_diff, highest_pos_by_win_count, rank_by_wins=True, equal_wins_are_equal_players=False):
    pen = 0;

    # No, you are not allowed to play yourself
    if p1.name == p2.name:
        return HUGE_PENALTY ** 2;

    # Don't want two players meeting twice
    pen += HUGE_PENALTY * num_played

    # Don't want two prunes drawn against each other
    if p1.is_prune() and p2.is_prune():
        pen += HUGE_PENALTY;

    # If two players have a different number of wins, apply a penalty.
    # Fixtures between players whose win counts differ by 1 are usually
    # unavoidable, but there should be exponentially harsher penalties for
    # putting people on the same table whose win counts differ by more.
    # Unless equal_wins_are_equal_players, we also take into account the
    # difference in standings position, so that we group together people in
    # roughly the same part of the standings.
    pos_diff = abs(p1.position - p2.position)
    if not rank_by_wins and not equal_wins_are_equal_players:
        win_diff = 0

    if win_diff > 0:
        game_pen = ( WIN_DIFFERENCE_PENALTY_BASE ** float(win_diff) )
    else:
        game_pen = 0

    if equal_wins_are_equal_players:
        if win_diff > 0:
            # If we have to put one or more players with N-1 wins with a
            # player with N wins, prefer to select the highest-ranked players
            # on N-1 wins, who should play random player(s) on N wins.
            # For this reason, we make the penalty between P1 and P2 the
            # number of places away from the top of their win-count-group the
            # lower-ranked player is, plus whatever win difference penalty was
            # calculated above. This "promotes" the highest ranked lower-win
            # players to be honorary higher-win players.
            if p1.wins < p2.wins:
                game_pen += p1.position - highest_pos_by_win_count[p1.wins]
            else:
                game_pen += p2.position - highest_pos_by_win_count[p2.wins]
    else:
        # Take into account these two players' difference in standings.
        game_pen += ( POSITION_DIFFERENCE_PENALTY_BASE ** float(pos_diff) )
    if game_pen >= HUGE_PENALTY:
        game_pen = HUGE_PENALTY - 1
    pen += game_pen

    return pen;

# Calculate the matrix of penalties for each pair of players.
def calculate_weight_matrix(games, players, played_matrix, win_diff_matrix, rank_by_wins=True, equal_wins_are_equal_players=False):
    matrix_size = len(players);
    matrix = [];

    # For each win count, work out the position of the highest-ranked player
    # with that win count. get_penalty() may use this.
    highest_pos_by_win_count = {}
    for p in players:
        if p.wins not in highest_pos_by_win_count or p.position < highest_pos_by_win_count[p.wins]:
            highest_pos_by_win_count[p.wins] = p.position

    for i1 in range(matrix_size):
        p1 = players[i1]
        vector = [];

        # To make the graph symmetric, in case get_penalty(p1, p2) does not
        # equal get_penalty(p2, p1) for some reason, the weight between p1
        # and p2 is max(penalty(p1, p2), penalty(p2, p1))

        for i2 in range(matrix_size):
            p2 = players[i2]
            pen = max(get_penalty(p1, p2, played_matrix[i1][i2],
                win_diff_matrix[i1][i2], highest_pos_by_win_count,
                rank_by_wins, equal_wins_are_equal_players),
                get_penalty(p2, p1, played_matrix[i2][i1],
                    win_diff_matrix[i2][i1], highest_pos_by_win_count,
                    rank_by_wins, equal_wins_are_equal_players)
            );
            vector.append(pen);

        matrix.append(vector);

    for i in range(matrix_size):
        for j in range(matrix_size):
            if matrix[i][j] != matrix[j][i]:
                print("i %d, j %d, matrix[i][j] %f, matrix[j][i] %f!" % (i, j, matrix[i][j], matrix[j][i]), file=sys.stderr);

    return matrix;

def get_table_penalty(weight_matrix, table, table_penalty_cache):
    table = tuple(table)
    if len(table) <= 1:
        return 0
    elif table_penalty_cache and table in table_penalty_cache:
        return table_penalty_cache[table]
    else:
        # penalty is the average penalty of all possible pairs on the table.
        penalty_sum = 0
        num_samples = 0
        for i1 in range(0, len(table)):
            for i2 in range(i1 + 1, len(table)):
                penalty_sum += weight_matrix[table[i1]][table[i2]]
                num_samples += 1
        avg_penalty = float(penalty_sum) / num_samples
        if table_penalty_cache is not None and len(table) <= 5 and len(table_penalty_cache) < TABLE_PENALTY_CACHE_MAX_SIZE:
            table_penalty_cache[table] = avg_penalty
        return avg_penalty

def total_penalty(weight_matrix, tables, table_penalty_cache):
    penalty = 0
    for table in tables:
        penalty += get_table_penalty(weight_matrix, table, table_penalty_cache)
    return penalty

def generate_sets(l, num, l_start=0, l_end=None):
    if l_end is None:
        l_end = len(l)
    l_size = l_end - l_start
    if num == 0:
        yield []
    elif num == l_size:
        yield l[l_start:l_end]
    elif num == 1:
        for i in range(l_start, l_end):
            yield [l[i]]
    elif num < l_size:
        # Generate the close-together sets first, so fix the last element at
        # near the start of the list for the first recursive call, then the
        # next, then the next, etc.
        for last_index in range(l_start + num - 1, l_end):
            for first_index in range(l_start, last_index - num + 2):
                for remainder in generate_sets(l, num - 2, first_index + 1, last_index):
                    yield [l[first_index]] + remainder + [l[last_index]]


def generate_all_groupings_aux(group_size_list, possible_opponent_matrix,
        penalty_matrix, limit_ms, depth=0, start_time=None,
        table_penalty_cache=None, unseated_players=None, known_solutions=None):
    """ Generate the best groupings of tables along with their penalty values.

    All players are represented by an integer in the range [0, N), where N
    is the number of players.

    group_size_list: an array of group sizes required, one entry for each
        group. For example, [3, 3, 3, 3, 3]. The entries must add up to
        exactly the number of players. Undefined behaviour occurs otherwise.
    possible_opponent_matrix: a two-dimensional list of boolean values.
        if possible_opponent_matrix[i][j] is False, we do not consider any
        grouping in which player i plays player j.
    penalty_matrix: another two-dimensional N*N list, this time of floats.
        penalty_matrix[i][j] gives the penalty associated with player i
        playing player j. This must be completely filled in and symmetric,
        so for all i and j, penalty_matrix[i][j] == penalty_matrix[j][i].
    limit_ms: give up and stop yielding results when after this amount of
        time has passed, in milliseconds.
    """

    if not group_size_list:
        # Base case: return an empty list of tables and a zero penalty.
        yield ([], 0)
        return

    if start_time is None:
        start_time = time.time()

    if time.time() > start_time + limit_ms / 1000.0:
        # Out of time
        return

    if table_penalty_cache is None:
        table_penalty_cache = {}
    if known_solutions is None:
        known_solutions = {}

    group_size = group_size_list[0]

    if unseated_players is None:
        unseated_players = set(range(len(possible_opponent_matrix)))

    # In this function players are represented as simple integers from 0 to
    # N-1, where N is the number of players. Player "0" is at the top of the
    # standings table. We're more likely to find a good match if we try numbers
    # close together (trying (0, 1, 2) first is likely to get better results
    # quicker than (0, 13, 35)), so remaining_players is a sorted list, not a
    # set.
    remaining_players = [ p for p in range(len(possible_opponent_matrix)) if p in unseated_players ]
    remaining_players_bitmask = 0
    for p in remaining_players:
        remaining_players_bitmask |= (1 << p)

    # The best solution we find to the problem given to this call, and the
    # penalty associated with that solution.
    best_solution = None
    best_penalty = None

    # If any player has fewer than group_size - 1 possible opponents, then
    # we know we can't find a complete solution so don't waste time solving
    # part of the problem a million times...
    for p in remaining_players:
        num_possible_opponents = 0
        for opp in remaining_players:
            if opp != p and possible_opponent_matrix[p][opp]:
                num_possible_opponents += 1
        if num_possible_opponents < group_size - 1:
            # No solutions
            return

    # Have we found the solution to this problem before? Yes? Good, return that.
    if remaining_players_bitmask in known_solutions:
        yield known_solutions[remaining_players_bitmask]
        return

    if remaining_players:
        p = remaining_players[0]
        opps = [ opp for opp in remaining_players if opp != p and possible_opponent_matrix[p][opp] ]

        # Sort the opponents, putting the opponent most compatible with p first.
        # This means we try that opponent first and we're more likely to get
        # the best grouping faster.
        opps.sort(key=lambda opp : penalty_matrix[p][opp])

        #sys.stderr.write("%*slooking for opponents for %d from %s\n" % (depth, "", p, str(opps)))
        if len(opps) >= group_size - 1:
            for remainder in generate_sets(opps, group_size - 1):
                # Check that the remaining players in this set could all
                # play each other...
                reject = False
                for i in range(len(remainder) - 1):
                    for j in range(i + 1, len(remainder)):
                        if not possible_opponent_matrix[remainder[i]][remainder[j]]:
                            reject = True
                            break
                    if reject:
                        break
                if reject:
                    continue

                if time.time() > start_time + limit_ms / 1000.0:
                    return

                candidate_table = [p] + remainder
                candidate_table_penalty = get_table_penalty(penalty_matrix, candidate_table, table_penalty_cache)

                # If the penalty for this table alone is higher than the
                # penalty of the best solution we've found from this point,
                # this candidate table can't form part of the optimal solution
                # so there's no point in using it.
                if ENABLE_PENALTY_CAP_OPTIMISATION and best_penalty is not None and candidate_table_penalty > best_penalty:
                    continue

                # Mark players on this table as already seated for the
                # next recursive call and those below it...
                for cp in candidate_table:
                    unseated_players.remove(cp)
                for (remaining_tables, rem_penalty) in generate_all_groupings_aux(
                        group_size_list[1:], possible_opponent_matrix,
                        penalty_matrix, limit_ms, depth + 1, start_time,
                        table_penalty_cache, unseated_players, known_solutions):
                    # If this solution to the remainder, when put together
                    # with the candidate table we picked, is better than
                    # any solution we might have yielded so far, then
                    # yield this new solution.
                    if best_penalty is None or candidate_table_penalty + rem_penalty < best_penalty:
                        best_solution = [candidate_table] + remaining_tables
                        best_penalty = candidate_table_penalty + rem_penalty
                        yield (best_solution, best_penalty)
                # Undo what we did to unseated_players before the call
                for cp in candidate_table:
                    unseated_players.add(cp)

    if best_penalty is not None and ENABLE_RESULTS_CACHE_OPTIMISATION:
        known_solutions[remaining_players_bitmask] = (best_solution, best_penalty)


def generate_all_groupings(group_size_list, played_matrix, win_diff_matrix,
        penalty_matrix, max_rematches, max_wins_diff, prune_set, start_time,
        limit_ms):
    num_players = len(played_matrix)
    possible_opponent_matrix = [ [ False for i in range(num_players) ] for j in range(num_players) ]
    if sum(group_size_list) != num_players:
        raise InvalidGroupSizeListException()
    for p in range(num_players):
        for opp in range(num_players):
            if p != opp:
                if played_matrix[p][opp] <= max_rematches and win_diff_matrix[p][opp] <= max_wins_diff and not(p in prune_set and opp in prune_set):
                    possible_opponent_matrix[p][opp] = True
    for (solution, penalty) in generate_all_groupings_aux(group_size_list,
            possible_opponent_matrix, penalty_matrix, limit_ms):
        yield (solution, penalty)

class PlayerGroup(object):
    def __init__(self, player_list, weight):
        self.player_list = player_list;
        self.weight = weight;

    def __getitem__(self, i):
        return self.player_list[i];

    def __len__(self):
        return len(self.player_list);

def shuffle_joint_positioned_players(players, equal_wins_are_equal_players=False):
    i = 0
    while i < len(players):
        pos = players[i].position
        wins = players[i].wins
        j = i + 1
        # If equal_wins_are_equal_players, chunks of players on the same number
        # of wins are shuffled, regardless of points or anything else.
        while j < len(players) and ((not equal_wins_are_equal_players and players[j].position == pos) or (equal_wins_are_equal_players and players[j].wins == wins)):
            j += 1
        if j - i > 1:
            # The chunk of the array in the interval [i, j) must be shuffled
            chunk = players[i:j]
            random.shuffle(chunk)
            for k in range(i, j):
                players[k] = chunk[k - i]
        i = j

def to_ordinal(n):
    if (n // 10) % 10 == 1:
        return str(n) + "th"
    elif n % 10 == 1:
        return str(n) + "st"
    elif n % 10 == 2:
        return str(n) + "nd"
    elif n % 10 == 3:
        return str(n) + "rd"
    else:
        return str(n) + "th"

def swissN_first_round(cdt_players, group_size):
    if group_size > 0 and len(cdt_players) % group_size != 0:
        raise IllegalNumberOfPlayersException()
    if group_size == -5:
        raise InvalidGroupSizeListException()

    # Put the players in rating order, largest to smallest
    players = sorted(cdt_players, key=lambda x : x.rating, reverse=True);

    num_groups = len(cdt_players) // group_size;
    groups = [];
    for i in range(num_groups):
        player_list = [];
        for j in range(group_size):
            player_list.append(players[j * num_groups + i]);
        if len(player_list) == 2:
            if random.random() >= 0.5:
                player_list = [player_list[1], player_list[0]]
        groups.append(PlayerGroup(player_list, 0));
    return (0, groups);

def rotate_players(groups, swapsies):
    """
    For each (table_index, player_index) in swapsies, replace that player
    with the player in the position described by the next element in
    swapsies, and so on, rotating around to the beginning of swapsies.

    Calling this function on the same list len(swapsies) times with the same
    value of swapsies will result in the groups list returning back to its
    state before the first call.
    """

    if not swapsies:
        return
    (first_t, first_p) = swapsies[0]
    first_player = groups[first_t][first_p]
    for (i, (t, p)) in enumerate(swapsies):
        if i + 1 >= len(swapsies):
            # Last element of swapsies: replace player at this position with first_player
            groups[t][p] = first_player
        else:
            # Replace player at this position with the next player
            (next_t, next_p) = swapsies[i + 1]
            groups[t][p] = groups[next_t][next_p]

def generate_table_and_seat_indices(groups, count, dist_between_tables):
    """
    Generate all combinations of lists of (table_index, player_index) where
    groups[table_index][player_index] is defined, subject to the constraints
    that all yielded lists have "count" 2-tuples in them, and the smallest and
    largest table_index in any list are dist_between_tables apart.

    For example:
      generate_table_and_seat_indices([[a, b, c], [d, e, f], [g, h, i]], 2, 2)
    yields:
      [ (0, 0), (2, 0) ]
      [ (0, 0), (2, 1) ]
      [ (0, 0), (2, 2) ]
      [ (0, 1), (2, 0) ]
      [ (0, 1), (2, 1) ]
      [ (0, 1), (2, 2) ]
      [ (0, 2), (2, 0) ]
      [ (0, 2), (2, 1) ]
      [ (0, 2), (2, 2) ]
    """

    for first_table in range(0, len(groups) - dist_between_tables):
        last_table = first_table + dist_between_tables
        # We know the lowest and highest table index. Work out all combinations
        # of length count - 2 of tables that are between those.
        for mid_tables in itertools.combinations(range(first_table + 1, last_table), count - 2):
            tables = [first_table] + list(mid_tables) + [last_table]

            # For this set of tables, generate results with all valid player indices.
            player_indices = [ 0 for t in tables ]
            finished = False
            while not finished:
                yield [ (tables[ti], player_indices[ti]) for ti in range(len(tables)) ]
                # Increment player_indices[0]. If this reaches
                # len(groups[tables[0]]), reset it to 0 and increment
                # player_indices[1], and so on until player_indices[-1] wraps.
                ti = 0
                while ti < len(player_indices):
                    player_indices[ti] += 1
                    if player_indices[ti] >= len(groups[tables[ti]]):
                        player_indices[ti] = 0
                        ti += 1
                    else:
                        break
                if ti == len(player_indices):
                    finished = True

def hill_climb(groups, penalty_matrix, time_limit_ms=None):
    """
    Try to swap players between groups to improve the overall penalty of the
    set of groups. groups will be modified in place, and the penalty of the
    new groupings will be returned. We only swap players if that improves the
    overall penalty. We keep swapping players until no more improvement occurs
    or the time limit expires.

    groups is an array of arrays of integers. Each array groups[x] represents a
    group of players, and each integer groups[x][y] represents a player.
    """

    if time_limit_ms:
        deadline = time.time() + time_limit_ms / 1000
    else:
        deadline = None
    penalty_cache = {}
    table_penalties = [ get_table_penalty(penalty_matrix, group, penalty_cache) for group in groups ]
    current_penalty = sum(table_penalties)
    improved = True
    while improved:
        # See if we can swap players between different tables to give a lower
        # overall penalty.
        improved = False
        # num_to_swap: the number of players we will rotate like a carousel.
        # When we've rotated them num_to_swap times, we're back where we began.
        # Start off by trying to swap only two players, then try to rotate
        # three players between different tables, then four.
        for num_to_swap in (2, 3, 4):
            if num_to_swap > 3:
                # Don't do an exhaustive search when trying to rotate four
                # players, because there will be loads of combinations to try,
                # most of them fruitless.
                dist_limit = 5
            else:
                dist_limit = len(groups) - 1
            # Start off trying to swap players from adjacent tables then
            # increase the distance between the tables we swap between if we
            # don't find any improvement.
            for dist_between_tables in range(num_to_swap - 1, dist_limit + 1):
                # Generate all possible combinations of num_to_swap players
                # between different tables where the furthest-apart tables
                # are exactly dist_between_tables tables apart.
                for swapsies in generate_table_and_seat_indices(groups, num_to_swap, dist_between_tables):
                    for rotate_iteration in range(num_to_swap):
                        rotate_players(groups, swapsies)
                        if rotate_iteration == num_to_swap - 1:
                            # No rotation of these players found any improvement
                            # and the players are now rotated back to where they
                            # were before.
                            break

                        # Recalculate the penalties for the tables involved in this swap
                        tables_in_swap = [ t for (t, p) in swapsies ]
                        add_penalty = sum([get_table_penalty(penalty_matrix, groups[t], penalty_cache) for t in tables_in_swap ])
                        remove_penalty = sum([table_penalties[t] for t in tables_in_swap])

                        # If the sum of the penalties for these two tables is
                        # now lower than what it was before by more than
                        # floating point rounding noise, accept this swap.
                        new_penalty = current_penalty + add_penalty - remove_penalty
                        if current_penalty - new_penalty > 0.000001:
                            current_penalty = new_penalty
                            for t in tables_in_swap:
                                table_penalties[t] = get_table_penalty(penalty_matrix, groups[t], penalty_cache)
                            improved = True
                            print("[swissN] Hill climb: swapsies %s, total penalty now %f." % (str(swapsies), current_penalty), file=sys.stderr)
                            break
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break
        if deadline and time.time() > deadline:
            print("[swissN] Hill climb: time expired.", file=sys.stderr)
            break
    return current_penalty


def swissN(games, cdt_players, standings, group_size, rank_by_wins=True,
        limit_ms=None, init_max_rematches=0, init_max_win_diff=0,
        ignore_rematches_before=None, equal_wins_are_equal_players=False):
    """swissN(): the public entry point to the SwissN generator.

    Generate a number of groups (or "tables"), each with a number of players
    at the table. Every player plays every other player on their table in a
    round robin.

    Arguments:

    games: a list of countdowntourney.Game objects, describing the games which
    have been played so far.

    cdt_players: a list of countdowntourney.Player objects, describing the
    players we want to include in this round. This should only include active
    players.

    standings: a list of countdowntourney.StandingsRow objects describing the
    standings table at the point we want to generate fixtures. Each
    StandingsRow object contains the position, win count, points scored, and
    name of a player, along with other information.

    group_size: the number of players to put in each group. Usually this is
    2 or 3. Valid values are 2, 3, 4 or -5. -5 means to use a mixture of
    tables of 3 and tables of 5. Each pair on a table of 3 plays twice.
    If the number of players is not a multiple of the group size, or if there
    are not at least 8 players if the group size is -5, an exception is thrown.

    rank_by_wins: True if players' win counts are used to rank players in the
    standings table. This is pretty much always true.

    limit_ms: If we haven't finished after this many milliseconds, terminate
    and return the best solution found so far, or return (None, None) if no
    solution was found.

    init_max_rematches: the (initial) number of maximum rematches that should
    be allowed, after considering the fixtures we generate. Usually this is 0,
    which means we don't put players on the same table if they've played each
    other already (according to games). If we can't find a solution and there's
    still time, swissN() might increase this and try again.

    init_max_win_diff: the (initial) maximum difference allowed between the
    player with the most wins on a table and the player with the fewest wins
    on that table. If we can't find a solution according to this constraint and
    there's still time, swissN() might increase this and try again. The default
    is 0, but this is usually impossible so we end up trying again with 1,
    which means players on the same table are allowed to have a difference of
    up to 1 in their win count.

    ignore_rematches_before: normally we attach a large penalty to generating
    a fixture between two players who have already played each other. If this
    is set to a positive integer, matches in the "games" list before that
    round number are ignored when applying this rule.

    equal_wins_are_equal_players: do not distinguish between players on the
    same number of wins. This effectively matches each player with random
    opponents on the same win count if possible. Standings position is only
    considered when deciding who has to be promoted to play people of a higher
    win count.
"""

    log = True
    players = [];

    # If we have auto-prunes, we'll need to invent a standings position for
    # them because they won't be in the standings. Put all auto-prunes in joint
    # last place, which is one more than the number of non-auto-prunes.
    num_auto_prunes = len([p for p in cdt_players if p.is_auto_prune()])
    last_place = len(cdt_players) - num_auto_prunes + 1
    for p in cdt_players:
        if p.is_auto_prune():
            # Make up a standings row for the auto-prune
            players.append(StandingsPlayer(p.name, 0, 0, last_place, 0, 0, True))
        else:
            # Look up this player in the standings
            for s in standings:
                if s.name == p.name:
                    players.append(StandingsPlayer(p.name, p.rating, s.wins + float(s.draws) / 2, s.position, s.played, s.played_first, p.is_avoiding_prune()));
                    break
            else:
                print(p.name + " not in standings table for this division", file=sys.stderr)
                raise PlayerNotInStandingsException()

    # Sort "players" by their position in the standings table, as that means
    # we try the most likely combinations first when later on we generate all
    # the combinations we can in a limited time.
    players = sorted(players, key=lambda x : x.position)

    # If any set of two or more players have exactly the same position,
    # randomly shuffle their positions in that part of the array. This ensures
    # that when we have such a set of people in joint Nth place, the person
    # whose name is nearest the beginning of the alphabet doesn't always get
    # selected first to play on a stronger table.
    shuffle_joint_positioned_players(players, equal_wins_are_equal_players)

    # Check that the group size makes sense for the number of players. By
    # this point we should have added any required auto-prunes, so the number
    # of StandingsPlayer objects in "players" must be a multiple of the
    # group size.
    if group_size == -5:
        if len(players) < 8:
            raise IllegalNumberOfPlayersException()
        group_size_list = countdowntourney.get_5_3_table_sizes(len(players))
    else:
        if len(players) % group_size != 0:
            raise IllegalNumberOfPlayersException()
        group_size_list = [ group_size for i in range(len(players) // group_size) ]

    player_name_to_index = {}
    for (i, p) in enumerate(players):
        player_name_to_index[p.get_name()] = i

    # Build the matrix of how many times each player has played each other
    # player.
    played_matrix = [ [ 0 for p in players ] for q in players ]
    for g in games:
        if ignore_rematches_before is not None and g.round_no < ignore_rematches_before:
            continue
        i1 = player_name_to_index.get(g.p1.get_name())
        i2 = player_name_to_index.get(g.p2.get_name())
        if i1 is not None and i2 is not None:
            played_matrix[i1][i2] += 1
            played_matrix[i2][i1] += 1

    # Identify the prunes, and put their indices in the prune_set set
    prune_set = set()
    a_prune_index = None
    for pi in range(len(players)):
        if players[pi].is_prune():
            prune_set.add(pi)
            if a_prune_index is None:
                a_prune_index = pi

    # If there is at least one prune, and any players should be treated as
    # having played prune even though they haven't, fiddle played_matrix
    # accordingly
    pi = 0
    if a_prune_index is not None:
        for p in players:
            if p.avoid_prune:
                played_matrix[pi][a_prune_index] += 1
                played_matrix[a_prune_index][pi] += 1
            pi += 1

    # Adjust the played_matrix so that if you've played one prune, you've
    # effectively played them all
    for pi in range(len(players)):
        num_prune_matches = sum(played_matrix[pi][x] for x in prune_set)
        for x in prune_set:
            played_matrix[pi][x] = num_prune_matches
            played_matrix[x][pi] = num_prune_matches

    if log:
        print("[swissN] Player / already played:", file=sys.stderr)
        for (i, p) in enumerate(players):
            opps = []
            for (j, opp) in enumerate(players):
                if played_matrix[i][j] > 0:
                    opps.append(opp)
            print("[swissN] %20s:  %s" % (p.get_name(), ", ".join([ opp.get_name() for opp in opps])), file=sys.stderr)
        print("", file=sys.stderr)

    win_diff_matrix = []
    for p in players:
        win_diff_row = []
        for opponent in players:
            win_diff_row.append(abs(p.wins - opponent.wins))
        win_diff_matrix.append(win_diff_row)

    penalty_matrix = calculate_weight_matrix(games, players, played_matrix, win_diff_matrix, rank_by_wins, equal_wins_are_equal_players);
    penalty_matrix_size = len(players);

    best_grouping = None
    best_weight = None
    max_rematches = init_max_rematches
    max_wins_diff = init_max_win_diff
    max_wins = max([x.wins for x in players])
    min_wins = min([x.wins for x in players])

    start_time = time.time()

    table_penalty_cache = dict()

    # If the group of people on N wins, for any N, is not a multiple of the
    # table size, then don't bother looking for groupings where max_wins_diff
    # is 0.
    if max_wins_diff == 0:
        if group_size < 0:
            max_wins_diff = 0
        else:
            max_wins_diff = 1
            for wins in range(int(min_wins), int(max_wins + 1.5)):
                num = len([x for x in players if x.wins == wins])
                if num % group_size != 0:
                    if log:
                        sys.stderr.write("%d players on %d wins, not a multiple of %d, so not bothering to look for perfection\n" % (num, wins, group_size))
                    break
            else:
                max_wins_diff = 0

    while best_grouping is None:
        if log:
            sys.stderr.write("[swissN] Trying with max_wins_diff %d, max_rematches %d\n" % (max_wins_diff, max_rematches))
        for (groups, weight) in generate_all_groupings(group_size_list,
                played_matrix, win_diff_matrix, penalty_matrix, max_rematches,
                max_wins_diff, prune_set, start_time, limit_ms):
            if best_weight is None or weight < best_weight:
                best_weight = weight
                best_grouping = groups
                if log:
                    sys.stderr.write("[swissN] New best plan is %f, %s\n" % (best_weight, str(best_grouping)))
            if limit_ms and time.time() - start_time > float(limit_ms) / 1000.0:
                break
            if best_weight == 0:
                # Can't improve on this, which might happen if
                # equal_wins_are_equal_players is set and the size of each
                # win count group is a multiple of the group size.
                break
        if limit_ms and time.time() - start_time > float(limit_ms) / 1000.0:
            if log:
                sys.stderr.write("[swissN] That's time...\n")
            break
        if best_weight is None:
            if log:
                sys.stderr.write("[swissN] No groupings for max_wins_diff %d, max_rematches %d\n" % (max_wins_diff, max_rematches))
            max_wins_diff += 1
            if max_wins_diff > max_wins - min_wins:
                max_wins_diff = 0
                max_rematches += 1

    if best_grouping is None:
        return (None, None)

    weight = best_weight
    groups = best_grouping

    # If we can further improve this by some simple swaps of players between
    # tables, do it. Use up to the time we have left, or five seconds,
    # whichever is greater.
    time_remaining_ms = max(5000, limit_ms - (time.time() - start_time) * 1000)
    weight = hill_climb(groups, penalty_matrix, time_limit_ms=time_remaining_ms)

    # Sort the groups. If we're treating players on equal numbers of wins as
    # equal, sort by total wins on that table. Otherwise sort by total
    # standings position on that table.
    if equal_wins_are_equal_players:
        groups = sorted(groups, key=lambda x : sum([(players[y].wins) for y in x]), reverse=True)
    else:
        groups = sorted(groups, key=lambda x : sum([(players[y].position) for y in x]));

    if log:
        group_no = 1
        largest_pos_diff = 0
        largest_pos_diff_groups = []
        largest_win_diff = 0
        largest_win_diff_groups = []
        for g in groups:
            min_pos = min([players[p].position for p in g ])
            max_pos = max([players[p].position for p in g ])
            min_wins = min([players[p].wins for p in g ])
            max_wins = max([players[p].wins for p in g ])
            if max_pos - min_pos >= largest_pos_diff:
                if max_pos - min_pos > largest_pos_diff:
                    largest_pos_diff = max_pos - min_pos
                    largest_pos_diff_groups = [group_no]
                else:
                    largest_pos_diff_groups.append(group_no)
            if max_wins - min_wins >= largest_win_diff:
                if max_wins - min_wins > largest_win_diff:
                    largest_win_diff = max_wins - min_wins
                    largest_win_diff_groups = [group_no]
                else:
                    largest_win_diff_groups.append(group_no)
            print("[swissN] Table %2d, win difference %d, position difference %d, penalty %f:" % (group_no, max_wins - min_wins, max_pos - min_pos, get_table_penalty(penalty_matrix, g, None)), file=sys.stderr)
            for p in g:
                print("[swissN]     [%2d]  %4s  %dW  %s" % (p, to_ordinal(players[p].position), players[p].wins, players[p].name), file=sys.stderr)
            group_no += 1
        sys.stderr.write("[swissN] Max position difference: %d (table %s)\n" % ( largest_pos_diff, ", ".join(map(str, largest_pos_diff_groups))))
        sys.stderr.write("[swissN] Max win difference: %d (table %s)\n" % (largest_win_diff, ", ".join(map(str, largest_win_diff_groups))))

    player_groups = [];
    for g in groups:
        # "groups" is a list of tuples of integers, which are indices into
        # "players". Look up the player's name in "players"
        player_group = [];
        if len(g) == 2:
            # If it's a group of 2, and the first player in the group has played
            # first more than the second player in the group, swap them over.
            # If they've played first the same number of times, swap them over
            # with 50% probability.
            swap = False
            played_first_pc = [ players[g[x]].get_played_first_pc() for x in (0,1) ]
            if played_first_pc[0] > played_first_pc[1]:
                swap = True
            elif played_first_pc[0] == played_first_pc[1]:
                if random.random() >= 0.5:
                    swap = True
            if swap:
                g = [g[1], g[0]]

        for i in g:
            standings_player = players[i];
            for player in cdt_players:
                if player.name == standings_player.name:
                    player_group.append(player);
                    break;
            else:
                raise UnknownPlayerException();
        group_weight = get_table_penalty(penalty_matrix, g, None)
        player_groups.append(PlayerGroup(player_group, group_weight));

    return (weight, player_groups);


###############################################################################

class TestFailedException(Exception):
    pass

def lists_equal(l1, l2):
    if len(l1) != len(l2):
        return False
    for i in range(len(l1)):
        if type(l1[i]) != type(l2[i]):
            return False
        if type(l1[i]) == list:
            if not lists_equal(l1[i], l2[i]):
                return False
        elif l1[i] != l2[i]:
            return False
    return True

def unit_test_rotate_players(input_list, swapsies, expected_result):
    rotate_players(input_list, swapsies)
    if not lists_equal(input_list, expected_result):
        raise TestFailedException("rotate_players failed.\nSwapsies: %s\nExpected: %s\nObserved: %s" % (str(swapsies), str(expected_result), str(input_list)))

def unit_test_rotate_players_cycle_test(input_list, swapsies):
    # Check that calling rotate_players N times on the same list with a
    # swapsies argument N elements long returns the list to its original state.
    initial_list = []
    for x in input_list:
        initial_list.append(x[:])
    for i in range(len(swapsies)):
        rotate_players(input_list, swapsies)
        if i < len(swapsies) - 1 and lists_equal(input_list, initial_list):
            raise TestFailedException("rotate_players cycle test failed. List unexpectedly same as original after only %d rotations out of %d.\nList: %s" % (i + 1, len(swapsies), str(input_list)))
    if not lists_equal(input_list, initial_list):
        raise TestFailedException("rotate_players cycle test failed.\nSwapsies: %s\nCalls: %d\nExpected:%s\nObserved: %s" % (str(swapsies), len(swapsies), str(initial_list), str(input_list)))

def unit_test_generate_table_and_seat_indices(groups, count, dist, expected):
    observed = list(generate_table_and_seat_indices(groups, count, dist))
    if not lists_equal(expected, observed):
        raise TestFailedException("generate_table_and_seat_indices test failed.\nGroups: %s\ncount: %d\ndist: %d\nExpected: %s\nObserved: %s" % (groups, count, dist, str(expected), str(observed)))

def unit_tests():
    # Self-contained tests for the rotate_players and
    # generate_table_and_seat_indices functions.
    try:
        l = [[0, 1], [2, 3], [4, 5], [6, 7]]
        unit_test_rotate_players(l, [ (1, 0), (3, 1) ], [[0, 1], [7, 3], [4, 5], [6, 2]])
        unit_test_rotate_players(l, [ (1, 0), (3, 1) ], [[0, 1], [2, 3], [4, 5], [6, 7]])

        l = [ [0,1,2], [3,4,5], [6,7,8], [9,10,11], [12,13,14] ]
        unit_test_rotate_players(l, [ (2, 2), (4, 0), (0, 0) ],
                [ [8,1,2], [3,4,5], [6,7,12], [9,10,11], [ 0,13,14 ] ])
        unit_test_rotate_players(l, [ (2, 2), (4, 0), (0, 0) ],
                [ [12,1,2], [3,4,5], [6,7,0], [9,10,11], [ 8,13,14 ] ])
        unit_test_rotate_players(l, [ (2, 2), (4, 0), (0, 0) ],
                [ [0,1,2], [3,4,5], [6,7,8], [9,10,11], [12,13,14] ])

        unit_test_rotate_players_cycle_test(l, [ (0, 1), (2, 1) ])
        unit_test_rotate_players_cycle_test(l, [ (0, 1), (3, 2), (1, 1) ])
        unit_test_rotate_players_cycle_test(l, [ (0, 0), (1, 1), (2, 2), (3, 0) ])

        groups = [ [0,1], [2,3], [4,5] ]
        unit_test_generate_table_and_seat_indices(groups, 2, 2,
            [
                [ (0, 0), (2, 0) ],
                [ (0, 1), (2, 0) ],
                [ (0, 0), (2, 1) ],
                [ (0, 1), (2, 1) ]
            ]
        )
        groups = [ [0,1], [2,3], [4,5], [6,7] ]
        unit_test_generate_table_and_seat_indices(groups, 3, 2,
            [
                [ (0, 0), (1, 0), (2, 0) ],
                [ (0, 1), (1, 0), (2, 0) ],
                [ (0, 0), (1, 1), (2, 0) ],
                [ (0, 1), (1, 1), (2, 0) ],
                [ (0, 0), (1, 0), (2, 1) ],
                [ (0, 1), (1, 0), (2, 1) ],
                [ (0, 0), (1, 1), (2, 1) ],
                [ (0, 1), (1, 1), (2, 1) ],

                [ (1, 0), (2, 0), (3, 0) ],
                [ (1, 1), (2, 0), (3, 0) ],
                [ (1, 0), (2, 1), (3, 0) ],
                [ (1, 1), (2, 1), (3, 0) ],
                [ (1, 0), (2, 0), (3, 1) ],
                [ (1, 1), (2, 0), (3, 1) ],
                [ (1, 0), (2, 1), (3, 1) ],
                [ (1, 1), (2, 1), (3, 1) ]
            ]
        )
    except TestFailedException as e:
        print(str(e))
        return False
    return True
