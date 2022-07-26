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

#def add_game(games, players, round_no, table_no, name1, score1, score2, name2, tb=False):
#    p1 = None;
#    p2 = None;
#    division = 0
#
#    round_seq = len(filter(lambda x : x.round_no == round_no, games)) + 1;
#
#    for p in players:
#        if name1 == p.name:
#            p1 = p;
#            break;
#    else:
#        print "Unknown player %s" % name1;
#        raise UnknownPlayerException();
#
#    for p in players:
#        if name2 == p.name:
#            p2 = p;
#            break;
#    else:
#        print "Unknown player %s" % name2;
#        raise UnknownPlayerException();
#
#    g = countdowntourney.Game(round_no, round_seq, table_no, division, 'P', p1, p2, score1, score2, tb);
#    games.append(g);


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


###############################################################################

def cartesian_product(l):
    for i1 in range(len(l)):
        for i2 in range(i1 + 1, len(l)):
            yield(l[i1], l[i2])

if __name__ == "__main__":
    if len(sys.argv) > 1:
        limit_ms = int(sys.argv[1]);
    else:
        limit_ms = 30000;

    if len(sys.argv) > 2:
        random.seed(int(sys.argv[2]));

    # Test data
    group_size = -5
    players = [];
    players.append(countdowntourney.Player("Jack Hurst",1940));
    players.append(countdowntourney.Player("Giles Hutchings",1840));
    players.append(countdowntourney.Player("Jack Worsley",1880));
    players.append(countdowntourney.Player("Jonathan Rawlinson",1680));
    players.append(countdowntourney.Player("Innis Carson",2000));
    players.append(countdowntourney.Player("Mark Deeks",1900));
    players.append(countdowntourney.Player("Adam Gillard",1920));
    players.append(countdowntourney.Player("Conor Travers",1980));
    players.append(countdowntourney.Player("Jen Steadman",1860));
    players.append(countdowntourney.Player("Matt Bayfield",1800));
    players.append(countdowntourney.Player("David Barnard",1580));
    players.append(countdowntourney.Player("James Robinson",1760));
    players.append(countdowntourney.Player("Oliver Garner",1660));
    players.append(countdowntourney.Player("Graeme Cole",1780));
    players.append(countdowntourney.Player("Ryan Taylor",1640));
    players.append(countdowntourney.Player("Spanky McCullagh",1960));
    players.append(countdowntourney.Player("Chris Marshall",1360));
    players.append(countdowntourney.Player("Oli Moore",1380));
    players.append(countdowntourney.Player("Ahmed Mohamed",1820));
    players.append(countdowntourney.Player("Tom Rowell",1560));
    players.append(countdowntourney.Player("Rob Foster",1480));
    players.append(countdowntourney.Player("Gevin Chapwell",1440));
    players.append(countdowntourney.Player("Ian Volante",1520));
    players.append(countdowntourney.Player("Jon O'Neill",1740));
    players.append(countdowntourney.Player("Michelle Nevitt",1500));
    players.append(countdowntourney.Player("Heather Styles",1340));
    players.append(countdowntourney.Player("Tom Barnes",1460));
    players.append(countdowntourney.Player("Adam Dexter",1260));
    players.append(countdowntourney.Player("Phil Collinge",1320));
    players.append(countdowntourney.Player("Zarte Siempre",1720));
    players.append(countdowntourney.Player("Jeff Clayton",1540));
    players.append(countdowntourney.Player("Paul Sinha",1620));
    players.append(countdowntourney.Player("Ned Pendleton",1400));
    players.append(countdowntourney.Player("Michael Cullen",1300));
    players.append(countdowntourney.Player("Lauren Hamer",1600));
    players.append(countdowntourney.Player("Phyl Styles",1420));
    players.append(countdowntourney.Player("Will Howells",1240));
    players.append(countdowntourney.Player("Rachel Dixon",1280));
    players.append(countdowntourney.Player("Sue Sanders",1220));
    players.append(countdowntourney.Player("Apterous Nude",1700));
    players.append(countdowntourney.Player("Supee Juachan",1200));
    players.append(countdowntourney.Player("Clare James",1180));
    for p in range(43, 49):
        players.append(countdowntourney.Player("Player %d" % p, 1180 - (p - 43) * 20))

    (penalty, groups) = swissN_first_round(players, 3)

    def random_result(p1, p2):
        s1 = 0
        s2 = 0
        for i in range(9):
            if i in [0,1,2,4,5,6]:
                score = random.choice([4,5,6,6,7,7,7,8,8,18])
            elif i in [3,7]:
                score = random.choice([5,7,7,7,10,10,10,10])
            else:
                score = 10
            r1 = random.random() * (p1.rating + p2.rating)
            r2 = random.random() * (p1.rating + p2.rating)
            if r1 < p1.rating and r2 < p1.rating:
                s1 += score
            elif r1 >= p1.rating and r2 >= p1.rating:
                s2 += score
            else:
                s1 += score
                s2 += score
        return (s1, s2)



    games = [];
    # Play round 1
    group_no = 1
    for group in groups:
        for (p1, p2) in cartesian_product(group):
            (s1, s2) = random_result(p1, p2)
            add_game(games, players, 1, group_no, p1.name, s1, s2, p2.name)
            print("R%dT%d: %30s %3d - %-3d %-30s" % (1, group_no, p1.name, s1, s2, p2.name))
        group_no += 1

    #add_game(games, players, 1, 1, "Innis Carson", 82, 47, "Gevin Chapwell");
    #add_game(games, players, 1, 1, "Gevin Chapwell", 45, 69, "Zarte Siempre");
    #add_game(games, players, 1, 1, "Zarte Siempre", 39, 64, "Innis Carson");
    #add_game(games, players, 1, 2, "Apterous Nude", 37, 70, "Conor Travers");
    #add_game(games, players, 1, 2, "Conor Travers", 75, 44, "Phyl Styles");
    #add_game(games, players, 1, 2, "Phyl Styles", 49, 59, "Apterous Nude");
    #add_game(games, players, 1, 3, "Jonathan Rawlinson", 63, 58, "Spanky McCullagh");
    #add_game(games, players, 1, 3, "Ned Pendleton", 39, 67, "Jonathan Rawlinson");
    #add_game(games, players, 1, 3, "Spanky McCullagh", 61, 39, "Ned Pendleton");
    #add_game(games, players, 1, 4, "Jack Hurst", 72, 46, "Oli Moore");
    #add_game(games, players, 1, 4, "Oli Moore", 40, 55, "Oliver Garner");
    #add_game(games, players, 1, 4, "Oliver Garner", 80, 70, "Jack Hurst");
    #add_game(games, players, 1, 5, "Adam Gillard", 71, 44, "Chris Marshall");
    #add_game(games, players, 1, 5, "Chris Marshall", 38, 58, "Ryan Taylor");
    #add_game(games, players, 1, 5, "Ryan Taylor", 56, 63, "Adam Gillard");
    #add_game(games, players, 1, 6, "David Barnard", 64, 52, "Mark Deeks");
    #add_game(games, players, 1, 6, "Heather Styles", 27, 67, "David Barnard");
    #add_game(games, players, 1, 6, "Mark Deeks", 49, 38, "Heather Styles");
    #add_game(games, players, 1, 7, "Adam Dexter", 55, 45, "Lauren Hamer", tb=True);
    #add_game(games, players, 1, 7, "Jack Worsley", 65, 26, "Adam Dexter");
    #add_game(games, players, 1, 7, "Lauren Hamer", 60, 70, "Jack Worsley");
    #add_game(games, players, 1, 8, "Jen Steadman", 65, 55, "Phil Collinge");
    #add_game(games, players, 1, 8, "Paul Sinha", 44, 65, "Jen Steadman");
    #add_game(games, players, 1, 8, "Phil Collinge", 29, 37, "Paul Sinha");
    #add_game(games, players, 1, 9, "Giles Hutchings", 67, 37, "Michael Cullen");
    #add_game(games, players, 1, 9, "Michael Cullen", 17, 68, "Tom Rowell");
    #add_game(games, players, 1, 9, "Tom Rowell", 62, 73, "Giles Hutchings");
    #add_game(games, players, 1, 10, "Ahmed Mohamed", 61, 26, "Rachel Dixon");
    #add_game(games, players, 1, 10, "Jeff Clayton", 36, 60, "Ahmed Mohamed");
    #add_game(games, players, 1, 10, "Rachel Dixon", 44, 51, "Jeff Clayton");
    #add_game(games, players, 1, 11, "Ian Volante", 42, 59, "Matt Bayfield");
    #add_game(games, players, 1, 11, "Matt Bayfield", 70, 37, "Sue Sanders");
    #add_game(games, players, 1, 11, "Sue Sanders", 25, 70, "Ian Volante");
    #add_game(games, players, 1, 12, "Graeme Cole", 67, 31, "Supee Juachan");
    #add_game(games, players, 1, 12, "Michelle Nevitt", 34, 68, "Graeme Cole");
    #add_game(games, players, 1, 12, "Supee Juachan", 45, 53, "Michelle Nevitt");
    #add_game(games, players, 1, 13, "Clare James", 14, 64, "Rob Foster");
    #add_game(games, players, 1, 13, "James Robinson", 68, 29, "Clare James");
    #add_game(games, players, 1, 13, "Rob Foster", 55, 61, "James Robinson");
    #add_game(games, players, 1, 14, "Jon O'Neill", 58, 36, "Will Howells");
    #add_game(games, players, 1, 14, "Tom Barnes", 21, 56, "Jon O'Neill");
    #add_game(games, players, 1, 14, "Will Howells", 43, 42, "Tom Barnes");

    #add_game(games, players, 2, 1, "Ahmed Mohamed", 51, 61, "Innis Carson");
    #add_game(games, players, 2, 1, "Conor Travers", 82, 65, "Ahmed Mohamed");
    #add_game(games, players, 2, 1, "Innis Carson", 63, 60, "Conor Travers");
    #add_game(games, players, 2, 2, "Adam Gillard", 59, 55, "Giles Hutchings");
    #add_game(games, players, 2, 2, "Giles Hutchings", 61, 53, "James Robinson");
    #add_game(games, players, 2, 2, "James Robinson", 66, 57, "Adam Gillard");
    #add_game(games, players, 2, 3, "Graeme Cole", 43, 71, "Jack Worsley");
    #add_game(games, players, 2, 3, "Jack Worsley", 81, 63, "Matt Bayfield");
    #add_game(games, players, 2, 3, "Matt Bayfield", 67, 57, "Graeme Cole");
    #add_game(games, players, 2, 4, "Jen Steadman", 84, 74, "Jonathan Rawlinson");
    #add_game(games, players, 2, 4, "Jon O'Neill", 53, 50, "Jen Steadman");
    #add_game(games, players, 2, 4, "Jonathan Rawlinson", 58, 55, "Jon O'Neill");
    #add_game(games, players, 2, 5, "David Barnard", 69, 39, "Will Howells");
    #add_game(games, players, 2, 5, "Oliver Garner", 51, 67, "David Barnard");
    #add_game(games, players, 2, 5, "Will Howells", 43, 72, "Oliver Garner");
    #add_game(games, players, 2, 6, "Jack Hurst", 70, 38, "Zarte Siempre");
    #add_game(games, players, 2, 6, "Ryan Taylor", 55, 63, "Jack Hurst");
    #add_game(games, players, 2, 6, "Zarte Siempre", 49, 50, "Ryan Taylor");
    #add_game(games, players, 2, 7, "Ian Volante", 42, 49, "Rob Foster");
    #add_game(games, players, 2, 7, "Rob Foster", 54, 26, "Spanky McCullagh");
    #add_game(games, players, 2, 7, "Spanky McCullagh", 66, 41, "Ian Volante");
    #add_game(games, players, 2, 8, "Adam Dexter", 39, 54, "Michelle Nevitt");
    #add_game(games, players, 2, 8, "Apterous Nude", 40, 43, "Adam Dexter");
    #add_game(games, players, 2, 8, "Michelle Nevitt", 64, 40, "Apterous Nude");
    #add_game(games, players, 2, 9, "Jeff Clayton", 39, 76, "Mark Deeks");
    #add_game(games, players, 2, 9, "Mark Deeks", 69, 51, "Michael Cullen");
    #add_game(games, players, 2, 9, "Michael Cullen", 31, 64, "Jeff Clayton");
    #add_game(games, players, 2, 10, "Lauren Hamer", 59, 49, "Tom Rowell");
    #add_game(games, players, 2, 10, "Tom Barnes", 50, 47, "Lauren Hamer");
    #add_game(games, players, 2, 10, "Tom Rowell", 52, 42, "Tom Barnes");
    #add_game(games, players, 2, 11, "Heather Styles", 60, 43, "Paul Sinha");
    #add_game(games, players, 2, 11, "Paul Sinha", 57, 33, "Sue Sanders");
    #add_game(games, players, 2, 11, "Sue Sanders", 38, 59, "Heather Styles");
    #add_game(games, players, 2, 12, "Ned Pendleton", 59, 52, "Phyl Styles");
    #add_game(games, players, 2, 12, "Phil Collinge", 46, 29, "Ned Pendleton");
    #add_game(games, players, 2, 12, "Phyl Styles", 42, 51, "Phil Collinge");
    #add_game(games, players, 2, 13, "Oli Moore", 51, 33, "Gevin Chapwell");
    #add_game(games, players, 2, 13, "Supee Juachan", 36, 63, "Oli Moore");
    #add_game(games, players, 2, 13, "Gevin Chapwell", 61, 34, "Supee Juachan");
    #add_game(games, players, 2, 14, "Chris Marshall", 44, 33, "Rachel Dixon");
    #add_game(games, players, 2, 14, "Clare James", 26, 58, "Chris Marshall");
    #add_game(games, players, 2, 14, "Rachel Dixon", 48, 40, "Clare James");

    #add_game(games, players, 3, 1, "Innis Carson", 62, 49, "Oliver Garner");
    #add_game(games, players, 3, 1, "Jen Steadman", 62, 48, "Innis Carson");
    #add_game(games, players, 3, 1, "Oliver Garner", 51, 49, "Jen Steadman");
    #add_game(games, players, 3, 2, "Adam Gillard", 68, 58, "Conor Travers");
    #add_game(games, players, 3, 2, "Conor Travers", 70, 53, "David Barnard");
    #add_game(games, players, 3, 2, "David Barnard", 52, 54, "Adam Gillard");
    #add_game(games, players, 3, 3, "Giles Hutchings", 76, 46, "Jon O'Neill");
    #add_game(games, players, 3, 3, "Jack Worsley", 59, 69, "Giles Hutchings");
    #add_game(games, players, 3, 3, "Jon O'Neill", 39, 54, "Jack Worsley");
    #add_game(games, players, 3, 4, "Jack Hurst", 68, 50, "James Robinson");
    #add_game(games, players, 3, 4, "James Robinson", 70, 40, "Michelle Nevitt");
    #add_game(games, players, 3, 4, "Michelle Nevitt", 58, 71, "Jack Hurst");
    #add_game(games, players, 3, 5, "Jonathan Rawlinson", 59, 45, "Matt Bayfield");
    #add_game(games, players, 3, 5, "Matt Bayfield", 68, 58, "Rob Foster");
    #add_game(games, players, 3, 5, "Rob Foster", 44, 61, "Jonathan Rawlinson");
    #add_game(games, players, 3, 6, "Mark Deeks", 63, 51, "Paul Sinha");
    #add_game(games, players, 3, 6, "Paul Sinha", 37, 53, "Tom Rowell");
    #add_game(games, players, 3, 6, "Tom Rowell", 46, 67, "Mark Deeks");
    #add_game(games, players, 3, 7, "Oli Moore", 82, 69, "Phil Collinge");
    #add_game(games, players, 3, 7, "Phil Collinge", 37, 54, "Spanky McCullagh");
    #add_game(games, players, 3, 7, "Spanky McCullagh", 67, 65, "Oli Moore");
    #add_game(games, players, 3, 8, "Heather Styles", 32, 71, "Ryan Taylor");
    #add_game(games, players, 3, 8, "Jeff Clayton", 54, 59, "Heather Styles");
    #add_game(games, players, 3, 8, "Ryan Taylor", 43, 32, "Jeff Clayton");
    #add_game(games, players, 3, 9, "Ahmed Mohamed", 62, 41, "Will Howells");
    #add_game(games, players, 3, 9, "Graeme Cole", 50, 46, "Ahmed Mohamed");
    #add_game(games, players, 3, 9, "Will Howells", 41, 55, "Graeme Cole");
    #add_game(games, players, 3, 10, "Chris Marshall", 51, 38, "Zarte Siempre");
    #add_game(games, players, 3, 10, "Lauren Hamer", 27, 44, "Chris Marshall");
    #add_game(games, players, 3, 10, "Zarte Siempre", 52, 50, "Lauren Hamer");
    #add_game(games, players, 3, 11, "Adam Dexter", 45, 61, "Gevin Chapwell");
    #add_game(games, players, 3, 11, "Rachel Dixon", 45, 53, "Adam Dexter");
    #add_game(games, players, 3, 11, "Gevin Chapwell", 64, 35, "Rachel Dixon");
    #add_game(games, players, 3, 12, "Apterous Nude", 40, 53, "Ned Pendleton");
    #add_game(games, players, 3, 12, "Ned Pendleton", 38, 42, "Tom Barnes");
    #add_game(games, players, 3, 12, "Tom Barnes", 59, 40, "Apterous Nude");
    #add_game(games, players, 3, 13, "Ian Volante", 63, 41, "Supee Juachan");
    #add_game(games, players, 3, 13, "Phyl Styles", 35, 52, "Ian Volante");
    #add_game(games, players, 3, 13, "Supee Juachan", 41, 42, "Phyl Styles");
    #add_game(games, players, 3, 14, "Clare James", 16, 51, "Sue Sanders");
    #add_game(games, players, 3, 14, "Michael Cullen", 60, 17, "Clare James");
    #add_game(games, players, 3, 14, "Sue Sanders", 40, 46, "Michael Cullen");


    def player_wins(games, player):
        wins = 0;
        for g in games:
            if g.contains_player(player) and g.is_complete():
                score = g.get_player_score(player);
                opp_score = g.get_opponent_score(player);
                if score > opp_score:
                    wins += 1;
        return wins;

    def player_points(games, player):
        points = 0;
        for g in games:
            if g.contains_player(player) and g.is_complete():
                if g.tb:
                    points += g.get_opponent_score(player);
                else:
                    points += g.get_player_score(player);
        return points;

    (weight, player_groups) = swissN(games, players, group_size, rank_by_wins=True, limit_ms=limit_ms);

    print("Weight %d" % weight);
    table_no = 1;
    for group in player_groups:
        legend = ["%s (%d-%d)" % (x.name, player_wins(games, x), player_points(games, x)) for x in group];
        print("T%2d (%5d) %s" % (table_no, group.weight, ", ".join(legend)));

        # Check there are no rematches
        names = [x.name for x in group];
        for g in games:
            if g.p1.name in names and g.p2.name in names:
                print("Rematch on table %d!" % table_no);
        table_no += 1;

    sys.exit(0);
