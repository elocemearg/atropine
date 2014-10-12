#!/usr/bin/python

import sys;
import countdowntourney;
import swiss3;
import random;

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

	#print "%d %d %.3f %.3f" % (game.p1.rating, game.p2.rating, p1_threshold, p2_threshold);

	p1_score = 0;
	p2_score = 0;

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

def simulate_tourney(num_players, num_rounds, limit_ms):
	games = [];

	# Generate player list
	players = [];

	top_rating = num_players * 20 + 100;
	for i in range(num_players):
		name = "Player %d" % i;
		rating = top_rating - i * 20;
		players.append(countdowntourney.Player(name, rating));
	
	for round_no in range(1, num_rounds + 1):
		print "Generating round %d..." % round_no;
		if round_no == 1:
			(weight, groups) = swiss3.swiss3_first_round(players);
		else:
			(weight, groups) = swiss3.swiss3(games, players, rank_by_wins=True, limit_ms=limit_ms);
		print "Done.";

		round_games = [];
		table_no = 1;
		round_seq = 1;
		for g in groups:
			round_games.append(countdowntourney.Game(round_no, round_seq, table_no, 'P', g[0], g[1]));
			round_games.append(countdowntourney.Game(round_no, round_seq + 1, table_no, 'P', g[1], g[2]));
			round_games.append(countdowntourney.Game(round_no, round_seq + 2, table_no, 'P', g[2], g[0]));
			round_seq += 3;
			table_no += 1;

		# Make sure the penalty for a single table isn't greater than 10000
		table_no = 1;
		for g in groups:
			if g.weight > 10000:
				print "Warning: round %d table %d (%s) has penalty %d" % (round_no, table_no, ", ".join(map(lambda x : x.name, g)), g.weight);
			table_no += 1;

		for g in round_games:
			set_random_score(g);

		games = games + round_games;
	
	return games;

for size in range(18, 49, 3):
	num_rounds = 3;
	print "%d players, %d rounds" % (size, num_rounds);
	games = simulate_tourney(size, num_rounds, 3000);
	#for g in games:
	#	print "%2d %2d %20s %3d-%-3d%s %-20s" % (g.round_no, g.table_no, g.p1.name, g.s1, g.s2, "*" if g.tb else " ", g.p2.name);
	print

sys.exit(0);
