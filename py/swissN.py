#!/usr/bin/python3

import sys
import time
import countdowntourney
import random

HUGE_PENALTY = 1000000000

class StandingsPlayer(object):
    def __init__(self, name, rating, wins, position, played, played_first, avoid_prune):
        self.name = name;
        self.rating = rating
        if rating == 0:
            self.is_prune = True;
        else:
            self.is_prune = False;
        self.wins = wins
        self.position = position
        self.games_played = played
        self.games_played_first = played_first
        self.avoid_prune = avoid_prune

    def get_name(self):
        return self.name

    def get_rating(self):
        return self.rating

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
def get_penalty(games, p1, p2, num_played, win_diff, rank_by_wins=True):
    pen = 0;

    # No, you are not allowed to play yourself
    if p1.name == p2.name:
        return HUGE_PENALTY ** 2;

    # Don't want two players meeting twice
    pen += HUGE_PENALTY * num_played

    # Don't want two prunes drawn against each other
    if p1.is_prune and p2.is_prune:
        pen += HUGE_PENALTY;

    # If one of these two players is a prune, then if the other player has
    # played a prune before, make it unlikely they will play a prune again
    if p1.get_rating() == 0 or p2.get_rating() == 0 and (p1.get_rating() != 0 or p2.get_rating() != 0):
        if p1.get_rating() == 0:
            human = p2
            prune = p1
        else:
            human = p1
            prune = p2

        for g in games:
            if g.p1.get_name() == human.get_name():
                if g.p2.get_rating() == 0:
                    pen += HUGE_PENALTY
            elif g.p2.get_name() == human.get_name():
                if g.p1.get_rating() == 0:
                    pen += HUGE_PENALTY

    # If two players have a different number of wins, apply a penalty.
    # Fixtures between players whose win counts differ by 1 are usually
    # unavoidable, but there should be exponentially harsher penalties for
    # putting people on the same table whose win counts differ by more.
    # Take the difference in standings position into consideration as well, so
    # that we group together people in roughly the same part of the standings.
    pos_diff = abs(p1.position - p2.position)
    if rank_by_wins:
        pen += ( 10 ** min(float(win_diff), 5) ) * ( 10 * (float(pos_diff) / float(pos_diff + 1)))
    else:
        pen += 10 * (float(pos_diff) / float(pos_diff + 1))

    # Square the penalty, to magnify the difference between a large
    # penalty and a smaller one.
    pen = pen ** 2;

    return pen;

# Calculate the matrix of penalties for each pair of players.
def calculate_weight_matrix(games, players, played_matrix, win_diff_matrix, rank_by_wins=True):
    matrix_size = len(players);
    matrix = [];
    for i1 in range(matrix_size):
        p1 = players[i1]
        vector = [];

        # To make the graph symmetric, in case get_penalty(p1, p2) does not
        # equal get_penalty(p2, p1) for some reason, the weight between p1
        # and p2 is max(penalty(p1, p2), penalty(p2, p1))

        for i2 in range(matrix_size):
            p2 = players[i2]
            pen = max(get_penalty(games, p1, p2, played_matrix[i1][i2],
                win_diff_matrix[i1][i2], rank_by_wins),
                get_penalty(games, p2, p1, played_matrix[i2][i1],
                    win_diff_matrix[i2][i1], rank_by_wins)
            );
            vector.append(pen);

        matrix.append(vector);

    for i in range(matrix_size):
        for j in range(matrix_size):
            if matrix[i][j] != matrix[j][i]:
                print("i %d, j %d, matrix[i][j] %f, matrix[j][i] %f!" % (i, j, matrix[i][j], matrix[j][i]));

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
        return float(penalty_sum) / num_samples
    #if table_penalty_cache is not None and len(table) <= 5:
    #    table_penalty_cache[table] = penalty
    #return penalty

def total_penalty(weight_matrix, tables, table_penalty_cache):
    penalty = 0
    for table in tables:
        penalty += get_table_penalty(weight_matrix, table, table_penalty_cache)
    return penalty

def generate_sets(l, num):
    if num == len(l):
        yield l[:]
    elif num == 1:
        for e in l:
            yield [e]
    elif num < len(l):
        for i in range(len(l) - (num - 1)):
            for remainder in generate_sets(l[(i+1):], num - 1):
                yield [l[i]] + remainder

def generate_all_groupings_aux(group_size_list, possible_opponents, depth, start_time, limit_ms):
    group_size = group_size_list[0]
    players_ordered = sorted(possible_opponents)

    if time.time() > start_time + limit_ms / 1000.0:
        # Out of time
        return

    if players_ordered:
        p = players_ordered[0]
        opps = possible_opponents[p]
        #sys.stderr.write("%*slooking for opponents for %d from %s\n" % (depth, "", p, str(opps)))
        if len(opps) >= group_size - 1:
            for remainder in generate_sets(opps, group_size - 1):
                reject = False
                for i in range(len(remainder) - 1):
                    for j in range(i + 1, len(remainder)):
                        if remainder[j] not in possible_opponents[remainder[i]]:
                            reject = True
                            break
                    if reject:
                        break
                if reject:
                    continue

                candidate_table = [p] + remainder
                #print len(remainder)
                new_possible_opponents = dict()
                for pp in possible_opponents:
                    if pp not in candidate_table:
                        new_opps = possible_opponents[pp][:]
                        for c in candidate_table:
                            if c in new_opps:
                                new_opps.remove(c)
                        new_possible_opponents[pp] = new_opps
                if len(new_possible_opponents) == 0:
                    # This is the last table
                    yield [candidate_table]
                else:
                    for remainder2 in generate_all_groupings_aux(group_size_list[1:], new_possible_opponents, depth + 1, start_time, limit_ms):
                        yield [candidate_table] + remainder2



def generate_all_groupings(played_matrix, win_diff_matrix, group_size_list, max_rematches, max_wins_diff, prune_set, start_time, limit_ms):
    num_players = len(played_matrix)
    possible_opponents = dict()
    if sum(group_size_list) != num_players:
        raise InvalidGroupSizeListException()
    for p in range(num_players):
        opponents = []
        for opp in range(num_players):
            if p != opp:
                if played_matrix[p][opp] <= max_rematches and win_diff_matrix[p][opp] <= max_wins_diff and not(p in prune_set and opp in prune_set):
                    #print "played_matrix[%d][%d] %d" % (p, opp, played_matrix[p][opp])
                    opponents.append(opp)
        possible_opponents[p] = opponents
    return generate_all_groupings_aux(group_size_list, possible_opponents, 0, start_time, limit_ms)

class PlayerGroup(object):
    def __init__(self, player_list, weight):
        self.player_list = player_list;
        self.weight = weight;

    def __getitem__(self, i):
        return self.player_list[i];

    def __len__(self):
        return len(self.player_list);

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

def swissN(games, cdt_players, standings, group_size, rank_by_wins=True, limit_ms=None, init_max_rematches=0, init_max_win_diff=0, ignore_rematches_before=None):
    log = True
    players = [];
    for p in cdt_players:
        for s in standings:
            if s.name == p.name:
                players.append(StandingsPlayer(p.name, p.rating, s.wins + float(s.draws) / 2, s.position, s.played, s.played_first, p.is_avoiding_prune()));
                break
        else:
            print(p.name + " not in standings table for this division")
            raise PlayerNotInStandingsException()

    # Sort "players" by their position in the standings table, as that means
    # we try the most likely combinations first when later on we generate all
    # the combinations we can in a limited time.
    players = sorted(players, key=lambda x : x.position)

    if group_size == -5:
        if len(players) < 8:
            raise IllegalNumberOfPlayersException()
        group_size_list = countdowntourney.get_5_3_table_sizes(len(players))
    else:
        group_size_list = [ group_size for i in range(len(players) // group_size) ]

    played_matrix = []
    for p in players:
        played_row = []
        for opponent in players:
            count = 0
            for g in games:
                if g.is_between_names(p.name, opponent.name) and (ignore_rematches_before is None or g.round_no >= ignore_rematches_before):
                    count += 1
            played_row.append(count)
        played_matrix.append(played_row)

    # Identify the prunes, and put their indices in the prune_set set
    prune_set = set()
    a_prune_index = None
    for pi in range(len(players)):
        if players[pi].rating == 0:
            prune_set.add(pi)
            if a_prune_index is None:
                a_prune_index = pi

    # If there is at least one prune, and any players should be treated as
    # having played prune even though they haven't, fiddle the matrix
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

    win_diff_matrix = []
    for p in players:
        win_diff_row = []
        for opponent in players:
            win_diff_row.append(abs(p.wins - opponent.wins))
        win_diff_matrix.append(win_diff_row)

    matrix = calculate_weight_matrix(games, players, played_matrix, win_diff_matrix, rank_by_wins);
    matrix_size = len(players);

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
        for groups in generate_all_groupings(played_matrix, win_diff_matrix, group_size_list, max_rematches, max_wins_diff, prune_set, start_time, limit_ms):
            weight = total_penalty(matrix, groups, table_penalty_cache)
            if best_weight is None or weight < best_weight:
                best_weight = weight
                best_grouping = groups
                if log:
                    sys.stderr.write("[swissN] New best plan is %f, %s\n" % (best_weight, str(best_grouping)))
            if limit_ms and time.time() - start_time > float(limit_ms) / 1000.0:
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

    #(weight, groups) = best_grouping(matrix, range(matrix_size), group_size, limit_ms=limit_ms)

    if best_grouping is None:
        return (None, None)

    weight = best_weight
    groups = best_grouping

    # Sort the groups so the players high up in the standings are on
    # low-numbered tables
    groups = sorted(groups, key=lambda x : sum([(players[y].position) for y in x]));

    if log:
        group_no = 1
        for g in groups:
            sys.stderr.write("[swissN] Table %2d:" % group_no)
            for p in g:
                sys.stderr.write(" [%d %s (%d, %dw)]" % (p + 1, players[p].name, players[p].position, players[p].wins))
            sys.stderr.write("\n")
            group_no += 1

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
        group_weight = get_table_penalty(matrix, g, None)
        player_groups.append(PlayerGroup(player_group, group_weight));

    return (weight, player_groups);
