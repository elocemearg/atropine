#!/usr/bin/python3

# Test the Swiss Army Blunderbuss fixture generator (swissN.py) and make
# sure it comes up with some reasonable fixtures.

import sys

sys.path.append("py")

import countdowntourney
import swissN
import random
import getopt

def set_random_score(game):
    r1 = game.p1.rating;
    r2 = game.p2.rating;

    # multiply stronger player's rating by 1.8 to magnify differences
    if r1 > r2:
        r1 *= 1.8;
    elif r2 > r1:
        r2 *= 1.8;

    p1_threshold = float(r1) / float(r1 + r2);
    p2_threshold = p1_threshold;
    p1_threshold *= 0.8
    p2_threshold = 1 - ((1 - p2_threshold) * 0.8)

    p1_score = 0;
    p2_score = 0;

    # Attempt to simulate a realistic 9-rounder score...
    for i in range(9):
        x = random.random();
        round_score = random.randint(4, 10);
        if round_score == 9:
            if random.randint(1, 4) == 1:
                round_score = 18;
            else:
                round_score = 7;
        if x < p1_threshold:
            p1_score += round_score;
        elif x > p2_threshold:
            p2_score += round_score;
        else:
            p1_score += round_score;
            p2_score += round_score;

    if p1_score == p2_score:
        if random.randint(0, 1) == 0:
            p1_score += 10;
        else:
            p2_score += 10;
        tb = True;
    else:
        tb = False;

    game.set_score(p1_score, p2_score, tb);

# Calculate the standings ourselves given the score of each game so far,
# because this test doesn't create a tourney in the database so we can't use
# countdowntourney.get_standings().
def calculate_standings(games, players):
    name_to_standings_row = {}
    rating = 2000
    for p in players:
        name_to_standings_row[p.get_name()] = countdowntourney.StandingsRow(1, p.get_name(), 0, 0, 0, 0, 0, 0, rating, 1000, False, "", 0)
        rating -= 20
    for g in games:
        g_names = g.get_player_names()
        g_players = g.get_players()
        for pi in (0, 1):
            points_for = g.get_player_score(g_players[pi])
            points_against = g.get_player_score(g_players[pi ^ 1])
            win = points_for > points_against
            draw = points_for == points_against
            if g.is_double_loss():
                win = False
                draw = False
            if g.is_tiebreak():
                points_for = points_against
            spread = points_for - points_against
            sr = name_to_standings_row[g_names[pi]]
            sr.played += 1
            if win:
                sr.wins += 1
            if draw:
                sr.draws += 1
            sr.points += points_for
            sr.spread += spread
            if pi == 0:
                sr.played_first += 1
    standings = [ name_to_standings_row[p.get_name()] for p in players ]
    standings = sorted(standings, key=lambda x : (x.wins, x.points, x.name), reverse=True)
    pos = 0
    joint = 0
    prev_s = None
    for s in standings:
        if prev_s and prev_s.wins == s.wins and prev_s.points == s.points:
            joint += 1
        else:
            pos += joint + 1
            joint = 0
        s.position = pos
        prev_s = s
    return standings

def simulate_tourney(num_players, num_rounds, group_size, limit_ms, init_max_win_diff):
    num_warnings = 0
    games = [];

    # Generate player list
    players = [];

    top_rating = 1000 + num_players * 20;
    for i in range(num_players):
        name = "Player %d" % i;
        rating = top_rating - i * 20;
        players.append(countdowntourney.Player(name, rating));

    if group_size > 0:
        # If num_players is not a multiple of the group size, add prunes
        # until it is.
        pn = 0
        while num_players % group_size != 0:
            name = "Prune %s" % (chr(ord('A') + pn))
            players.append(countdowntourney.Player(name, 0))
            pn += 1
            num_players += 1

    for round_no in range(1, num_rounds + 1):
        print("Generating round %d..." % round_no);
        standings = calculate_standings(games, players)
        if round_no == 1:
            (weight, groups) = swissN.swissN_first_round(players, group_size);
        else:
            (weight, groups) = swissN.swissN(games, players, standings, group_size, rank_by_wins=True, limit_ms=limit_ms, init_max_win_diff=init_max_win_diff);
        print("Done.");

        round_games = [];
        table_no = 1;
        round_seq = 1;
        division = 0
        if not groups:
            print("Unable to find any acceptable groupings in the time limit.")
            assert(False)

        for g in groups:
            for pi1 in range(0, len(g) - 1):
                for pi2 in range(pi1 + 1, len(g)):
                    round_games.append(countdowntourney.Game(round_no, round_seq, table_no, division, 'P', g[pi1], g[pi2]))
                    round_seq += 1
            table_no += 1

        # Sanity check the groups we've been given.
        # First, make sure every player appears exactly once.
        player_names_seen = set()
        for g in groups:
            for p in g:
                if p.get_name() in player_names_seen:
                    print("%s appears more than once!" % (p.get_name()))
                    assert(False)
                player_names_seen.add(p.get_name())
        unseen_players = []
        for p in players:
            if p.get_name() not in player_names_seen:
                unseen_players.append(p.get_name())
        if unseen_players:
            print("The following players do not appear in any group!")
            print(", ".join(unseen_players))
            assert(False)

        # Find any disgruntled players. A disgruntled player is someone who
        # has been drawn to play against someone higher in the standings,
        # where there is at least one other person between them in the
        # standings who they haven't yet played and aren't drawn to play
        # in this round.
        # It's impossible to avoid any disgruntled players - sometimes the
        # draw has to be shuffled like this to avoid more disgruntling
        # elsewhere. But we should report the number of disgruntleds.
        already_played_names = set()
        for g in games + round_games:
            already_played_names.add((g.p1.get_name(), g.p2.get_name()))
            already_played_names.add((g.p2.get_name(), g.p1.get_name()))

        standings_positions = {}
        for sp in standings:
            standings_positions[sp.name] = sp.position

        # dict mapping player names to how disgruntled they are
        disgruntled_players = {}
        for g in groups:
            for p in g:
                for opp in g:
                    if opp.get_name() == p.get_name():
                        continue
                    opp_pos = standings_positions[opp.get_name()]
                    p_pos = standings_positions[p.get_name()]
                    if opp_pos < p_pos:
                        intervening_eligible_opps = [ sp for sp in standings if sp.position > opp_pos and sp.position < p_pos and (p.get_name(), sp.name) not in already_played_names ]
                        if intervening_eligible_opps:
                            disgruntled_players[p.get_name()] = disgruntled_players.get(p.get_name(), 0) + len(intervening_eligible_opps)
        if disgruntled_players:
            print("%d disgruntled players:" % (len(disgruntled_players)))
        for pn in sorted(disgruntled_players, key=lambda x : disgruntled_players[x], reverse=True):
            print("%20s  %2d" % (pn, disgruntled_players[pn]))

        for g in round_games:
            set_random_score(g);

        games = games + round_games;
    return num_warnings

def main():
    opts, args = getopt.getopt(sys.argv[1:], "p:t:n:T:w:v")
    num_players = 24
    players_per_table = 3
    num_rounds = 3
    init_max_win_diff = 0
    time_limit_ms = 30000
    for o, a in opts:
        if o == "-p":
            num_players = int(a)
        elif o == "-t":
            players_per_table = int(a)
        elif o == "-n":
            num_rounds = int(a)
        elif o == "-v":
            verbose = True
        elif o == "-T":
            time_limit_ms = 1000 * int(a)
        elif o == "-w":
            init_max_win_diff = int(a)
        else:
            print("lol wat")
            sys.exit(1)

    if players_per_table not in (2, 3, 4, -5):
        print("-p: players per table must be 2, 3, 4 or -5 (=5&3).")
        sys.exit(1)

    print("Running unit tests...")
    if not swissN.unit_tests():
        print("Unit tests failed, see above.")
        sys.exit(1)
    print("Unit tests passed.")

    print("%d players, %d rounds" % (num_players, num_rounds));
    num_warnings = simulate_tourney(num_players, num_rounds, players_per_table, time_limit_ms, init_max_win_diff);
    print()

    if num_warnings > 0:
        print("%d warning%s, see above." % (num_warnings, "s" if num_warnings != 1 else ""))
    else:
        print("Finished with no warnings.")

    sys.exit(1 if num_warnings > 0 else 0)

if __name__ == "__main__":
    main()
