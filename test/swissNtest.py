#!/usr/bin/python3

# Test the Swiss Army Blunderbuss fixture generator (swissN.py) and make
# sure it comes up with some reasonable fixtures.

import sys

sys.path.append("py")

import countdowntourney
import swissN
import random

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

def simulate_tourney(num_players, num_rounds, group_size, limit_ms):
    num_warnings = 0
    games = [];

    # Generate player list
    players = [];

    top_rating = num_players * 20 + 100;
    for i in range(num_players):
        name = "Player %d" % i;
        rating = top_rating - i * 20;
        players.append(countdowntourney.Player(name, rating));

    for round_no in range(1, num_rounds + 1):
        print("Generating round %d..." % round_no);
        if round_no == 1:
            (weight, groups) = swissN.swissN_first_round(players, group_size);
        else:
            standings = calculate_standings(games, players)
            (weight, groups) = swissN.swissN(games, players, standings, group_size, rank_by_wins=True, limit_ms=limit_ms);
        print("Done.");

        round_games = [];
        table_no = 1;
        round_seq = 1;
        division = 0
        for g in groups:
            for pi1 in range(0, len(g) - 1):
                for pi2 in range(pi1 + 1, len(g)):
                    round_games.append(countdowntourney.Game(round_no, round_seq, table_no, division, 'P', g[pi1], g[pi2]))
                    round_seq += 1
            table_no += 1

        # Make sure the penalty for a single table isn't greater than 10000
        table_no = 1;
        for g in groups:
            if g.weight > 10000:
                print("Warning: round %d table %d (%s) has penalty %d" % (round_no, table_no, ", ".join([x.name for x in g]), g.weight));
                num_warnings += 1
            table_no += 1;

        for g in round_games:
            set_random_score(g);

        games = games + round_games;
    return num_warnings

def main():
    num_warnings = 0
    min_players = 18
    max_players = 48
    for size in range(min_players, max_players + 1, 3):
        num_rounds = 3;
        print("%d players, %d rounds" % (size, num_rounds));
        num_warnings += simulate_tourney(size, num_rounds, 3, 5000);
        print()

    if num_warnings > 0:
        print("%d warning%s, see above." % (num_warnings, "s" if num_warnings != 1 else ""))
    else:
        print("Finished with no warnings.")

    sys.exit(1 if num_warnings > 0 else 0)

if __name__ == "__main__":
    main()
