#!/usr/bin/python

import sqlite3;
import re;
import os;

RANK_WINS_POINTS = 0;
RANK_POINTS = 1;

create_tables_sql = """
begin transaction;

-- PLAYER table
create table if not exists player (
	id integer primary key autoincrement,
	name text,
	rating int,
	unique(name)
);

-- GAME table, containing scheduled games and played games
create table if not exists game (
	round_no int,
	seq int,
	table_no int,
	game_type text,
	p1 integer,
	p1_score integer,
	p2 integer,
	p2_score integer,
	tiebreak int,
	unique(round_no, seq)
);

-- game log, never deleted from
create table if not exists game_log (
	seq integer primary key autoincrement,
	ts text,
	round_no int,
	round_seq int,
	table_no int,
	game_type text,
	p1 integer not null,
	p1_score int,
	p2 integer not null,
	p2_score int,
	tiebreak int,
	log_type int
);

-- Games where we don't yet know who the players are going to be, but we
-- do know it's going to be "winner of this match versus winner of that match".
create table if not exists game_pending (
	round_no int,
	seq int,
	seat int,
	winner int,
	from_round_no int,
	from_seq int,
	unique(round_no, seq, seat)
);

-- options, such as what to sort players by, how to decide fixtures, etc
create table if not exists options (
	name text primary key,
	value text
);

-- Round names. When a fixture generator generates some fixtures, it will
-- probably create a new round. This is always given a number, but it can
-- also be given a name, e.g. "Quarter-finals". The "round type" column should
-- be something like 'P' for preliminary, 'QF', 'SF', 'F' for the finals
-- stages, etc.
create table if not exists rounds (
	id integer primary key,
	type text,
	name text
);

create view if not exists completed_game as
select * from game
where p1_score is not null and p2_score is not null;

create view if not exists completed_heat_game as
select * from game
where p1_score is not null and p2_score is not null and game_type = 'P';

create view if not exists game_divided as
select round_no, table_no, game_type, p1 p_id, p1_score p_score,
	p2 opp_id, p2_score opp_score, tiebreak
from game
union
select round_no, table_no, game_type, p2 p_id, p2_score p_score,
	p1 opp_id, p1_score opp_score, tiebreak
from game;

create view if not exists heat_game_divided as
select * from game_divided where game_type = 'P';

create view if not exists player_wins as
select p.id, sum(case when g.p_id is null then 0
	              when g.p_score is null or g.opp_score is null then 0
		      when g.p_score > g.opp_score then 1
		      else 0 end) wins
from player p left outer join heat_game_divided g on p.id = g.p_id
group by p.id;

create view if not exists player_points as
select p.id, sum(case when g.p_score is null then 0
	              when g.tiebreak and g.p_score > g.opp_score
			then g.opp_score
		      else g.p_score end) points
from player p left outer join heat_game_divided g on p.id = g.p_id
group by p.id;

create view if not exists player_played as
select p.id, sum(case when g.p_score is not null and g.opp_score is not null then 1 else 0 end) played
from player p left outer join heat_game_divided g on p.id = g.p_id
group by p.id;

create view if not exists player_standings as
select p.id, p.name, played.played, wins.wins, points.points
from player p, player_wins wins, player_played played, player_points points
where p.id = wins.id and p.id = played.id and p.id = points.id;

-- Tables for controlling the display system Teleost
create table if not exists teleost(current_mode int);
delete from teleost;
insert into teleost values(0);
create table if not exists teleost_modes(num int, name text, desc text);

commit;
""";

class TourneyException(Exception):
	def __init__(self, description=None):
		self.description = description;

class TourneyInProgressException(TourneyException):
	pass;

class PlayerDoesNotExistException(TourneyException):
	pass;

class PlayerExistsException(TourneyException):
	pass;

class UnknownRankMethodException(TourneyException):
	pass;

class DBNameExistsException(TourneyException):
	pass;

class DBNameDoesNotExistException(TourneyException):
	pass;

class InvalidDBNameException(TourneyException):
	pass;

class InvalidRatingException(TourneyException):
	pass;

class IncompleteRatingsException(TourneyException):
	pass;

class InvalidTableSizeException(TourneyException):
	pass;

class FixtureGeneratorException(TourneyException):
	pass;

class PlayerNotInGameException(TourneyException):
	pass;

class Player(object):
	def __init__(self, name, rating=0):
		self.name = name;
		self.rating = rating;
	
	def __eq__(self, other):
		if other is None:
			return False;
		elif self.name == other.name:
			return True;
		else:
			return False;
	
	def __ne__(self, other):
		return not(self.__eq__(other));
	
	# Emulate a 2-tuple
	def __len__(self):
		return 2;

	def __getitem__(self, key):
		return [self.name, self.rating][key];
	
	def __str__(self):
		return self.name;

	def is_player_known(self):
		return True;

	def is_pending(self):
		return False;

	def make_dict(self):
		return {
				"name" : self.name,
				"rating" : self.rating
		};

	def get_name(self):
		return self.name;

# This object can be on one side and/or other of a Game, just like a Player.
# However, it does not represent a player. It represents the winner or loser
# of another specific game yet to be played.
class PlayerPending(object):
	def __init__(self, round_no, round_seq, winner=True, round_short_name=None):
		self.round_no = round_no;
		self.round_seq = round_seq;
		self.winner = winner;
		self.round_short_name = round_short_name if round_short_name else ("R%d" % self.round_no)
	
	def __eq__(self, other):
		if other is None:
			return False;
		elif self.round_no == other.round_no and self.round_seq == other.round_seq and self.winner == other.winner:
			return True;
		else:
			return False;
	
	def __len__(self):
		return 2;

	def __getitem__(self, key):
		return [None, 0][key];

	def is_player_known(self):
		return False;

	def is_pending(self):
		return True;

	def make_dict(self):
		return {
				"round" : self.round_no,
				"round_seq" : self.round_seq,
				"winner" : self.winner,
				"round_short_name" : self.round_short_name
		};
	
	@staticmethod
	def from_dict(d):
		return PlayerPending(d["round"], d["round_seq"], d["winner"], d["round_short_name"]);

	def get_name(self):
		return None;

	def __str__(self):
		if self.round_short_name is None:
			return "%s of R%d.%d" % ("Winner" if self.winner else "Loser", self.round_no, self.round_seq);
		else:
			return "%s of %s.%d" % ("Winner" if self.winner else "Loser", self.round_short_name, self.round_seq);

	def get_pending_game_details(self):
		return (self.round_no, self.round_seq, self.winner);


class Game(object):
	def __init__(self, round_no, seq, table_no, game_type, p1, p2, s1=None, s2=None, tb=False):
		self.round_no = round_no;
		self.seq = seq;
		self.table_no = table_no;
		self.game_type = game_type;
		self.p1 = p1;
		self.p2 = p2;
		self.s1 = s1;
		self.s2 = s2;
		self.tb = tb;
	
	def is_complete(self):
		if self.s1 is not None and self.s2 is not None:
			return True;
		else:
			return False;
	
	def are_players_known(self):
		if self.p1.is_player_known() and self.p2.is_player_known():
			return True;
		else:
			return False;

	
	def contains_player(self, player):
		if self.p1 == player or self.p2 == player:
			return True;
		else:
			return False;
	
	def __str__(self):
		if self.is_complete():
			return "Round %d, table %d, %s %s %s" % (self.round_no, self.table_no, str(self.p1), self.format_score(), str(self.p2));
		else:
			return "Round %d, table %d, %s v %s" % (self.round_no, self.table_no, str(self.p1), str(self.p2));
	
	def make_dict(self):
		names = self.get_player_names();
		if self.p1.is_pending():
			p1pending = self.p1.make_dict();
		else:
			p1pending = None;
		if self.p2.is_pending():
			p2pending = self.p2.make_dict();
		else:
			p2pending = None;
		return {
				"round_no" : self.round_no,
				"round_seq" : self.seq,
				"table_no" : self.table_no,
				"game_type" : self.game_type,
				"p1" : names[0],
				"p2" : names[1],
				"p1pending" : p1pending,
				"p2pending" : p2pending,
				"s1" : self.s1,
				"s2" : self.s2,
				"tb" : self.tb
		};

	def is_between_names(self, name1, name2):
		if not self.p1.is_player_known() or not self.p2.is_player_known():
			return False;
		(pname1, pname2) = self.get_player_names();
		if (pname1 == name1 and pname2 == name2) or (pname1 == name2 and pname2 == name1):
			return True;
		else:
			return False;
	
	def get_player_names(self):
		return [self.p1.get_name(), self.p2.get_name()];
	
	def get_player_score(self, player):
		if self.p1.is_player_known() and self.p1 == player:
			score = self.s1;
		elif self.p2.is_player_known() and self.p2 == player:
			score = self.s2;
		else:
			raise PlayerNotInGameException("player %s is not in the game between %s and %s." % (str(player), str(self.p1), str(self.p2)));
		return score;
	
	def get_opponent_score(self, player):
		if self.p1 == player:
			score = self.s2;
		elif self.p2 == player:
			score = self.s1;
		else:
			raise PlayerNotInGameException("player %s is not in the game between %s and %s." % (str(player), str(self.p1), str(self.p2)));
		return score;

	
	def set_player_score(self, player, score):
		if self.p1 == player:
			self.s1 = score;
		elif self.p2 == player:
			self.s2 = score;
		else:
			raise PlayerNotInGameException("player %s is not in the game between %s and %s." % (str(player), str(self.p1), str(self.p2)));
	
	def set_tiebreak(self, tb):
		self.tb = tb;
	
	def set_score(self, s1, s2, tb):
		self.s1 = s1;
		self.s2 = s2;
		self.tb = tb;
	
	def format_score(self):
		if self.s1 is None and self.s2 is None:
			return "";

		if self.s1 is None:
			left = "";
		else:
			left = str(self.s1);
		if self.s2 is None:
			right = "";
		else:
			right = str(self.s2);
		if self.tb:
			if self.s1 > self.s2:
				left += "*";
			elif self.s2 > self.s1:
				right += "*";
		return left + " - " + right;
	
	# Emulate a list of values
	def __len__(self):
		return 9;

	def __getitem__(self, key):
		return [self.round_no, self.seq, self.table_no, self.game_type, str(self.p1), self.s1, str(self.p2), self.s2, self.tb ][key];


class Tourney(object):
	def __init__(self, filename, tourney_name):
		self.filename = filename;
		self.name = tourney_name;
		self.db = sqlite3.connect(filename);
	
	# Number of games in the GAME table - that is, number of games played
	# or in progress.
	def get_num_games(self):
		cur = self.db.cursor();
		cur.execute("select count(*) from game");
		row = cur.fetchone();
		count = row[0];
		cur.close();
		return count;
	
	def get_round_type(self, round_no):
		cur = self.db.cursor();
		cur.execute("select type from rounds where id = ?", (round_no,));
		row = cur.fetchone();
		if not row:
			cur.close();
			return None;
		else:
			cur.close();
			return row[0];
	
	def get_round_name(self, round_no):
		cur = self.db.cursor();
		cur.execute("select name from rounds where id = ?", (round_no,));
		row = cur.fetchone();
		if not row:
			cur.close();
			return None;
		else:
			cur.close();
			return row[0];
	
	def get_rounds(self):
		cur = self.db.cursor();
		cur.execute("select g.round_no, r.type, r.name from game g left outer join rounds r on g.round_no = r.id group by g.round_no");
		rounds = [];
		for row in cur:
			rdict = dict();
			if row[2] is None:
				rdict["name"] = "Round " + str(row[0]);
			else:
				rdict["name"] = row[2];
			rdict["type"] = row[1];
			rdict["num"] = row[0];
			rounds.append(rdict);
		cur.close();
		return rounds;
	
	def name_round(self, round_no, round_name, round_type):
		# Does round_no already exist?
		cur = self.db.cursor();
		cur.execute("select id from rounds where id = ?", (round_no,));
		rows = cur.fetchall();
		if len(rows) > 0:
			cur.close();
			cur = self.db.cursor();
			cur.execute("update rounds set name = ?, type = ? where id = ?", (round_name, round_type, round_no));
		else:
			cur.close();
			cur = self.db.cursor();
			cur.execute("insert into rounds(id, name, type) values (?, ?, ?)", (round_no, round_name, round_type));
		self.db.commit();
		cur.close()


	# players must be a list of two-tuples. Each tuple is (name, rating).
	# Alternatively they can be Player objects, which pretend to be 2-tuples.
	# Rating should be an integer. The rating may be None for all players,
	# in which case the first player is given a rating of 2000 and subsequent
	# players are rated progressively lower. It is an error to specify a
	# rating for some players and not others.
	# This function removes any players currently registered.
	def set_players(self, players):
		# If there are any games, in this tournament, it's too late to
		# change the player list.
		if self.get_num_games() > 0:
			raise TourneyInProgressException("Adding or removing players is not permitted once the tournament has started.");

		# Check the ratings, if given, are sane, and convert them to integers
		new_players = [];
		for p in players:
			try:
				if p[1] is not None:
					rating = int(p[1]);
				else:
					rating = None;
				new_players.append((p[0], rating));
			except ValueError:
				raise InvalidRatingException("Player \"%s\" has an invalid rating \"%s\". A player's rating must be an integer." % (p[0], p[1]));
		players = new_players;

		ratings = map(lambda x : x[1], filter(lambda x : x[1] is not None, players));
		#if len(ratings) != 0 and len(ratings) != len(players):
		#	raise IncompleteRatingsException("Either every player must be given a rating, or no players may be given ratings in which case ratings will be automatically assigned.");

		if len(ratings) < len(players):
			max_rating = 2000;
			rating_step = 20;

			new_players = [];
			rating = max_rating;
			for i in range(len(players)):
				if players[i][1] is None:
					new_players.append((players[i][0], rating));
				else:
					new_players.append((players[i][0], players[i][1]));
				rating -= rating_step;
			players = new_players;
			self.set_attribute("autoratings", 1);
		else:
			self.set_attribute("autoratings", 0);

		self.db.execute("delete from player");

		self.db.executemany("insert into player(name, rating) values (?, ?)", players);
		self.db.commit();
	
	def are_ratings_automatic(self):
		return bool(self.get_int_attribute("autoratings", 1));
	
	def get_players(self):
		cur = self.db.cursor();
		cur.execute("select name, rating from player order by rating desc, name");
		players = [];
		for row in cur:
			players.append(Player(row[0], row[1]));
		cur.close();
		return players;
	
	def add_player(self, name, rating):
		if self.get_num_games() > 0:
			raise TourneyInProgressException("Adding or removing players is not permitted once the tournament has started.");
		self.db.execute("insert into player(name, rating) values (?, ?)", (name, rating));
		self.db.commit();
	
	def remove_player(self, name):
		if self.get_num_games() > 0:
			raise TourneyInProgressException("Adding or removing players is not permitted once the tournament has started.");

		cur = self.db.cursor();
		cur.execute("delete from player where name = ?", (name));
		if cur.rowcount < 1:
			self.db.rollback();
			raise PlayerDoesNotExistException("Cannot remove player \"" + name + "\" because such a player does not exist.");
		cur.close();
		self.db.commit();
	
	def rerate_player(self, name, rating):
		try:
			rating = int(rating)
		except ValueError:
			raise InvalidRatingException("Cannot set %s's rating - invalid rating." % name);
		cur = self.db.cursor();
		cur.execute("update player set rating = ? where name = ?", (rating, name));
		if cur.rowcount < 1:
			self.db.rollback();
			raise PlayerDoesNotExistException("Cannot change the rating of player \"" + name + "\" because no player by that name exists.");
		cur.close();
		self.db.commit();
	
	def rename_player(self, oldname, newname):
		players = self.get_players();
		for p in players:
			if p.name == newname:
				raise PlayerExistsException("Cannot rename player \"%s\" to \"%s\" because there's already another player called %s." % (oldname, newname, newname));
		cur = self.db.cursor();
		cur.execute("update player set name = ? where name = ?", (newname, oldname));
		if cur.rowcount < 1:
			self.db.rollback();
			raise PlayerDoesNotExistException("Cannot rename player \"" + oldname + "\" because no player by that name exists.");
		cur.close();
		self.db.commit();
	
	def get_player_name(self, player_id):
		cur = self.db.cursor();
		cur.execute("select name from player where id = ?", (player_id));
		rows = cur.fetchall();
		if len(rows) < 1:
			raise PlayerDoesNotExistException();
		cur.close();
		self.db.commit();
		return rows[0];

	# games is a list of tuples:
	# (round_no, seq, table_no, game_type, name1, score1, name2, score2, tiebreak)
	def merge_games(self, games):
		try:
			known_games = filter(lambda x : x.are_players_known(), games);
			pending_games = filter(lambda x : not x.are_players_known(), games);

			# Records to insert into game_staging, where we use NULL if the
			# player isn't known yet
			game_records = map(lambda x : (x.round_no, x.seq, x.table_no,
				x.game_type,
				x.p1.name if x.p1.is_player_known() else None, x.s1,
				x.p2.name if x.p2.is_player_known() else None, x.s2,
				x.tb), games);

			cur = self.db.cursor();

			cur.execute("""create temporary table if not exists game_staging(
				round_no int, seq int, table_no int, game_type text,
				name1 text, score1 integer,
				name2 text, score2 integer, tiebreak integer)""");
			cur.execute("""create temporary table if not exists game_staging_ids(
				round_no int, seq int, table_no int, game_type text,
				p1 integer, score1 integer,
				p2 integer, score2 integer, tiebreak integer)""");
			cur.execute("""create temporary table if not exists game_pending_staging(
				round_no int, seq int, seat int, player_id int)""");
			cur.execute("delete from temp.game_staging");
			cur.execute("delete from temp.game_staging_ids");
			cur.execute("delete from temp.game_pending_staging");

			cur.executemany("insert into temp.game_staging values(?, ?, ?, ?, ?, ?, ?, ?, ?)", games);
			cur.execute("""insert into temp.game_staging_ids
				select g.round_no, g.seq, g.table_no, g.game_type,
				p1.id, g.score1, p2.id, g.score2, g.tiebreak
				from temp.game_staging g left outer join player p1
					on g.name1 = p1.name left outer join player p2
					on g.name2 = p2.name""");
				#where g.name1 = p1.name and g.name2 = p2.name""");

			# Remove any rows that are already in GAME
			cur.execute("""delete from temp.game_staging_ids
				where exists(select * from game g where
					g.round_no = game_staging_ids.round_no and
					g.seq = game_staging_ids.seq and
					g.table_no = game_staging_ids.table_no and
					g.game_type = game_staging_ids.game_type and
					g.p1 = game_staging_ids.p1 and
					g.p1_score is game_staging_ids.score1 and
					g.p2 = game_staging_ids.p2 and
					g.p2_score is game_staging_ids.score2 and
					g.tiebreak is game_staging_ids.tiebreak)""");

			# Write "new result" logs for rows that don't have a matching
			# entry in GAME for (round_no, table_no, game_type, p1, p2)
			# with a non-NULL score but the entry we're writing has a
			# non-NULL score.
			cur.execute("""insert into game_log(
					ts, round_no, round_seq, table_no, game_type, p1, p1_score,
					p2, p2_score, tiebreak, log_type)
				select current_timestamp, round_no, seq, table_no, game_type,
					p1, score1, p2, score2, tiebreak, 1
				from temp.game_staging_ids gs
				where score1 is not null and score2 is not null and
					p1 is not null and p2 is not null and
					not exists(select * from game g where
					g.round_no = gs.round_no and
					g.seq = gs.seq and
					g.table_no = gs.table_no and
					g.game_type = gs.game_type and
					g.p1 = gs.p1 and
					g.p2 = gs.p2 and
					g.p1_score is not null and
					g.p2_score is not null)""");

			# And write "correction" logs for rows that do have a matching
			# entry in game for (round_no, table_no, game_type, p1, p2)
			# with a non-NULL score.
			cur.execute("""insert into game_log(
					ts, round_no, round_seq, table_no, game_type, p1, p1_score,
					p2, p2_score, tiebreak, log_type)
				select current_timestamp, round_no, seq, table_no, game_type,
					p1, score1, p2, score2, tiebreak, 2
				from temp.game_staging_ids gs
				where p1 is not null and p2 is not null and
					exists(select * from game g where
					g.round_no = gs.round_no and
					g.seq = gs.seq and
					g.table_no = gs.table_no and
					g.game_type = gs.game_type and
					g.p1 = gs.p1 and
					g.p2 = gs.p2 and
					g.p1_score is not null and
					g.p2_score is not null)""");

			# Insert rows into game if they're not there already
			cur.execute("""insert or replace into game(
						round_no, seq, table_no, game_type,
						p1, p1_score, p2, p2_score, tiebreak)
					select * from temp.game_staging_ids""");

			# Insert into GAME_PENDING any sides of a game where the player
			# is not yet known
			pending_games_records = [];
			for g in pending_games:
				if not g.p1.is_player_known():
					pending_games_records.append((g.round_no, g.seq, 1, g.p1.winner, g.p1.round_no, g.p1.round_seq));
				if not g.p2.is_player_known():
					pending_games_records.append((g.round_no, g.seq, 2, g.p2.winner, g.p2.round_no, g.p2.round_seq));

			cur.executemany("""insert or replace into
					game_pending
					values (?, ?, ?, ?, ?, ?)""",
					pending_games_records);

			# If we inserted any rows into GAME whose (round_no, round_seq)
			# corresponds to (from_round_no, from_round_seq) in GAME_PENDING,
			# it means that we can fill in one or more unknown players in
			# GAME. For example, if we inserted the result for a semi-final,
			# then we might now be able to fill in the player ID for one side
			# of the final.
			cur.execute("""insert into temp.game_pending_staging
						select gp.round_no, gp.seq, gp.seat,
							case when gp.winner = 1 and gsi.score1 > gsi.score2
							then gsi.p1
							when gp.winner = 1 and gsi.score2 > gsi.score1
							then gsi.p2
							when gp.winner = 0 and gsi.score1 > gsi.score2
							then gsi.p2
							when gp.winner = 0 and gsi.score2 > gsi.score1
							then gsi.p1
							else NULL
							end player_id
						from game_staging_ids gsi, game_pending gp
						on gsi.round_no = gp.from_round_no and
						   gsi.seq = gp.from_seq""");

			cur.execute("select * from temp.game_pending_staging");
			updcur = self.db.cursor();
			for row in cur:
				(round_no, seq, seat, player_id) = row;
				updcur.execute("update game set p%d = ? where round_no = ? and seq = ? and p1_score is NULL and p2_score is NULL" % (seat), (player_id, round_no, seq));

			self.db.commit();
		except:
			self.db.rollback();
			raise;
	
	def set_game_players(self, alterations):
		# alterations is (round_no, seq, p1, p2)
		# but we want (p1name, p2name, round_no, seq) for feeding into the
		# executemany() call.
		alterations_reordered = map(lambda x : (x[2].get_name(), x[3].get_name(), x[0], x[1]), alterations);
		cur = self.db.cursor();
		cur.executemany("""
update game
set p1 = (select id from player where name = ?),
p2 = (select id from player where name = ?)
where round_no = ? and seq = ?""", alterations_reordered);
		rows_updated = cur.rowcount;
		cur.close();
		self.db.commit();
		return rows_updated;
	
	def get_player_from_name(self, name):
		sql = "select name, rating from player where name = ?";
		cur = self.db.cursor();
		cur.execute(sql, (name,));
		row = cur.fetchone();
		cur.close();
		if row is None:
			raise PlayerDoesNotExistException("Player with name \"%s\" does not exist" % name);
		else:
			return Player(row[0], row[1]);
	
	def get_player_from_id(self, player_id):
		sql = "select name, rating from player where id = ?";
		cur = self.db.cursor();
		cur.execute(sql, (player_id,));
		row = cur.fetchone();
		cur.close();
		if row is None:
			raise PlayerDoesNotExistException("No player exists with ID %d" % player_id);
		else:
			return Player(row[0], row[1]);
	
	def get_latest_round_no(self, round_type=None):
		cur = self.db.cursor();

		if round_type is None:
			cur.execute("select max(id) from rounds");
		else:
			cur.execute("select max(id) from rounds where type = ?", (round_type,));
		row = cur.fetchone();
		if row is None:
			cur.close();
			return None;
		else:
			cur.close();
			return row[0];
	
	def get_played_unplayed_counts(self, round_no=None):
		cur = self.db.cursor();
		params = [];

		conditions = "";
		if round_no is not None:
			conditions += "where round_no = ? ";
			params.append(round_no);

		sql = "select case when p1_score is NULL or p2_score is NULL then 0 else 1 end complete, count(*) from game " + conditions + " group by 1 order by 1";

		if params:
			cur.execute(sql, params);
		else:
			cur.execute(sql);

		num_played = 0;
		num_unplayed = 0;
		for r in cur:
			if r[0] == 0:
				num_unplayed = r[1];
			elif r[0] == 1:
				num_played = r[1];
		cur.close();
		return (num_played, num_unplayed);

	def get_games(self, round_no=None, table_no=None, game_type=None, only_players_known=True):
		conditions = [];
		params = [];

		if round_no is not None:
			conditions.append("g.round_no = ?");
			params.append(round_no);
		if table_no is not None:
			conditions.append("g.table_no = ?");
			params.append(table_no);
		if game_type is not None:
			conditions.append("g.game_type = ?");
			params.append(game_type);
		if only_players_known:
			conditions.append("(g.p1 is not null and g.p2 is not null)");

		cur = self.db.cursor();
		sql = """select g.round_no, g.seq, g.table_no, g.game_type, g.p1,
				g.p1_score, g.p2, g.p2_score, g.tiebreak,
				gp1.winner as seat1_which, gp1.from_round_no as seat1_round_no,
				gp1.from_seq seat1_seq,
				gp2.winner as seat2_which, gp2.from_round_no as seat2_round_no,
				gp2.from_seq as seat2_seq
				from game g left outer join game_pending gp1
				on g.round_no = gp1.round_no and g.seq = gp1.seq and gp1.seat=1
				left outer join game_pending gp2
				on g.round_no = gp2.round_no and g.seq = gp2.seq and gp2.seat=2
				where 1=1 """;
		for c in conditions:
			sql += " and " + c;
		sql += "\norder by g.round_no, g.seq";
		if len(params) == 0:
			cur.execute(sql);
		else:
			cur.execute(sql, params);

		rounds = self.get_rounds();

		games = [];
		for row in cur:
			if row[8] is None:
				tb = None;
			elif row[8]:
				tb = True;
			else:
				tb = False;
			for p_index in (1,2):
				if p_index == 1:
					p_id = row[4];
				else:
					p_id = row[6];
				if p_id is None:
					if p_index == 1:
						winner = bool(row[9]);
						of_round_no = int(row[10]);
						of_seq = int(row[11]);
					else:
						winner = bool(row[12]);
						of_round_no = int(row[13]);
						of_seq = int(row[14]);

					short_name = None;
					for r in rounds:
						if r["num"] == of_round_no:
							short_name = r["type"];
							break;
					p = PlayerPending(of_round_no, of_seq, winner, short_name);
				else:
					p = self.get_player_from_id(p_id);
				if p_index == 1:
					p1 = p;
				else:
					p2 = p;
			game = Game(row[0], row[1], row[2], row[3], p1, p2, row[5], row[7], tb);
			games.append(game);

		cur.close();
		self.db.commit();

		return games;

	def ranked_query(self, query, sort_cols=[]):
		pos = 0;
		joint = 0;

		cur = self.db.cursor();
		cur.execute(query);

		prev_sort_vals = None;
		results = [];
		for row in cur:
			if sort_cols:
				sort_vals = [];
				for c in sort_cols:
					sort_vals.append(row[c - 1]);
				sort_vals = tuple(sort_vals);
				if prev_sort_vals and sort_vals == prev_sort_vals:
					joint += 1;
				else:
					pos += joint + 1;
					joint = 0;
				prev_sort_vals = sort_vals;
			else:
				pos += 1;
			
			result = [pos];
			for val in row:
				result.append(val);
			result = tuple(result);
			results.append(result);
		cur.close();
		return results;

	def get_int_attribute(self, name, defval=None):
		value = self.get_attribute(name, defval);
		if value is not None:
			value = int(value);
		return value;

	def get_attribute(self, name, defval=None):
		cur = self.db.cursor();
		cur.execute("select value from options where name = ?", (name,));
		value = cur.fetchone();
		if value is None:
			value = defval;
		else:
			value = str(value[0]);
		cur.close();
		return value;

	def set_attribute(self, name, value):
		cur = self.db.cursor();
		if re.match("^ *-?[0-9]+ *$", str(value)):
			value = int(value);
		cur.execute("insert or replace into options values (?, ?)", (name, value));
		cur.close();
		self.db.commit();
	
	def get_rank_method(self):
		return self.get_int_attribute("rankmethod", RANK_WINS_POINTS);

	def set_rank_method(self, method):
		if method not in [RANK_WINS_POINTS, RANK_POINTS]:
			raise UnknownRankMethodException("Can't rank tourney by method %d because I don't know what that is." % method);
		self.set_attribute("rankmethod", method);
	
	def set_table_size(self, table_size):
		if table_size not in [2,3]:
			raise InvalidTableSizeException("Number of players to a table must be 2 or 3.");
		self.set_attribute("tablesize", int(table_size));
	
	def get_table_size(self):
		return self.get_int_attribute("tablesize", 3);

	def get_standings(self):
		method = self.get_rank_method();
		if method == RANK_WINS_POINTS:
			orderby = "order by wins desc, points desc, name";
			rankcols = [3,4];
		elif method == RANK_POINTS:
			orderby = "order by points desc, name";
			rankcols = [4];
		else:
			raise UnknownRankMethodException("This tourney's standings are ranked by method %d, which I don't recognise." % method);
		return self.ranked_query("select name, played, wins, points from player_standings " + orderby, rankcols);

	def get_logs_since(self, seq, include_new_games=False):
		cur = self.db.cursor();
		sql = """select seq, datetime(ts, 'localtime') ts, round_no,
				round_seq, table_no, game_type, p1.name p1, p1_score,
				p2.name p2, p2_score, tiebreak, log_type
				from game_log, player p1, player p2
				where p1 = p1.id and p2 = p2.id and seq > ?""";
		if not(include_new_games):
			sql += " and log_type > 0";
		sql += " order by seq";
		cur.execute(sql, (seq,));
		results = cur.fetchall();
		cur.close();
		return results;

	def get_teleost_modes(self):
		cur = self.db.cursor();
		cur.execute("select current_mode from teleost");
		row = cur.fetchone();
		if row is not None:
			current_mode = row[0];
		else:
			current_mode = None;

		cur.execute("select num, name, desc from teleost_modes order by num");
		modes = [];
		for row in cur:
			mode = dict();
			mode["num"] = row[0];
			mode["name"] = row[1];
			mode["desc"] = row[2];
			mode["selected"] = (row[0] == current_mode);
			modes.append(mode);
		cur.close();
		self.db.commit();
		return modes;

	def set_teleost_mode(self, mode):
		cur = self.db.cursor();
		cur.execute("update teleost set current_mode = ?", (mode,));
		cur.close();
		self.db.commit();
	
	def define_teleost_modes(self, modes):
		cur = self.db.cursor();
		cur.execute("delete from teleost_modes");
		cur.executemany("insert into teleost_modes (num, name, desc) values (?, ?, ?)", modes);
		cur.close();
		self.db.commit();
	
	def get_current_teleost_mode(self):
		cur = self.db.cursor();
		cur.execute("select current_mode from teleost");
		row = cur.fetchone();
		if row is None:
			return 0;
		return row[0];

	def get_num_games_to_play_by_table(self, round_no=None):
		sql = """select table_no,
			sum(case when p1_score is null and p2_score is null
				then 1 else 0 end) games_left
			from game""";
		if round_no is not None:
			sql += " where round_no = %d" % round_no;
		sql += " group by table_no";
		cur = self.db.cursor();
		cur.execute(sql);
		d = dict();
		for (table, count) in cur:
			d[table] = count;
		cur.close();
		return d;
	
	def get_latest_game_times_by_table(self, round_no=None):
		sql = "select table_no, max(ts) from game_log";
		sql += " where log_type = 1";
		if round_no is not None:
			sql += " and round_no = %d" % round_no;
		sql += " group by 1 order by 2";
		cur = self.db.cursor();
		cur.execute(sql);
		d = dict();
		for (table, ts) in cur:
			d[table] = str(ts);
		cur.close();
		return d;

	def close(self):
		self.db.commit();
		self.db.close();

def tourney_open(dbname, directory="."):
	if not re.match("^[A-Za-z0-9_-]+$", dbname):
		raise InvalidDBNameException("The tourney database name can only contain letters, numbers, underscores and hyphens.");
	if directory:
		if directory[-1] != os.sep:
			directory += os.sep;
	dbpath = directory + dbname + ".db";

	if not os.path.exists(dbpath):
		raise DBNameDoesNotExistException("The tourney \"%s\" does not exist." % dbname);
	else:
		tourney = Tourney(dbpath, dbname);

	return tourney;

def tourney_create(dbname, directory="."):
	if not re.match("^[A-Za-z0-9_-]+$", dbname):
		raise InvalidDBNameException("The tourney database name can only contain letters, numbers, underscores and hyphens.");
	if directory:
		if directory[-1] != '/':
			directory += "/";
	dbpath = directory + dbname + ".db";
	if os.path.exists(dbpath):
		raise DBNameExistsException("The tourney \"%s\" already exists. Pick another name." % dbname);
	tourney = Tourney(dbpath, dbname);
	tourney.db.executescript(create_tables_sql);
	tourney.db.commit();
	return tourney;
