#!/usr/bin/python3

import sys;
import time;
import countdowntourney;

class StandingsPlayer(object):
    def __init__(self, name, rating):
        self.name = name;
        if rating == 0:
            self.is_prune = True;
        else:
            self.is_prune = False;
        self.wins = 0
        self.points = 0
        self.rating = rating

    def get_name(self):
        return self.name

    def get_rating(self):
        return self.rating

    def post_result(self, myscore, theirscore, tb=False):
        if myscore > theirscore:
            self.wins += 1;
        if tb:
            self.points += min(myscore, theirscore);
        else:
            self.points += myscore;


class UnknownPlayerException(object):
    pass;

class IllegalNumberOfPlayersException(object):
    pass;

def add_game(games, players, round_no, table_no, name1, score1, score2, name2, tb=False):
    p1 = None;
    p2 = None;
    division = 0

    round_seq = len([x for x in games if x.round_no == round_no]) + 1;

    for p in players:
        if name1 == p.name:
            p1 = p;
            break;
    else:
        print("Unknown player %s" % name1);
        raise UnknownPlayerException();

    for p in players:
        if name2 == p.name:
            p2 = p;
            break;
    else:
        print("Unknown player %s" % name2);
        raise UnknownPlayerException();

    g = countdowntourney.Game(round_no, round_seq, table_no, division, 'P', p1, p2, score1, score2, tb);
    games.append(g);



# Calculate number of penalty points associated with p1 playing p2. This is
# also called the "weighting".
def get_penalty(games, p1, p2, rank_by_wins=True):
    pen = 0;

    if p1.name == p2.name:
        return 100000000;

    # Don't want two players meeting twice
    for g in games:
        if g.is_between_names(p1.name, p2.name):
            pen += 1000000;

    # Don't want two prunes drawn against each other
    if p1.is_prune and p2.is_prune:
        pen += 1000000;

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
                    pen += 1000000
            elif g.p2.get_name() == human.get_name():
                if g.p1.get_rating() == 0:
                    pen += 1000000

    # If two players have a different number of wins, apply a penalty.
    # Fixtures between players whose win counts differ by 1 are usually
    # unavoidable, but there should be exponentially harsher penalties for
    # putting people on the same table whose win counts differ by more.
    # Take the difference in points into consideration as well, so that
    # we group together people in roughly the same part of the standings.
    if rank_by_wins and (p1.wins != p2.wins or p1.points != p2.points):
        pen += 10 ** min([abs((float(p1.wins) + float(p1.points) / 500.0) - (float(p2.wins) + float(p2.points) / 500.0)), 5]);

    # Small penalty if two players have a markedly different number of points.
    if not rank_by_wins:
        pen += abs(p1.points - p2.points) / 4;

    # Square the penalty, to magnify the difference between a large
    # penalty and a smaller one.
    pen = pen ** 2;

    return pen;

# Calculate the matrix of penalties for each pair of players.
def calculate_weight_matrix(games, players, rank_by_wins=True):
    matrix_size = len(players);
    matrix = [];
    for p1 in players:
        vector = [];
        # To make the graph symmetric, in case get_penalty(p1, p2) does not
        # equal get_penalty(p2, p1) for some reason, the weight between p1
        # and p2 is max(penalty(p1, p2), penalty(p2, p1))

        for p2 in players:
            pen = max(get_penalty(games, p1, p2, rank_by_wins), get_penalty(games, p2, p1, rank_by_wins));
            vector.append(pen);

        matrix.append(vector);

    for i in range(matrix_size):
        for j in range(matrix_size):
            if matrix[i][j] != matrix[j][i]:
                print("i %d, j %d, matrix[i][j] %f, matrix[j][i] %f!" % (i, j, matrix[i][j], matrix[j][i]));

    return matrix;


# This function finds the best way of grouping the numbers "player_indices"
# into groups of three, to minimise the penalty weighting for each group.
#
# First, we arrange the best N starting groups, for some convenient value of
# N (for example 10). Of all possible groups of three players from the numbers
# in player_indices, these are the best N. For each of these groups, we
# recursively find the best grouping for the remainder of the players, and
# then we've got 10 candidate arrangements. We return the best one.
#
# We try to keep within limit_ms milliseconds.
#
def best_grouping(weight_cube, player_indices, limit_ms=None, depth=0, best_total_so_far=None, result_cache=None):
    best_groups = [];
    size = len(player_indices);
    max_log_depth = -1;

    # Initialise the result cache
    if result_cache is None:
        result_cache = dict();

    # If we've already solved this problem, let's not bother solving it again.
    if tuple(player_indices) in result_cache:
        return result_cache[tuple(player_indices)];

    # Base case: there's only one arragement of three players. We just need to
    # return the weight.
    if size == 3:
        return (weight_cube[player_indices[0]][player_indices[1]][player_indices[2]], [player_indices]);

    # A naive solution might make a table by picking i,j,k from player_indices
    # where weight_cube[i][j][k] is the minimum, then call that a table and
    # recurse to find the seating arrangement for what's left. This sometimes
    # works but you can end up painting yourself into a corner - for example,
    # ending up with six players to divide among two tables, but they've mostly
    # all played each other.
    #
    # So we need to be able to backtrack. For this reason, we come up with
    # the best_max best (i,j,k), rather than just the best one. We solve the
    # problem for each of those, and hopefully we'll get at least one that's
    # acceptable.
    if size < 10:
        best_max = None;
    else:
        best_max = 20;

    # Get some ideas for which three players to put on a table.
    for i in player_indices:
        for j in player_indices:
            if j > i:
                for k in player_indices:
                    if k > j and k > i:
                        weight = weight_cube[i][j][k];
                        entry = (weight, [i,j,k]);
                        if best_max is None:
                            best_groups.append(entry);
                        elif len(best_groups) < best_max or weight < best_groups[-1][0]:
                            best_groups.append(entry);
                            best_groups = sorted(best_groups, key=lambda x : x[0])[0:best_max];

    #if depth == 0:
    #    print "size %d, len(best_groups) %d" % (size, len(best_groups));
    if best_max is None:
        best_groups = sorted(best_groups, key=lambda x : x[0]);

    overall_best_group = None;
    overall_best_weight = None;
    iter_num = 0;

    indent = "";
    for x in range(depth):
        indent += " ";

    start_time = time.time();

    # Each table in best_groups is a triple (i,j,k), where
    # weight_cube[i][j][k] is low. All we have to do, for each of these
    # triples, is work out, recursively, what the best seating arrangement is
    # for player_indices minus [i,j,k]. Then we'll pick the best one.
    for entry in best_groups:
        (weight, group) = entry;
        iter_num += 1;

        # If the weight of this table is greater than the weight of the best
        # whole arrangement found so far, don't bother proceeding with it.
        if best_total_so_far is not None and weight > best_total_so_far:
            continue;

        # players_remaining = player_indices - [i,j,k]
        players_remaining = player_indices[:];
        for p in group:
            players_remaining.remove(p);

        # How long do we want to spend on this step? Work out how much time we
        # have left. If this is negative for some reason, spend a very short
        # amount of time on it.
        #
        # Otherwise, for the higher levels of recursion we use half the time
        # remaining. This is because early iterations are expected to run
        # slower because the result cache hasn't had a chance to be
        # populated. So if we've got 16 seconds, then we'll allocate 8 seconds
        # for the first entry in best_groups, 4 for the second, 2 for the
        # third, and so on.
        #
        # For lower levels of recursion we'll just use a fair share of the
        # time we have left, that is, time left divided by the number of
        # groups still to check.
        #
        # Lastly, if the problem is very small (number of players < 10)
        # then don't impose a time limit.

        if size < 10 or limit_ms is None:
            step_time_limit=None;
        else:
            time_left_ms = 1000 * ((start_time + limit_ms / 1000.0) - time.time());
            if time_left_ms < 0:
                step_time_limit = 10;
            else:
                if depth <= 1:
                    step_time_limit = time_left_ms / 2;
                else:
                    step_time_limit = time_left_ms / (len(best_groups) - iter_num + 1);
                if step_time_limit < 10:
                    step_time_limit = 10;

        if depth <= max_log_depth:
            print("[%02d] %sGroup %d of %d, best so far %d, %sms allotted" % (depth, indent, iter_num, len(best_groups), best_total_so_far if best_total_so_far else 0, str(int(step_time_limit) if step_time_limit is not None else "?")));

        # The recursive bit.
        (total_weight, grouping) = best_grouping(weight_cube, players_remaining, step_time_limit, depth + 1, best_total_so_far, result_cache);

        if total_weight is None:
            # If total_weight is None, then it means it couldn't beat the
            # best_total_so_far so it returned empty-handed.
            result_cache[tuple(players_remaining)] = (None, None);
            continue;

        # If the total weight of the grouping of players_remaining plus the
        # weight of the group we picked is less than the best we've found
        # so far, update overall_best_weight and overall_best_group.
        if overall_best_weight is None or total_weight + weight < overall_best_weight:
            overall_best_weight = total_weight + weight;
            overall_best_group = [group] + grouping;
            if best_total_so_far is None or overall_best_weight < best_total_so_far:
                best_total_so_far = overall_best_weight;

        #max_group_weight = 0;
        #for group in overall_best_group:
        #    group_weight = weight_cube[group[0]][group[1]][group[2]];
        #    if group_weight > max_group_weight:
        #        max_group_weight = group_weight;

        #if depth < 3:
        #    print "[%02d] %sbest weight %d, num groups %d, max weight %d" % (depth, indent, overall_best_weight, len(overall_best_group), max_group_weight);

        # If we've run out of time, call proceedings to a halt after one
        # iteration.
        if size >= 10 and limit_ms is not None and start_time + limit_ms / 1000.0 < time.time():
            if depth <= max_log_depth:
                print("[%02d] %sout of time!" % (depth, indent));
            break;

    # We're ready to return our result. Put it in the result cache in case
    # we end up trying to solve this problem again.
    result_cache[tuple(player_indices)] = (overall_best_weight, overall_best_group);

    return (overall_best_weight, overall_best_group);

class PlayerGroup(object):
    def __init__(self, player_list, weight):
        self.player_list = player_list;
        self.weight = weight;

    def __getitem__(self, i):
        return self.player_list[i];

    def __len__(self):
        return 3;

def swiss3_first_round(cdt_players):
    if len(cdt_players) % 3 != 0:
        raise IllegalNumberOfPlayersException()

    # Put the players in rating order, largest to smallest
    players = sorted(cdt_players, key=lambda x : x.rating, reverse=True);

    num_groups = len(cdt_players) // 3;
    groups = [];
    for i in range(num_groups):
        player_list = [];
        for j in range(3):
            player_list.append(players[j * num_groups + i]);
        groups.append(PlayerGroup(player_list, 0));
    return (0, groups);

def swiss3(games, cdt_players, rank_by_wins=True, limit_ms=None):
    players = [];
    for p in cdt_players:
        players.append(StandingsPlayer(p.name, p.rating));

    # Work out wins and points totals for all the players
    for g in games:
        for p in players:
            if p.name == g.p1.name:
                p.post_result(g.s1, g.s2, g.tb);
            elif p.name == g.p2.name:
                p.post_result(g.s2, g.s1, g.tb);

    players = sorted(players, key=lambda p : (p.wins, p.points), reverse=True);
    matrix = calculate_weight_matrix(games, players, rank_by_wins);
    matrix_size = len(players);
    weighted_companion_cube = [];
    for i in range(0, matrix_size):
        vj = [];
        for j in range(0, matrix_size):
            vk = [];
            for k in range(0, matrix_size):
                vk.append(matrix[i][j] + matrix[j][k] + matrix[k][i]);
            vj.append(vk);
        weighted_companion_cube.append(vj);

    (weight, groups) = best_grouping(weighted_companion_cube, list(range(matrix_size)), limit_ms=limit_ms);

    # Sort the groups so the highest-performing players are on low-numbered
    # tables
    groups = sorted(groups, key=lambda x : sum([players[y].wins * 10000 + players[y].points for y in x]), reverse=True);

    player_groups = [];
    for g in groups:
        # "groups" is a list of triples of integers, which are indices into
        # "players". Look up the player's name in "players"
        player_group = [];
        for i in g:
            standings_player = players[i];
            for player in cdt_players:
                if player.name == standings_player.name:
                    player_group.append(player);
                    break;
            else:
                raise UnknownPlayerException();
        group_weight = weighted_companion_cube[g[0]][g[1]][g[2]];
        player_groups.append(PlayerGroup(player_group, group_weight));

    return (weight, player_groups);


###############################################################################

if __name__ == "__main__":
    if len(sys.argv) > 1:
        limit_ms = int(sys.argv[1]);
    else:
        limit_ms = 10000;

    # Test data
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


    games = [];
    add_game(games, players, 1, 1, "Innis Carson", 82, 47, "Gevin Chapwell");
    add_game(games, players, 1, 1, "Gevin Chapwell", 45, 69, "Zarte Siempre");
    add_game(games, players, 1, 1, "Zarte Siempre", 39, 64, "Innis Carson");
    add_game(games, players, 1, 2, "Apterous Nude", 37, 70, "Conor Travers");
    add_game(games, players, 1, 2, "Conor Travers", 75, 44, "Phyl Styles");
    add_game(games, players, 1, 2, "Phyl Styles", 49, 59, "Apterous Nude");
    add_game(games, players, 1, 3, "Jonathan Rawlinson", 63, 58, "Spanky McCullagh");
    add_game(games, players, 1, 3, "Ned Pendleton", 39, 67, "Jonathan Rawlinson");
    add_game(games, players, 1, 3, "Spanky McCullagh", 61, 39, "Ned Pendleton");
    add_game(games, players, 1, 4, "Jack Hurst", 72, 46, "Oli Moore");
    add_game(games, players, 1, 4, "Oli Moore", 40, 55, "Oliver Garner");
    add_game(games, players, 1, 4, "Oliver Garner", 80, 70, "Jack Hurst");
    add_game(games, players, 1, 5, "Adam Gillard", 71, 44, "Chris Marshall");
    add_game(games, players, 1, 5, "Chris Marshall", 38, 58, "Ryan Taylor");
    add_game(games, players, 1, 5, "Ryan Taylor", 56, 63, "Adam Gillard");
    add_game(games, players, 1, 6, "David Barnard", 64, 52, "Mark Deeks");
    add_game(games, players, 1, 6, "Heather Styles", 27, 67, "David Barnard");
    add_game(games, players, 1, 6, "Mark Deeks", 49, 38, "Heather Styles");
    add_game(games, players, 1, 7, "Adam Dexter", 55, 45, "Lauren Hamer", tb=True);
    add_game(games, players, 1, 7, "Jack Worsley", 65, 26, "Adam Dexter");
    add_game(games, players, 1, 7, "Lauren Hamer", 60, 70, "Jack Worsley");
    add_game(games, players, 1, 8, "Jen Steadman", 65, 55, "Phil Collinge");
    add_game(games, players, 1, 8, "Paul Sinha", 44, 65, "Jen Steadman");
    add_game(games, players, 1, 8, "Phil Collinge", 29, 37, "Paul Sinha");
    add_game(games, players, 1, 9, "Giles Hutchings", 67, 37, "Michael Cullen");
    add_game(games, players, 1, 9, "Michael Cullen", 17, 68, "Tom Rowell");
    add_game(games, players, 1, 9, "Tom Rowell", 62, 73, "Giles Hutchings");
    add_game(games, players, 1, 10, "Ahmed Mohamed", 61, 26, "Rachel Dixon");
    add_game(games, players, 1, 10, "Jeff Clayton", 36, 60, "Ahmed Mohamed");
    add_game(games, players, 1, 10, "Rachel Dixon", 44, 51, "Jeff Clayton");
    add_game(games, players, 1, 11, "Ian Volante", 42, 59, "Matt Bayfield");
    add_game(games, players, 1, 11, "Matt Bayfield", 70, 37, "Sue Sanders");
    add_game(games, players, 1, 11, "Sue Sanders", 25, 70, "Ian Volante");
    add_game(games, players, 1, 12, "Graeme Cole", 67, 31, "Supee Juachan");
    add_game(games, players, 1, 12, "Michelle Nevitt", 34, 68, "Graeme Cole");
    add_game(games, players, 1, 12, "Supee Juachan", 45, 53, "Michelle Nevitt");
    add_game(games, players, 1, 13, "Clare James", 14, 64, "Rob Foster");
    add_game(games, players, 1, 13, "James Robinson", 68, 29, "Clare James");
    add_game(games, players, 1, 13, "Rob Foster", 55, 61, "James Robinson");
    add_game(games, players, 1, 14, "Jon O'Neill", 58, 36, "Will Howells");
    add_game(games, players, 1, 14, "Tom Barnes", 21, 56, "Jon O'Neill");
    add_game(games, players, 1, 14, "Will Howells", 43, 42, "Tom Barnes");

    add_game(games, players, 2, 1, "Ahmed Mohamed", 51, 61, "Innis Carson");
    add_game(games, players, 2, 1, "Conor Travers", 82, 65, "Ahmed Mohamed");
    add_game(games, players, 2, 1, "Innis Carson", 63, 60, "Conor Travers");
    add_game(games, players, 2, 2, "Adam Gillard", 59, 55, "Giles Hutchings");
    add_game(games, players, 2, 2, "Giles Hutchings", 61, 53, "James Robinson");
    add_game(games, players, 2, 2, "James Robinson", 66, 57, "Adam Gillard");
    add_game(games, players, 2, 3, "Graeme Cole", 43, 71, "Jack Worsley");
    add_game(games, players, 2, 3, "Jack Worsley", 81, 63, "Matt Bayfield");
    add_game(games, players, 2, 3, "Matt Bayfield", 67, 57, "Graeme Cole");
    add_game(games, players, 2, 4, "Jen Steadman", 84, 74, "Jonathan Rawlinson");
    add_game(games, players, 2, 4, "Jon O'Neill", 53, 50, "Jen Steadman");
    add_game(games, players, 2, 4, "Jonathan Rawlinson", 58, 55, "Jon O'Neill");
    add_game(games, players, 2, 5, "David Barnard", 69, 39, "Will Howells");
    add_game(games, players, 2, 5, "Oliver Garner", 51, 67, "David Barnard");
    add_game(games, players, 2, 5, "Will Howells", 43, 72, "Oliver Garner");
    add_game(games, players, 2, 6, "Jack Hurst", 70, 38, "Zarte Siempre");
    add_game(games, players, 2, 6, "Ryan Taylor", 55, 63, "Jack Hurst");
    add_game(games, players, 2, 6, "Zarte Siempre", 49, 50, "Ryan Taylor");
    add_game(games, players, 2, 7, "Ian Volante", 42, 49, "Rob Foster");
    add_game(games, players, 2, 7, "Rob Foster", 54, 26, "Spanky McCullagh");
    add_game(games, players, 2, 7, "Spanky McCullagh", 66, 41, "Ian Volante");
    add_game(games, players, 2, 8, "Adam Dexter", 39, 54, "Michelle Nevitt");
    add_game(games, players, 2, 8, "Apterous Nude", 40, 43, "Adam Dexter");
    add_game(games, players, 2, 8, "Michelle Nevitt", 64, 40, "Apterous Nude");
    add_game(games, players, 2, 9, "Jeff Clayton", 39, 76, "Mark Deeks");
    add_game(games, players, 2, 9, "Mark Deeks", 69, 51, "Michael Cullen");
    add_game(games, players, 2, 9, "Michael Cullen", 31, 64, "Jeff Clayton");
    add_game(games, players, 2, 10, "Lauren Hamer", 59, 49, "Tom Rowell");
    add_game(games, players, 2, 10, "Tom Barnes", 50, 47, "Lauren Hamer");
    add_game(games, players, 2, 10, "Tom Rowell", 52, 42, "Tom Barnes");
    add_game(games, players, 2, 11, "Heather Styles", 60, 43, "Paul Sinha");
    add_game(games, players, 2, 11, "Paul Sinha", 57, 33, "Sue Sanders");
    add_game(games, players, 2, 11, "Sue Sanders", 38, 59, "Heather Styles");
    add_game(games, players, 2, 12, "Ned Pendleton", 59, 52, "Phyl Styles");
    add_game(games, players, 2, 12, "Phil Collinge", 46, 29, "Ned Pendleton");
    add_game(games, players, 2, 12, "Phyl Styles", 42, 51, "Phil Collinge");
    add_game(games, players, 2, 13, "Oli Moore", 51, 33, "Gevin Chapwell");
    add_game(games, players, 2, 13, "Supee Juachan", 36, 63, "Oli Moore");
    add_game(games, players, 2, 13, "Gevin Chapwell", 61, 34, "Supee Juachan");
    add_game(games, players, 2, 14, "Chris Marshall", 44, 33, "Rachel Dixon");
    add_game(games, players, 2, 14, "Clare James", 26, 58, "Chris Marshall");
    add_game(games, players, 2, 14, "Rachel Dixon", 48, 40, "Clare James");

    add_game(games, players, 3, 1, "Innis Carson", 62, 49, "Oliver Garner");
    add_game(games, players, 3, 1, "Jen Steadman", 62, 48, "Innis Carson");
    add_game(games, players, 3, 1, "Oliver Garner", 51, 49, "Jen Steadman");
    add_game(games, players, 3, 2, "Adam Gillard", 68, 58, "Conor Travers");
    add_game(games, players, 3, 2, "Conor Travers", 70, 53, "David Barnard");
    add_game(games, players, 3, 2, "David Barnard", 52, 54, "Adam Gillard");
    add_game(games, players, 3, 3, "Giles Hutchings", 76, 46, "Jon O'Neill");
    add_game(games, players, 3, 3, "Jack Worsley", 59, 69, "Giles Hutchings");
    add_game(games, players, 3, 3, "Jon O'Neill", 39, 54, "Jack Worsley");
    add_game(games, players, 3, 4, "Jack Hurst", 68, 50, "James Robinson");
    add_game(games, players, 3, 4, "James Robinson", 70, 40, "Michelle Nevitt");
    add_game(games, players, 3, 4, "Michelle Nevitt", 58, 71, "Jack Hurst");
    add_game(games, players, 3, 5, "Jonathan Rawlinson", 59, 45, "Matt Bayfield");
    add_game(games, players, 3, 5, "Matt Bayfield", 68, 58, "Rob Foster");
    add_game(games, players, 3, 5, "Rob Foster", 44, 61, "Jonathan Rawlinson");
    add_game(games, players, 3, 6, "Mark Deeks", 63, 51, "Paul Sinha");
    add_game(games, players, 3, 6, "Paul Sinha", 37, 53, "Tom Rowell");
    add_game(games, players, 3, 6, "Tom Rowell", 46, 67, "Mark Deeks");
    add_game(games, players, 3, 7, "Oli Moore", 82, 69, "Phil Collinge");
    add_game(games, players, 3, 7, "Phil Collinge", 37, 54, "Spanky McCullagh");
    add_game(games, players, 3, 7, "Spanky McCullagh", 67, 65, "Oli Moore");
    add_game(games, players, 3, 8, "Heather Styles", 32, 71, "Ryan Taylor");
    add_game(games, players, 3, 8, "Jeff Clayton", 54, 59, "Heather Styles");
    add_game(games, players, 3, 8, "Ryan Taylor", 43, 32, "Jeff Clayton");
    add_game(games, players, 3, 9, "Ahmed Mohamed", 62, 41, "Will Howells");
    add_game(games, players, 3, 9, "Graeme Cole", 50, 46, "Ahmed Mohamed");
    add_game(games, players, 3, 9, "Will Howells", 41, 55, "Graeme Cole");
    add_game(games, players, 3, 10, "Chris Marshall", 51, 38, "Zarte Siempre");
    add_game(games, players, 3, 10, "Lauren Hamer", 27, 44, "Chris Marshall");
    add_game(games, players, 3, 10, "Zarte Siempre", 52, 50, "Lauren Hamer");
    add_game(games, players, 3, 11, "Adam Dexter", 45, 61, "Gevin Chapwell");
    add_game(games, players, 3, 11, "Rachel Dixon", 45, 53, "Adam Dexter");
    add_game(games, players, 3, 11, "Gevin Chapwell", 64, 35, "Rachel Dixon");
    add_game(games, players, 3, 12, "Apterous Nude", 40, 53, "Ned Pendleton");
    add_game(games, players, 3, 12, "Ned Pendleton", 38, 42, "Tom Barnes");
    add_game(games, players, 3, 12, "Tom Barnes", 59, 40, "Apterous Nude");
    add_game(games, players, 3, 13, "Ian Volante", 63, 41, "Supee Juachan");
    add_game(games, players, 3, 13, "Phyl Styles", 35, 52, "Ian Volante");
    add_game(games, players, 3, 13, "Supee Juachan", 41, 42, "Phyl Styles");
    add_game(games, players, 3, 14, "Clare James", 16, 51, "Sue Sanders");
    add_game(games, players, 3, 14, "Michael Cullen", 60, 17, "Clare James");
    add_game(games, players, 3, 14, "Sue Sanders", 40, 46, "Michael Cullen");


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

    (weight, player_groups) = swiss3(games, players, rank_by_wins=True, limit_ms=limit_ms);

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
