#!/usr/bin/python
# coding: utf-8

import sys;
import teleostscreen;
import countdowntourney;
import time;

show_timestamps = False;

class VideprinterFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
		self.last_log_seq = 0;
	
	def fetch_header_row(self):
		return None;
	
	def fetch_data_rows(self, num_rows):
		logs = self.tourney.get_logs_since(self.last_log_seq);
		logs = logs[-num_rows:];

		rows = [];
		row_padding = teleostscreen.PercentLength(2);
		for log_row in logs:
			l = {
					"seq" : log_row[0],
					"ts" : log_row[1],
					"round_no" : log_row[2],
					"round_seq" : log_row[3],
					"table_no" : log_row[4],
					"game_type" : log_row[5],
					"p1" : log_row[6],
					"s1" : log_row[7],
					"p2" : log_row[8],
					"s2" : log_row[9],
					"tiebreak" : log_row[10],
					"log_type" : log_row[11]
			};
			if l["seq"] > self.last_log_seq:
				self.last_log_seq = l["seq"];
			if show_timestamps:
				timestamp = l["ts"][11:16];
			else:
				timestamp = None;
			game_type = l["game_type"];
			if game_type == "P":
				round_desc = "R%dT%d" % (l["round_no"], l["table_no"]);
			else:
				round_desc = game_type + "." + str(l["round_seq"]);
			name1 = l["p1"];
			s1 = l["s1"];
			name2 = l["p2"];
			s2 = l["s2"];
			if s1 is not None:
				s1 = int(s1);
			if s2 is not None:
				s2 = int(s2);

			round_desc_colour = (255, 128, 64);
			timestamp_colour = (192, 192, 192);
			score_colour = (255, 255, 255);
			name1_colour = (192, 192, 192);
			name2_colour = (192, 192, 192);
			if s1 is not None and s2 is not None:
				if s1 > s2:
					name1_colour = (0, 192, 0);
					name2_colour = (255, 48, 48);
				elif s2 > s1:
					name1_colour = (255, 48, 48);
					name2_colour = (0, 192, 0);
				if l["tiebreak"]:
					if s1 > s2:
						score_str = "%d* - %d" % (s1, s2);
					elif s2 > s1:
						score_str = "%d - %d*" % (s1, s2);
					else:
						score_str = "%d - %d" % (s1, s2);
				else:
					score_str = "%d - %d" % (s1, s2);
			else:
				score_str = " - ";

			row = teleostscreen.TableRow();
			if timestamp:
				row.append_value(teleostscreen.RowValue(timestamp, None, timestamp_colour, row_padding=row_padding));
			row.append_value(teleostscreen.RowValue(round_desc, None, round_desc_colour, row_padding=row_padding));
			row.append_value(teleostscreen.RowValue(name1, None, name1_colour, row_padding=row_padding));
			row.append_value(teleostscreen.RowValue(score_str, None, score_colour, row_padding=row_padding));
			row.append_value(teleostscreen.RowValue(name2, None, name2_colour, row_padding=row_padding));

			rows.append(row);
		return rows;


class StandingsFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
	
	def fetch_header_row(self):
		row = teleostscreen.TableRow();
		grey = (128, 128, 128);
		row.append_value(teleostscreen.RowValue("", teleostscreen.PercentLength(10), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
		row.append_value(teleostscreen.RowValue("", teleostscreen.PercentLength(55), text_colour=grey));
		row.append_value(teleostscreen.RowValue("P", teleostscreen.PercentLength(10), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
		row.append_value(teleostscreen.RowValue("W", teleostscreen.PercentLength(10), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
		row.append_value(teleostscreen.RowValue("Pts", teleostscreen.PercentLength(15), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
		row.set_border(bottom_border=teleostscreen.LineStyle((96, 96, 96), 1));
		return row;
	
	def fetch_data_rows(self, start_row, num_rows):
		pos_colour = (255, 255, 0);
		name_colour = (255,255,255);
		played_colour = (0, 128, 128);
		if self.tourney.get_rank_method() == countdowntourney.RANK_WINS_POINTS:
			wins_colour = (0, 255, 255)
		else:
			wins_colour = (0, 128, 128)
		points_colour = (0, 255, 255);

		standings = self.tourney.get_standings();

		if start_row >= len(standings):
			return None;
		
		subset = standings[start_row:(start_row + num_rows)];

		rows = [];
		for player in subset:
			row = teleostscreen.TableRow();
			row.append_value(teleostscreen.RowValue(str(player[0]), teleostscreen.PercentLength(10), text_colour=pos_colour, alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(str(player[1]), teleostscreen.PercentLength(55), text_colour=name_colour));
			row.append_value(teleostscreen.RowValue(str(player[2]), teleostscreen.PercentLength(10), text_colour=played_colour, alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(str(player[3]), teleostscreen.PercentLength(10), text_colour=wins_colour, alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(str(player[4]), teleostscreen.PercentLength(15), text_colour=points_colour, alignment=teleostscreen.ALIGN_RIGHT));
			rows.append(row);

		return rows;

class TableResultsFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
	
	def fetch_header_row(self):
		return None;

	def fetch_data_rows(self, start_row, num_rows):
		# Find the latest prelim round
		rounds = self.tourney.get_rounds();
		latest_round_no = None;
		for r in rounds:
			if r["type"] == 'P' and (latest_round_no is None or latest_round_no < r["num"]):
				latest_round_no = r["num"];
				latest_round_name = r["name"];

		if latest_round_no is None:
			# That was easy.
			return [];
		
		desired_table_index = start_row / num_rows;
		games = self.tourney.get_games(round_no=latest_round_no);
		table_index = 0;
		games = sorted(games, key=lambda x : x.table_no);
		prev_table_no = None;
		table_no = None;
		table_games = [];
		for g in games:
			if prev_table_no is not None and prev_table_no != g.table_no:
				table_index += 1;
			if table_index == desired_table_index:
				table_no = g.table_no;
				table_games.append(g);
			prev_table_no = g.table_no;

		if not table_games:
			return None;
		
		rows = [];
		top_row = teleostscreen.TableRow();
		top_row_colour = (0, 192, 192);
		name_colour = (255, 255, 255);
		score_colour = (255, 255, 255);
		top_row.append_value(teleostscreen.RowValue("%s   Table %d" % (latest_round_name, table_no), teleostscreen.PercentLength(100), text_colour=top_row_colour, alignment=teleostscreen.ALIGN_CENTRE));
		rows.append(top_row);

		green = (0, 255, 0, 64);
		green_transparent = (0, 255, 0, 0);
		red = (255, 0, 0, 64);
		red_transparent = (255, 0, 0, 0);

		for g in table_games:
			row = teleostscreen.TableRow();
			hgradientpair_left = None;
			hgradientpair_right = None;
			if g.is_complete():
				score_str = g.format_score();
				if g.s1 > g.s2:
					hgradientpair_left = (green, green_transparent);
					hgradientpair_right = (red_transparent, red);
				elif g.s2 > g.s1:
					hgradientpair_left = (red, red_transparent);
					hgradientpair_right = (green_transparent, green);
			else:
				score_str = "v";
			names = g.get_player_names();
			row.append_value(teleostscreen.RowValue(names[0], teleostscreen.PercentLength(40), text_colour=name_colour, alignment=teleostscreen.ALIGN_RIGHT, hgradientpair=hgradientpair_left));
			row.append_value(teleostscreen.RowValue(score_str, teleostscreen.PercentLength(20), text_colour=score_colour, alignment=teleostscreen.ALIGN_CENTRE));
			row.append_value(teleostscreen.RowValue(names[1], teleostscreen.PercentLength(40), text_colour=name_colour, alignment=teleostscreen.ALIGN_LEFT, hgradientpair=hgradientpair_right));
			rows.append(row);

		return rows;

class HighestWinningScoresFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
	
	def fetch_header_row(self):
		return None;
	
	def fetch_data_rows(self, start_row, num_rows):
		results = self.tourney.ranked_query("""
				select round_no, seq, table_no,
				case when p1_score > p2_score then p1.name else p2.name end winner,
				case when p1_score > p2_score then p1_score else p2_score end winning_score,
				case when p1_score <= p2_score then p1.name else p2.name end loser,
				case when p1_score <= p2_score then p1_score else p2_score end losing_score, tiebreak
				from game g, player p1, player p2
				where g.p1 = p1.id
				and g.p2 = p2.id
				and g.game_type = 'P'
				and p1_score is not null and p2_score is not null
				and p1_score <> p2_score
				order by 5 desc limit %d""" % (num_rows), sort_cols=[5]);
		
		rows = [];
		for r in results:
			row = teleostscreen.TableRow();
			round_desc = "R%dT%d" % (r[1], r[3]);
			winner_name = r[4];
			winner_score = r[5];
			loser_name = r[6];
			loser_score = r[7];
			tiebreak = r[8];

			round_desc_colour = (255, 128, 64);
			name_colour = (255, 255, 255);
			score_colour = (255, 255, 255);

			if tiebreak:
				score_str = "%d* - %d" % (winner_score, loser_score);
			else:
				score_str = "%d - %d" % (winner_score, loser_score);

			row.append_value(teleostscreen.RowValue(round_desc, teleostscreen.PercentLength(15), text_colour=round_desc_colour));
			row.append_value(teleostscreen.RowValue(winner_name, teleostscreen.PercentLength(35), text_colour=name_colour, alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(score_str, teleostscreen.PercentLength(15), text_colour=score_colour, alignment=teleostscreen.ALIGN_CENTRE));
			row.append_value(teleostscreen.RowValue(loser_name, teleostscreen.PercentLength(35), text_colour=name_colour, alignment=teleostscreen.ALIGN_LEFT));
			rows.append(row);
		return rows;

class HighestJointScoresFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
	
	def fetch_header_row(self):
		return None;
	
	def fetch_data_rows(self, start_row, num_rows):
		results = self.tourney.ranked_query("""
				select round_no, seq, table_no, p1.name, p1_score, p2.name,
					p2_score, p1_score + p2_score joint, tiebreak
				from game g, player p1, player p2
				where g.p1 = p1.id and g.p2 = p2.id
				and g.game_type = 'P'
				and g.p1_score is not null
				and g.p2_score is not null
				order by 8 desc limit %d""" % (num_rows), sort_cols=[8]);

		rows = [];
		for r in results:
			row = teleostscreen.TableRow();
			round_desc = "R%dT%d" % (r[1], r[3]);
			name1 = r[4];
			score1 = r[5];
			name2 = r[6];
			score2 = r[7];
			joint_score = r[8];
			tiebreak = r[9];

			round_desc_colour = (255, 128, 64);
			name_colour = (255, 255, 255);
			score_colour = (255, 255, 255);

			if tiebreak and score1 != score2:
				if score1 > score2:
					score_str = "%d* - %d" % (score1, score2);
				else:
					score_str = "%d - %d*" % (score1, score2);
			else:
				score_str = "%d - %d" % (score1, score2);

			row.append_value(teleostscreen.RowValue(round_desc, teleostscreen.PercentLength(15), text_colour=round_desc_colour));
			row.append_value(teleostscreen.RowValue(name1, teleostscreen.PercentLength(35), text_colour=name_colour, alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(score_str, teleostscreen.PercentLength(15), text_colour=score_colour, alignment=teleostscreen.ALIGN_CENTRE));
			row.append_value(teleostscreen.RowValue(name2, teleostscreen.PercentLength(35), text_colour=name_colour, alignment=teleostscreen.ALIGN_LEFT));
			rows.append(row);
		return rows;

class CurrentRoundFixturesFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
	
	def fetch_header_row(self):
		return None;
	
	def fetch_games(self):
		# Find the latest round number
		rounds = self.tourney.get_rounds();
		if not rounds:
			return [];
		#rounds = filter(lambda x : x["type"] == "P", rounds);

		latest_round = max(rounds, key=lambda x : x["num"]);
		latest_round_no = latest_round["num"];

		if latest_round["type"] == "P":
			# If this is a prelim round, just return this round
			return self.tourney.get_games(round_no=latest_round_no);
		else:
			# Otherwise, return this and all previous rounds back to but
			# not including the last prelim round
			rounds = sorted(rounds, key=lambda x : x["num"], reverse=True);
			rounds_to_include = [];
			for r in rounds:
				if r["type"] == "P":
					break;
				else:
					rounds_to_include = [r] + rounds_to_include;

			games = [];
			for r in rounds_to_include:
				games = games + self.tourney.get_games(round_no=r["num"], only_players_known=False);
			return games;
	
	def get_round_name(self, round_no):
		rounds = self.tourney.get_rounds();
		for r in rounds:
			if r["num"] == round_no:
				name = r.get("name", None);
				if not name:
					name = "Round %d" % round_no;
				return name;
		return "";

class HighestLosingScoresFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
	
	def fetch_header_row(self):
		return None;
	
	def fetch_data_rows(self, start_row, num_rows):
		results = self.tourney.ranked_query("""
				select round_no, seq, table_no,
				case when p1_score <= p2_score then p1.name else p2.name end loser,
				case when p1_score <= p2_score then p1_score else p2_score end losing_score,
				case when p1_score > p2_score then p1.name else p2.name end winner,
				case when p1_score > p2_score then p1_score else p2_score end winning_score,
				tiebreak
				from game g, player p1, player p2
				where g.p1 = p1.id
				and g.p2 = p2.id
				and g.game_type = 'P'
				and p1_score is not null and p2_score is not null
				and p1_score <> p2_score
				order by 5 desc limit %d""" % (num_rows), sort_cols=[5]);
		
		rows = [];
		for r in results:
			row = teleostscreen.TableRow();
			round_desc = "R%dT%d" % (r[1], r[3]);
			loser_name = r[4];
			loser_score = r[5];
			winner_name = r[6];
			winner_score = r[7];
			tiebreak = r[8];

			round_desc_colour = (255, 128, 64);
			name_colour = (255, 255, 255);
			score_colour = (255, 255, 255);

			if tiebreak:
				score_str = "%d - %d*" % (loser_score, winner_score);
			else:
				score_str = "%d - %d" % (loser_score, winner_score);

			row.append_value(teleostscreen.RowValue(round_desc, teleostscreen.PercentLength(15), text_colour=round_desc_colour));
			row.append_value(teleostscreen.RowValue(loser_name, teleostscreen.PercentLength(35), text_colour=name_colour, alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(score_str, teleostscreen.PercentLength(15), text_colour=score_colour, alignment=teleostscreen.ALIGN_CENTRE));
			row.append_value(teleostscreen.RowValue(winner_name, teleostscreen.PercentLength(35), text_colour=name_colour, alignment=teleostscreen.ALIGN_LEFT));
			rows.append(row);
		return rows;

class OverachieversFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
	
	def fetch_header_row(self):
		row = teleostscreen.TableRow();

		heading_colour = (255, 255, 255);
		row.append_value(teleostscreen.RowValue("", teleostscreen.PercentLength(10), text_colour=heading_colour, alignment=teleostscreen.ALIGN_RIGHT));
		row.append_value(teleostscreen.RowValue("", teleostscreen.PercentLength(60), text_colour=heading_colour, alignment=teleostscreen.ALIGN_LEFT));
		row.append_value(teleostscreen.RowValue("Seed", teleostscreen.PercentLength(10), text_colour=heading_colour, alignment=teleostscreen.ALIGN_RIGHT));
		row.append_value(teleostscreen.RowValue("Pos", teleostscreen.PercentLength(10), text_colour=heading_colour, alignment=teleostscreen.ALIGN_RIGHT));
		row.append_value(teleostscreen.RowValue("+/-", teleostscreen.PercentLength(10), text_colour=heading_colour, alignment=teleostscreen.ALIGN_RIGHT));
		
		return row;

	
	def fetch_data_rows(self, start_row, num_rows):
		standings = self.tourney.get_standings();
		players = self.tourney.get_players();
		players = sorted(players, key=lambda x : x.rating, reverse=True);

		seeds = dict();
		seed_no = 0;
		joint = 0;
		prev_rating = None;
		for p in players:
			if p.rating == prev_rating:
				joint += 1;
			else:
				seed_no += 1 + joint;
				joint = 0;
			seeds[p.name] = seed_no;
			prev_rating = p.rating;

		positions = dict();
		for s in standings:
			positions[s[1]] = s[0];

		def overac_cmp(p1, p2):
			diff1 = positions[p1.name] - seeds[p1.name];
			diff2 = positions[p2.name] - seeds[p2.name];
			if diff1 < diff2:
				return -1;
			elif diff1 > diff2:
				return 1;
			else:
				if seeds[p1.name] < seeds[p2.name]:
					return 1;
				elif seeds[p1.name] > seeds[p2.name]:
					return -1;
				else:
					return 0;

		players = sorted(players, cmp=overac_cmp);
		rank = 0;
		joint = 0;
		prev_overac = None;
		overac_records = [];
		for p in players:
			overac = positions[p.name] - seeds[p.name];
			seed = seeds[p.name];
			if overac == prev_overac:
				joint += 1;
			else:
				rank += 1 + joint;
				joint = 0;
			overac_records.append((rank, p.name, seed, positions[p.name], -overac));
			prev_overac = overac;

		rank_colour = (255, 255, 0);
		name_colour = (255, 255, 255);
		seed_colour = (0, 128, 128);
		pos_colour = (0, 128, 128);
		overac_colour = (0, 255, 255);

		rows = [];
		for r in overac_records[0:num_rows]:
			row = teleostscreen.TableRow();
			(rank, name, seed, pos, overac) = r;

			row.append_value(teleostscreen.RowValue(str(rank), teleostscreen.PercentLength(10), text_colour=rank_colour, alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(name, teleostscreen.PercentLength(60), text_colour=name_colour, alignment=teleostscreen.ALIGN_LEFT));
			row.append_value(teleostscreen.RowValue(str(seed), teleostscreen.PercentLength(10), text_colour=seed_colour, alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(str(pos), teleostscreen.PercentLength(10), text_colour=pos_colour, alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(("%+d" if overac != 0 else "%d") % overac, teleostscreen.PercentLength(10), text_colour=overac_colour, alignment=teleostscreen.ALIGN_RIGHT));
			rows.append(row);

		return rows;

class QuickestFinishersFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
	
	def fetch_header_row(self):
		round_no = self.tourney.get_latest_round_no();
		if round_no is None:
			return None;
		round_name = self.tourney.get_round_name(round_no);

		row = teleostscreen.TableRow();
		row.append_value(teleostscreen.RowValue(round_name, teleostscreen.PercentLength(50), (192, 192, 192), alignment=teleostscreen.ALIGN_LEFT));
		time_str = time.strftime("%I.%M%p").lower().lstrip("0");
		row.append_value(teleostscreen.RowValue(time_str, teleostscreen.PercentLength(50), (192, 192, 192), alignment=teleostscreen.ALIGN_RIGHT));
		row.set_border(bottom_border=teleostscreen.LineStyle((128, 128, 128), 1));
		return row;

	def fetch_data_rows(self, start_row, num_rows):
		round_no = self.tourney.get_latest_round_no();
		if round_no is None:
			return None;
		games_to_play = self.tourney.get_num_games_to_play_by_table(round_no=round_no);
		finished_tables = [];
		unfinished_tables = [];
		for table in games_to_play:
			count = games_to_play[table];
			if count == 0:
				finished_tables.append(table);
			else:
				unfinished_tables.append(table);

		latest_game_times = self.tourney.get_latest_game_times_by_table(round_no=round_no);
		finishing_times = [];
		for table in latest_game_times:
			if games_to_play[table] == 0:
				finishing_times.append((table, latest_game_times[table]));
		finishing_times = sorted(finishing_times, key=lambda x : x[1]);

		table_colour = (255, 255, 255);
		table_bg_colour = (0, 0, 255, 64);
		time_colour = (0, 255, 0);
		diff_time_colour = (0, 255, 255);

		rows = [];
		first_secs = None;

		# We'll build each row so it only takes up 50% of the screen, because
		# we're going to put them together into two columns.
		for (table, timestamp) in finishing_times:
			stime = time.strptime(timestamp, "%Y-%m-%d %H:%M:%S");
			secs = time.mktime(stime);
			if len(rows) == 0:
				first_secs = secs;
			row = teleostscreen.TableRow();
			row.append_value(teleostscreen.RowValue(str(table), teleostscreen.PercentLength(10), text_colour=table_colour, alignment=teleostscreen.ALIGN_CENTRE, bg_colour=table_bg_colour));
			
			row.append_value(teleostscreen.RowValue(time.strftime("%I.%M%p", stime).lower().lstrip("0"), teleostscreen.PercentLength(20), text_colour=time_colour, alignment=teleostscreen.ALIGN_RIGHT));
			if len(rows) > 0:
				diff = int(secs - first_secs);
				row.append_value(teleostscreen.RowValue("+%dm%02ds" % (diff / 60, diff % 60), teleostscreen.PercentLength(19), text_colour=diff_time_colour, alignment=teleostscreen.ALIGN_RIGHT));
				row.append_value(teleostscreen.RowValue("", teleostscreen.PercentLength(1)));
			else:
				row.append_value(teleostscreen.RowValue("", teleostscreen.PercentLength(20), text_colour=diff_time_colour, alignment=teleostscreen.ALIGN_RIGHT));
			rows.append(row);
		
		def unf_tab_cmp(t1, t2):
			if games_to_play[t1] < games_to_play[t2]:
				return -1;
			elif games_to_play[t1] > games_to_play[t2]:
				return 1;
			else:
				if t1 not in latest_game_times:
					if t2 not in latest_game_times:
						return 0;
					else:
						return 1;
				elif t2 not in latest_game_times and t1 in latest_game_times:
					return -1;
				if latest_game_times[t1] < latest_game_times[t2]:
					return -1;
				elif latest_game_times[t1] > latest_game_times[t2]:
					return 1;
				else:
					return 0;

		unfinished_tables = sorted(unfinished_tables, cmp=unf_tab_cmp);
		for table in unfinished_tables:
			row = teleostscreen.TableRow();
			row.append_value(teleostscreen.RowValue(str(table), teleostscreen.PercentLength(10), text_colour=table_colour, alignment=teleostscreen.ALIGN_CENTRE, bg_colour=table_bg_colour));
			row.append_value(teleostscreen.RowValue("%d to play" % (games_to_play[table]), teleostscreen.PercentLength(40), text_colour=(255, 64, 64), alignment=teleostscreen.ALIGN_LEFT));
			rows.append(row);

		# Fold rows together into two columns
		start_element = start_row * 2;
		num_elements = num_rows * 2;
		rows = rows[start_element:(start_element + num_elements)];

		folded_rows = [];
		for row_num in range(num_rows):
			if row_num >= len(rows):
				left = None;
			else:
				left = rows[row_num];
			if row_num + num_rows >= len(rows):
				right = None;
			else:
				right = rows[row_num + num_rows];
			if left or right:
				folded_rows.append(teleostscreen.TableRow.concat_rows((left, right)));

		return folded_rows;

class TuffLuckFetcher(object):
	def __init__(self, tourney):
		self.tourney = tourney;
	
	def fetch_header_row(self):
		row = teleostscreen.TableRow();
		row.append_value(teleostscreen.RowValue("", teleostscreen.PercentLength(80), text_colour=(192,192,192), alignment=teleostscreen.ALIGN_RIGHT));
		row.append_value(teleostscreen.RowValue("Tuffness", teleostscreen.PercentLength(20), text_colour=(224,224,224), alignment=teleostscreen.ALIGN_RIGHT));
		return row;
	
	def fetch_data_rows(self, start_row, num_rows):
		games = self.tourney.get_games(game_type='P');
		
		# Player names -> list of losing margins
		losing_margins = dict();

		for g in games:
			if g.s1 is not None and g.s2 is not None:
				p = None;
				if g.s1 < g.s2:
					p = g.p1;
				elif g.s1 > g.s2:
					p = g.p2;
				if p:
					if g.tb:
						margin = 0;
					else:
						margin = abs(g.s1 - g.s2);
					losing_margins[p.name] = losing_margins.get(p.name, []) + [margin];

		# List of players who have lost at least three matches
		losing_margins_3 = filter(lambda x : len(losing_margins.get(x, [])) >= 3, losing_margins);

		tuff_luck_order = sorted(losing_margins_3,
				key=lambda x : sum(sorted(losing_margins[x])[0:3]));

		rows = [];

		rank = 0;
		joint = 0;
		prev_tuffness = None;
		for pname in tuff_luck_order:
			tuffness = sum(sorted(losing_margins[pname])[0:3]);
			if tuffness == prev_tuffness:
				joint += 1;
			else:
				rank += joint + 1;
				joint = 0;
			row = teleostscreen.TableRow();
			row.append_value(teleostscreen.RowValue(str(rank), teleostscreen.PercentLength(10), text_colour=(255, 255, 0), alignment=teleostscreen.ALIGN_RIGHT));
			row.append_value(teleostscreen.RowValue(pname, teleostscreen.PercentLength(70), text_colour=(255, 255, 255), alignment=teleostscreen.ALIGN_LEFT));
			row.append_value(teleostscreen.RowValue(str(tuffness), teleostscreen.PercentLength(20), text_colour=(0,255,255), alignment=teleostscreen.ALIGN_RIGHT));
			rows.append(row);
			prev_tuffness = tuffness;

		return rows[0:num_rows];


