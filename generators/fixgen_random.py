import random;
import countdowntourney;

name = "Random Fixture Generator";
description = "Randomly distribute players between tables, without regard for previous results.";

# If this fixture generator is now able to generate a new round without
# any further information from the user, return None.
# Otherwise, return a FixtureForm object for the user to fill in.
# The settings obtained from this should be passed in the dictionary "settings".
# Note that subsequent calls might return further forms, and the settings
# obtained from them should be added to the "settings" dictionary and the
# call made again.
def get_user_form(tourney, settings):
	return None;

def check_ready(tourney):
	players = tourney.get_players();
	table_size = tourney.get_table_size();

	if len(players) % table_size != 0:
		return (False, "Number of players (%d) not a multiple of table size (%d)" % (len(players), table_size));

	return (True, None);

# Generate and return a list of fixtures. This function does NOT add them
# to the tourney database. It's the caller's responsibility to do that, and
# it might choose not to, if, for example, the user decides they don't want
# to accept the fixtures.
def generate(tourney, settings):
	players = tourney.get_players();
	table_size = tourney.get_table_size();

	(ready, excuse) = check_ready(tourney);
	if not ready:
		raise countdowntourney.FixtureGeneratorException(excuse);

	tables = [];
	random.shuffle(players);

	num_tables = len(players) / table_size;
	for table_no in range(0, num_tables):
		table = [];
		for i in range(0, table_size):
			table.append(players[table_no * table_size + i]);
		tables.append(table);
	
	fixtures = [];
	current_games = tourney.get_games(game_type='P');
	if len(current_games) == 0:
		max_round_no = 0;
	else:
		max_round_no = max(map(lambda x : x.round_no, current_games));

	round_no = max_round_no + 1;
	table_no = 1;
	round_seq = 1;
	for table in tables:
		for i in range(0, len(table)):
			for j in range(i + 1, len(table)):
				p1 = table[i];
				p2 = table[j];
				if (i + j) % 2 == 0:
					(p1, p2) = (p2, p1);
				fixture = countdowntourney.Game(round_no, round_seq, table_no, 'P', p1, p2);
				fixtures.append(fixture);
				round_seq += 1;
		table_no += 1;
	
	d = dict();
	d["fixtures"] = fixtures;
	d["rounds"] = [{
		"round": round_no,
		"name": "Round %d" % round_no,
		"type": "P"
	}];
	return d;
