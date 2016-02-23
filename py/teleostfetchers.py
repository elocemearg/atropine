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
        num_divisions = self.tourney.get_num_divisions()
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
                    "log_type" : log_row[11],
                    "division" : log_row[12]
            };
            if l["seq"] > self.last_log_seq:
                self.last_log_seq = l["seq"];
            if show_timestamps:
                timestamp = l["ts"][11:16];
            else:
                timestamp = None;
            game_type = l["game_type"];
            if game_type == "P":
                if num_divisions > 1:
                    round_desc = "R%d %s" % (l["round_no"], self.tourney.get_short_division_name(l["division"]));
                else:
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
            name1_colour = (192, 192, 48);
            name2_colour = (192, 192, 48);
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

            p1 = self.tourney.get_player_from_name(name1)
            p2 = self.tourney.get_player_from_name(name2)
            team1_colour = p1.get_team_colour_tuple()
            team2_colour = p2.get_team_colour_tuple()

            row = teleostscreen.TableRow();
            if timestamp:
                row.append_value(teleostscreen.RowValue(timestamp, None, timestamp_colour, row_padding=row_padding));
            row.append_value(teleostscreen.RowValue(round_desc, None, round_desc_colour, row_padding=row_padding));
            row.append_value(teleostscreen.RowValue(name1, None, name1_colour, row_padding=row_padding));
            if team1_colour:
                row.append_value(teleostscreen.RowValueTeamDot(teleostscreen.PercentLength(2), team1_colour))
            row.append_value(teleostscreen.RowValue(score_str, None, score_colour, row_padding=row_padding));
            if team2_colour:
                row.append_value(teleostscreen.RowValueTeamDot(teleostscreen.PercentLength(2), team2_colour))

            row.append_value(teleostscreen.RowValue(name2, None, name2_colour, row_padding=row_padding));

            rows.append(row);
        return rows;

class TeamScoreFetcher(object):
    def __init__(self, tourney):
        self.tourney = tourney

    def fetch_header_row(self):
        return None
    
    def fetch_data_rows(self, start_row, num_rows):
        row = teleostscreen.TableRow()
        if not self.tourney.are_players_assigned_teams():
            return None
        team_scores = self.tourney.get_team_scores()
        if not team_scores:
            return []
        pc_width_per_team = 100.0 / (len(team_scores))
        for (team, score) in team_scores:
            hex_colour = int(team.get_hex_colour(), 16)
            bgred = (hex_colour >> 16) & 0xff
            bggreen = (hex_colour >> 8) & 0xff
            bgblue = (hex_colour) & 0xff

            if (bgred + bggreen / 2 + bgblue) / 3 < 128:
                text_colour = (255, 255, 255)
            else:
                text_colour = (0, 0, 0)

            row.append_value(teleostscreen.RowValue(str(score), teleostscreen.PercentLength(pc_width_per_team), text_colour, teleostscreen.ALIGN_CENTRE, bg_colour=(bgred, bggreen, bgblue)));
        return [row]

def row_to_div_and_offset(div_standings, start_row, page_length):
    # Given that the screen has space for page_length rows, and every division
    # starts on a new page, work out which division we're displaying.
    div_num_pages = []
    for standings in div_standings:
        div_num_pages.append((len(standings) + page_length - 1) / page_length)

    div_start_offset = start_row
    selected_division = None
    for div_index in range(len(div_standings)):
        if div_start_offset < div_num_pages[div_index] * page_length:
            selected_division = div_index
            break
        else:
            div_start_offset -= div_num_pages[div_index] * page_length

    return (selected_division, div_start_offset)

class StandingsFetcher(object):
    def __init__(self, tourney, use_short_names=False):
        self.tourney = tourney;
        self.use_short_names = use_short_names
        self.short_name_widths = (12, 48, 10, 10, 0, 20)
        self.short_name_widths_inc_draws = (12, 38, 10, 10, 10, 20)
        self.ordinary_name_widths = (10, 55, 10, 10, 0, 15)
        self.ordinary_name_widths_inc_draws = (10, 45, 10, 10, 10, 15)

    def fetch_header_row(self):
        return self.fetch_header_row_for_page()

    def fetch_header_row_for_page(self, start_row=None, page_length=None):
        if start_row is not None and page_length is not None:
            num_divisions = self.tourney.get_num_divisions()
            if num_divisions <= 1:
                division_name = ""
            else:
                div_standings = [ self.tourney.get_standings(div_index) for div_index in range(num_divisions) ]
                (selected_division, div_start_offset) = row_to_div_and_offset(div_standings, start_row, page_length)
                if selected_division is not None:
                    division_name = self.tourney.get_division_name(selected_division)
                else:
                    division_name = ""
        else:
            division_name = ""

        draws_exist = self.tourney.get_show_draws_column()
        if self.use_short_names:
            (pos_width_pc, name_width_pc, played_width_pc, wins_width_pc, draws_width_pc, points_width_pc) = self.short_name_widths_inc_draws if draws_exist else self.short_name_widths
        else:
            (pos_width_pc, name_width_pc, played_width_pc, wins_width_pc, draws_width_pc, points_width_pc) = self.ordinary_name_widths_inc_draws if draws_exist else self.ordinary_name_widths

        row = teleostscreen.TableRow();
        grey = (128, 128, 128);
        white = (255, 255, 255);
        green = (32, 255, 32)
        row.append_value(teleostscreen.RowValue("", teleostscreen.PercentLength(pos_width_pc), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
        row.append_value(teleostscreen.RowValue(division_name, teleostscreen.PercentLength(name_width_pc), text_colour=green));
        row.append_value(teleostscreen.RowValue("P", teleostscreen.PercentLength(played_width_pc), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
        row.append_value(teleostscreen.RowValue("W", teleostscreen.PercentLength(wins_width_pc), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
        if draws_exist:
            row.append_value(teleostscreen.RowValue("D", teleostscreen.PercentLength(draws_width_pc), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
        if self.tourney.get_rank_method() == countdowntourney.RANK_WINS_SPREAD:
            row.append_value(teleostscreen.RowValue("Spr", teleostscreen.PercentLength(points_width_pc), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
        else:
            row.append_value(teleostscreen.RowValue("Pts", teleostscreen.PercentLength(points_width_pc), text_colour=grey, alignment=teleostscreen.ALIGN_RIGHT));
        row.set_border(bottom_border=teleostscreen.LineStyle((96, 96, 96), 1));
        return row;
    
    def fetch_data_rows(self, start_row, num_rows):
        pos_colour = (255, 255, 0);
        name_colour = (255,255,255);
        played_colour = (0, 128, 128);
        if self.tourney.get_rank_method() in (countdowntourney.RANK_WINS_POINTS, countdowntourney.RANK_WINS_SPREAD):
            wins_colour = (0, 255, 255)
        else:
            wins_colour = (0, 128, 128)
        points_colour = (0, 255, 255);

        div_standings = []
        num_divisions = self.tourney.get_num_divisions()
        for div_index in range(num_divisions):
            standings = self.tourney.get_standings(division=div_index)
            div_standings.append(standings)

        (selected_division, div_start_offset) = row_to_div_and_offset(div_standings, start_row, num_rows)

        # Past the end
        if selected_division is None:
            return None

        standings = div_standings[selected_division]

        if div_start_offset >= len(standings):
            return None;
        
        subset = standings[div_start_offset:(div_start_offset + num_rows)];

        draws_exist = self.tourney.get_show_draws_column();

        rows = [];
        for player in subset:
            row = teleostscreen.TableRow();
            player_object = self.tourney.get_player_from_name(str(player[1]))
            team_colour = player_object.get_team_colour_tuple()
            if self.use_short_names:
                display_name = player_object.get_short_name()
                (pos_width_pc, name_width_pc, played_width_pc, wins_width_pc, draws_width_pc, points_width_pc) = self.short_name_widths_inc_draws if draws_exist else self.short_name_widths;
            else:
                display_name = player_object.get_name()
                (pos_width_pc, name_width_pc, played_width_pc, wins_width_pc, draws_width_pc, points_width_pc) = self.ordinary_name_widths_inc_draws if draws_exist else self.ordinary_name_widths

            row.append_value(teleostscreen.RowValue(str(player[0]), teleostscreen.PercentLength(pos_width_pc), text_colour=pos_colour, alignment=teleostscreen.ALIGN_RIGHT));
            if team_colour:
                row.append_value(teleostscreen.RowValueTeamDot(teleostscreen.PercentLength(3), team_colour))
                row.append_value(teleostscreen.RowValue(display_name, teleostscreen.PercentLength(name_width_pc - 3), text_colour=name_colour));
            else:
                row.append_value(teleostscreen.RowValue(display_name, teleostscreen.PercentLength(name_width_pc), text_colour=name_colour));
            row.append_value(teleostscreen.RowValue(str(player[2]), teleostscreen.PercentLength(played_width_pc), text_colour=played_colour, alignment=teleostscreen.ALIGN_RIGHT));
            row.append_value(teleostscreen.RowValue(str(player[3]), teleostscreen.PercentLength(wins_width_pc), text_colour=wins_colour, alignment=teleostscreen.ALIGN_RIGHT));
            if draws_exist:
                row.append_value(teleostscreen.RowValue(str(player[5]), teleostscreen.PercentLength(draws_width_pc), text_colour=wins_colour, alignment=teleostscreen.ALIGN_RIGHT));
            if self.tourney.get_rank_method() == countdowntourney.RANK_WINS_SPREAD:
                row.append_value(teleostscreen.RowValue("%+d" % (player.spread), teleostscreen.PercentLength(points_width_pc), text_colour=points_colour, alignment=teleostscreen.ALIGN_RIGHT));
            else:
                row.append_value(teleostscreen.RowValue(str(player.points), teleostscreen.PercentLength(points_width_pc), text_colour=points_colour, alignment=teleostscreen.ALIGN_RIGHT));
            rows.append(row);

        return rows;

class TableResultsFetcher(object):
    def __init__(self, tourney, use_short_names=False):
        self.tourney = tourney;
        self.use_short_names = use_short_names
    
    def fetch_header_row(self):
        return None;

    def fetch_data_rows(self, start_row, num_rows_to_fetch):
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
        
        pages = []
        current_page = []
        #desired_table_index = start_row / num_rows;
        games = self.tourney.get_games(round_no=latest_round_no);
        games = sorted(games, key=lambda x : x.table_no);

        # If each table has only one game on it, group the matches by
        # division rather than putting in a new heading (containing the table
        # number) for each match.
        prev_table_no = None
        for g in games:
            if prev_table_no == g.table_no:
                get_group_number = lambda x : x.table_no
                get_group_name = lambda x : "Table %d" % (x)
                break
            prev_table_no = g.table_no
        else:
            get_group_number = lambda x : x.division
            if self.tourney.get_num_divisions() <= 1:
                get_group_name = lambda x : ""
            else:
                get_group_name = lambda x : self.tourney.get_division_name(x)

        prev_group_no = None

        for g in games:
            add_header = False
            add_gap_before_header = False
            if prev_group_no is None or prev_group_no != get_group_number(g):
                # New group... if the number of games in this group will
                # fit onto this page, draw them on this page, otherwise
                # open a new page
                group_no = get_group_number(g)
                games_in_group = len(filter(lambda x : get_group_number(x) == group_no, games))
                if len(current_page) > 0:
                    add_gap_before_header = True

                if len(current_page) > 0 and len(current_page) + int(add_gap_before_header) + 1 + games_in_group > num_rows_to_fetch:
                    pages.append(current_page)
                    current_page = []
                    add_gap_before_header = False

                add_header = True
            elif len(current_page) >= num_rows_to_fetch:
                # We're out of space on the screen, force a new page.
                pages.append(current_page)
                current_page = []
                add_header = True
                add_gap_before_header = False

            if add_gap_before_header:
                current_page.append(teleostscreen.TableRow())

            if add_header:
                top_row = teleostscreen.TableRow();
                top_row_colour = (0, 192, 192);
                name_colour = (255, 255, 255);
                score_colour = (255, 255, 255);
                top_row.append_value(teleostscreen.RowValue("%s   %s" % (latest_round_name, get_group_name(group_no)), teleostscreen.PercentLength(100), text_colour=top_row_colour, alignment=teleostscreen.ALIGN_CENTRE));
                current_page.append(top_row);

            green = (0, 255, 0, 64);
            green_transparent = (0, 255, 0, 0);
            red = (255, 0, 0, 64);
            red_transparent = (255, 0, 0, 0);
            yellow = (255, 255, 0, 64)
            yellow_transparent = (255, 255, 0, 0)

            row = teleostscreen.TableRow();
            hgradientpair_left = None;
            hgradientpair_right = None;
            if g.is_complete():
                score_str = g.format_score();
                if self.use_short_names:
                    score_str = "".join(score_str.split())
                if g.s1 > g.s2:
                    hgradientpair_left = (green, green_transparent);
                    hgradientpair_right = (red_transparent, red);
                elif g.s2 > g.s1:
                    hgradientpair_left = (red, red_transparent);
                    hgradientpair_right = (green_transparent, green);
                else:
                    hgradientpair_left = (yellow, yellow_transparent)
                    hgradientpair_right = (yellow_transparent, yellow)
            else:
                score_str = "v";

            team = g.p1.get_team()
            if team:
                team1_colour = team.get_colour_tuple()
                name1_pc = 37
            else:
                team1_colour = None
                name1_pc = 40
            team = g.p2.get_team()
            if team:
                team2_colour = team.get_colour_tuple()
                name2_pc = 37
            else:
                team2_colour = None
                name2_pc = 40

            if self.use_short_names:
                names = g.get_short_player_names()
                name1_pc -= 4
                name2_pc -= 4
                score_width_pc = 28
            else:
                names = g.get_player_names()
                score_width_pc = 20

            # Name of player 1
            row.append_value(teleostscreen.RowValue(names[0], teleostscreen.PercentLength(name1_pc), text_colour=name_colour, alignment=teleostscreen.ALIGN_RIGHT, hgradientpair=hgradientpair_left));
            # Player 1's team colour dot, if applicable
            if team1_colour:
                row.append_value(teleostscreen.RowValueTeamDot(teleostscreen.PercentLength(3), team1_colour))
            
            # Score
            row.append_value(teleostscreen.RowValue(score_str, teleostscreen.PercentLength(score_width_pc), text_colour=score_colour, alignment=teleostscreen.ALIGN_CENTRE));
            # Player 2's team colour dot, if applicable
            if team2_colour:
                row.append_value(teleostscreen.RowValueTeamDot(teleostscreen.PercentLength(3), team2_colour))
            # Name of player 2
            row.append_value(teleostscreen.RowValue(names[1], teleostscreen.PercentLength(name2_pc), text_colour=name_colour, alignment=teleostscreen.ALIGN_LEFT, hgradientpair=hgradientpair_right));

            current_page.append(row)
            prev_group_no = group_no

        pages.append(current_page)
        
        requested_page = start_row / num_rows_to_fetch
        if requested_page < 0 or requested_page >= len(pages):
            return None
        else:
            return pages[requested_page]

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
            stime = time.strptime(timestamp + " UTC", "%Y-%m-%d %H:%M:%S %Z");
            secs = time.mktime(stime);
            localtime = time.localtime(secs)
            if len(rows) == 0:
                first_secs = secs;
            row = teleostscreen.TableRow();
            row.append_value(teleostscreen.RowValue(str(table), teleostscreen.PercentLength(10), text_colour=table_colour, alignment=teleostscreen.ALIGN_CENTRE, bg_colour=table_bg_colour));
            
            row.append_value(teleostscreen.RowValue(time.strftime("%I.%M%p", localtime).lower().lstrip("0"), teleostscreen.PercentLength(20), text_colour=time_colour, alignment=teleostscreen.ALIGN_RIGHT));
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


