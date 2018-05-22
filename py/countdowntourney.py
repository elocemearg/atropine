#!/usr/bin/python

import sqlite3;
import re;
import os;

SW_VERSION = "0.7.7"
SW_VERSION_SPLIT = (0, 7, 7)
EARLIEST_COMPATIBLE_DB_VERSION = (0, 7, 0)

RANK_WINS_POINTS = 0;
RANK_POINTS = 1;
RANK_WINS_SPREAD = 2;

RATINGS_MANUAL = 0
RATINGS_GRADUATED = 1
RATINGS_UNIFORM = 2

CONTROL_NUMBER = 1
CONTROL_CHECKBOX = 2

create_tables_sql = """
begin transaction;

-- PLAYER table
create table if not exists player (
    id integer primary key autoincrement,
    name text,
    rating float,
    team_id int,
    short_name text,
    withdrawn int not null default 0,
    division int not null default 0,
    division_fixed int not null default 0,
    avoid_prune int not null default 0,
    unique(name), unique(short_name)
);

-- TEAM table
create table if not exists team (
    id integer primary key autoincrement,
    name text,
    colour int,
    unique(name)
);

insert into team(name, colour) values('White', 255 * 256 * 256 + 255 * 256 + 255);
insert into team(name, colour) values('Blue', 128 * 256 + 255);

-- GAME table, containing scheduled games and played games
create table if not exists game (
    round_no int,
    seq int,
    table_no int,
    division int,
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
    division int,
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

-- metadata for per-view options in teleost (values stored in "options" above)
create table if not exists teleost_options (
    mode int,
    seq int,
    name text primary key,
    control_type int,
    desc text,
    default_value text,
    unique(mode, seq)
);

-- Table in which we persist the HTML form settings given to a fixture
-- generator
create table if not exists fixgen_settings (
    fixgen text,
    name text,
    value text
);

-- Round names. When a fixture generator generates some fixtures, it will
-- probably create a new round. This is always given a number, but it can
-- also be given a name, e.g. "Quarter-finals". The "round type" column is
-- no longer used.
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
select round_no, seq, table_no, game_type, p1 p_id, p1_score p_score,
    p2 opp_id, p2_score opp_score, tiebreak
from game
union all
select round_no, seq, table_no, game_type, p2 p_id, p2_score p_score,
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

create view if not exists player_draws as
select p.id, sum(case when g.p_id is null then 0
                   when g.p_score is null or g.opp_score is null then 0
                   when g.p_score == g.opp_score then 1
                   else 0 end) draws
from player p left outer join heat_game_divided g on p.id = g.p_id
group by p.id;

create view if not exists player_points as
select p.id, sum(case when g.p_score is null then 0
                  when g.tiebreak and g.p_score > g.opp_score
            then g.opp_score
              else g.p_score end) points
from player p left outer join heat_game_divided g on p.id = g.p_id
group by p.id;

create view if not exists player_points_against as
select p.id, sum(case when g.opp_score is null then 0
                  when g.tiebreak and g.opp_score > g.p_score
            then g.p_score
              else g.opp_score end) points_against
from player p left outer join heat_game_divided g on p.id = g.p_id
group by p.id;

create view if not exists player_played as
select p.id, sum(case when g.p_score is not null and g.opp_score is not null then 1 else 0 end) played
from player p left outer join heat_game_divided g on p.id = g.p_id
group by p.id;

create view if not exists player_played_first as
select p.id, count(g.p1) played_first
from player p left outer join completed_game g on p.id = g.p1
group by p.id;

create view if not exists player_standings as
select p.id, p.name, p.division, played.played, wins.wins, draws.draws, points.points, points_against.points_against, ppf.played_first
from player p, player_wins wins, player_draws draws, player_played played,
player_points points, player_points_against points_against,
player_played_first ppf
where p.id = wins.id
and p.id = played.id
and p.id = points.id
and p.id = draws.id
and p.id = points_against.id
and p.id = ppf.id;

-- Tables for controlling the display system Teleost
create table if not exists teleost(current_mode int);
delete from teleost;
insert into teleost values(0);
create table if not exists teleost_modes(num int, name text, desc text);

create table if not exists tr_opts (
    bonus float,
    rating_diff_cap float
);
delete from tr_opts;
insert into tr_opts (bonus, rating_diff_cap) values (50, 40);

-- View for working out tournament ratings
-- For each game, you get 50 + your opponent's rating if you win,
-- your opponent's rating if you draw, and your opponent's rating - 50 if
-- you lost. For the purpose of this calculation, your opponent's rating
-- is your opponent's rating at the start of the tourney, except where that
-- is more than 40 away from your own, in which case it's your rating +40 or
-- -40 as appropriate.
-- The 50 and 40 are configurable, in the tr_opts table.
create view tournament_rating as
    select p.id, p.name,
        avg(case when hgd.p_score > hgd.opp_score then rel_ratings.opp_rating + tr_opts.bonus
                 when hgd.p_score = hgd.opp_score then rel_ratings.opp_rating
                 else rel_ratings.opp_rating - tr_opts.bonus end) tournament_rating
    from player p, heat_game_divided hgd on p.id = hgd.p_id,
        (select me.id p_id, you.id opp_id,
            case when you.rating < me.rating - tr_opts.rating_diff_cap
                then me.rating - tr_opts.rating_diff_cap
                when you.rating > me.rating + tr_opts.rating_diff_cap
                then me.rating + tr_opts.rating_diff_cap
                else you.rating end opp_rating
             from player me, player you, tr_opts) rel_ratings
             on rel_ratings.p_id = p.id and hgd.opp_id = rel_ratings.opp_id,
             tr_opts
    where hgd.p_score is not null and hgd.opp_score is not null
    group by p.id, p.name;

commit;
""";

class TourneyException(Exception):
    def __init__(self, description=None):
        if description:
            self.description = description;

class TourneyInProgressException(TourneyException):
    description = "Tournament is in progress."
    pass;

class PlayerDoesNotExistException(TourneyException):
    description = "Player does not exist."
    pass;

class PlayerExistsException(TourneyException):
    description = "Player already exists."
    pass;

class DuplicatePlayerException(TourneyException):
    description = "No two players are allowed to have the same name."
    pass

class UnknownRankMethodException(TourneyException):
    description = "Unknown ranking method."
    pass;

class DBNameExistsException(TourneyException):
    description = "Tourney name already exists."
    pass;

class DBNameDoesNotExistException(TourneyException):
    description = "No tourney by that name exists."
    pass;

class InvalidDBNameException(TourneyException):
    description = "Invalid tourney name."
    pass;

class InvalidRatingException(TourneyException):
    description = "Invalid rating. Rating must be an integer."
    pass;

class TooManyPlayersException(TourneyException):
    description = "You've got too many players. Turf some out onto the street."
    pass

class IncompleteRatingsException(TourneyException):
    description = "Incomplete ratings - specify ratings for nobody or everybody."
    pass;

class InvalidDivisionNumberException(TourneyException):
    description = "Invalid division number"
    pass

class InvalidPlayerNameException(TourneyException):
    description = "A player's name is not allowed to be blank or consist entirely of whitespace."

class InvalidTableSizeException(TourneyException):
    description = "Invalid table size - number of players per table must be 2 or 3."
    pass;

class FixtureGeneratorException(TourneyException):
    description = "Failed to generate fixtures."
    pass;

class PlayerNotInGameException(TourneyException):
    description = "That player is not in that game."
    pass;

class NotMostRecentRoundException(TourneyException):
    description = "That is not the most recent round."
    pass

class NoGamesException(TourneyException):
    description = "No games have been played."
    pass

class IllegalDivisionException(TourneyException):
    description = "Cannot distribute players into the specified number of divisions in the way you have asked, either because there aren't enough players, or the number of players in a division cannot be set to the requested multiple."
    pass

class DBVersionMismatchException(TourneyException):
    description = "This tourney database file was created with a version of atropine which is not compatible with the one you're using."
    pass

class InvalidEntryException(TourneyException):
    description = "Result entry is not valid."
    pass

class Player(object):
    def __init__(self, name, rating=0, team=None, short_name=None, withdrawn=False, division=0, division_fixed=False, player_id=None, avoid_prune=False):
        self.name = name;
        self.rating = rating;
        self.team = team;
        self.withdrawn = withdrawn
        if short_name:
            self.short_name = short_name
        else:
            self.short_name = name
        self.division = division

        # If true, player has been manually put in this division rather than
        # happened to fall into it because of their rating
        self.division_fixed = division_fixed

        self.player_id = player_id
        self.avoid_prune = avoid_prune
    
    def __eq__(self, other):
        if other is None:
            return False;
        elif self.name == other.name:
            return True;
        else:
            return False;
    
    def __ne__(self, other):
        return not(self.__eq__(other));
    
    # Emulate a 3-tuple
    def __len__(self):
        return 3;

    def __getitem__(self, key):
        return [self.name, self.rating, self.division][key];
    
    def __str__(self):
        return self.name;

    def is_player_known(self):
        return True;

    def is_pending(self):
        return False;
    
    def is_withdrawn(self):
        return self.withdrawn

    def make_dict(self):
        return {
                "name" : self.name,
                "rating" : self.rating
        };

    def get_name(self):
        return self.name;
    
    def get_rating(self):
        return self.rating
    
    def get_id(self):
        return self.player_id
    
    def get_team_colour_tuple(self):
        if self.team:
            return self.team.get_colour_tuple()
        else:
            return None
    
    def get_team(self):
        return self.team

    def get_short_name(self):
        return self.short_name

    def get_division(self):
        return self.division

    def is_division_fixed(self):
        return self.division_fixed

    def is_avoiding_prune(self):
        return self.avoid_prune

def get_first_name(name):
    return name.split(" ", 1)[0]

def get_first_name_and_last_initial(name):
    names = name.split(" ", 1)
    if len(names) < 2 or len(names[1]) < 1:
        return get_first_name(name)
    else:
        return names[0] + " " + names[1][0]

def get_short_name(name, players):
    short_name = get_first_name(name)
    for op in players:
        if name != op[0] and short_name == get_first_name(op[0]):
            break
    else:
        return short_name
    
    short_name = get_first_name_and_last_initial(name)
    for op in players:
        if name != op[0] and short_name == get_first_name_and_last_initial(op[0]):
            break
    else:
        return short_name
    return name

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
        return 3;

    def __getitem__(self, key):
        return [None, 0, 0][key];

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

# COLIN Hangover 2015: each player is assigned a team
class Team(object):
    def __init__(self, team_id, team_name, colour=0xffffff):
        self.team_id = team_id;
        self.name = team_name;
        self.colour = colour;
    
    def get_name(self):
        return self.name
    
    def get_id(self):
        return self.team_id

    def get_hex_colour(self):
        return "%06x" % (self.colour)

    def get_colour_tuple(self):
        return ((self.colour >> 16) & 0xff, (self.colour >> 8) & 0xff, self.colour & 0xff)

class StandingsRow(object):
    def __init__(self, position, name, played, wins, points, draws, spread, played_first, rating, tournament_rating):
        self.position = position
        self.name = name
        self.played = played
        self.wins = wins
        self.points = points
        self.draws = draws
        self.spread = spread
        self.played_first = played_first
        self.rating = rating
        self.tournament_rating = tournament_rating

    def __str__(self):
        return "%3d. %-25s %3dw %3dd %4dp" % (self.position, self.name, self.wins, self.draws, self.points)

    # Emulate a list for bits of the code that require it
    def __len__(self):
        return 8
    
    def __getitem__(self, index):
        return [self.position, self.name, self.played, self.wins, self.points, self.draws, self.spread, self.played_first][index]

class Game(object):
    def __init__(self, round_no, seq, table_no, division, game_type, p1, p2, s1=None, s2=None, tb=False):
        self.round_no = round_no;
        self.seq = seq;
        self.table_no = table_no;
        self.division = division
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
            return "Round %d, %s, Table %d, %s %s %s" % (self.round_no, get_general_division_name(self.division), self.table_no, str(self.p1), self.format_score(), str(self.p2));
        else:
            return "Round %d, %s, Table %d, %s v %s" % (self.round_no, get_general_division_name(self.division), self.table_no, str(self.p1), str(self.p2));
    
    def get_short_string(self):
        if self.is_complete():
            return "%s %s %s" % (str(self.p1), self.format_score(), str(self.p2))
        else:
            return "%s v %s" % (str(self.p1), str(self.p2))
    
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
                "division" : self.division,
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
    
    def get_short_player_names(self):
        return [self.p1.get_short_name(), self.p2.get_short_name()]
    
    def get_player_score(self, player):
        if self.p1.is_player_known() and self.p1 == player:
            score = self.s1;
        elif self.p2.is_player_known() and self.p2 == player:
            score = self.s2;
        else:
            raise PlayerNotInGameException("player %s is not in the game between %s and %s." % (str(player), str(self.p1), str(self.p2)));
        return score;
    
    def get_player_name_score(self, player_name):
        if self.p1.is_player_known() and self.p1.get_name().lower() == player_name.lower():
            return self.s1
        elif self.p2.is_player_known() and self.p2.get_name().lower() == player_name.lower():
            return self.s2
        else:
            raise PlayerNotInGameException("Player %s not in the game between %s and %s." % (str(player_name), str(self.p1), str(self.p2)))
    
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

    def get_division(self):
        return self.division
    
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
        return 10;

    def __getitem__(self, key):
        return [self.round_no, self.seq, self.table_no, self.division, self.game_type, str(self.p1), self.s1, str(self.p2), self.s2, self.tb ][key];


def get_general_division_name(num):
    if num < 0:
        return "Invalid division number %d" % (num)
    elif num > 25:
        return "Division %d" % (num + 1)
    else:
        return "Division %s" % (chr(ord('A') + num))

def get_general_short_division_name(num):
    if num < 0:
        return ""
    elif num > 25:
        return int(num + 1)
    else:
        return chr(ord('A') + num)

class TeleostOption(object):
    def __init__(self, mode, seq, name, control_type, desc, value):
        self.mode = mode
        self.seq = seq
        self.name = name
        self.control_type = control_type
        self.desc = desc
        self.value = value


class Tourney(object):
    def __init__(self, filename, tourney_name, versioncheck=True):
        self.filename = filename;
        self.name = tourney_name;
        self.db = sqlite3.connect(filename);
        if versioncheck:
            cur = self.db.cursor()
            cur.execute("select value from options where name = 'atropineversion'")
            row = cur.fetchone()
            if row is None:
                raise DBVersionMismatchException("This tourney database file was created by an atropine version prior to 0.7.0. It's not compatible with this version of atropine.")
            else:
                version = row[0]
                version_split = version.split(".")
                if len(version_split) != 3:
                    raise DBVersionMismatchException("This tourney database has an invalid version number %s." % (version))
                else:
                    try:
                        version_split = map(int, version_split)
                    except ValueError:
                        raise DBVersionMismatchException("This tourney database has an invalid version number %s." % (version))
                    if tuple(version_split) < EARLIEST_COMPATIBLE_DB_VERSION:
                        raise DBVersionMismatchException("This tourney database was created with atropine version %s, which is not compatible with this version of atropine (%s)" % (version, SW_VERSION))
                self.db_version = tuple(version_split)
        else:
            self.db_version = (0, 0, 0)
    
    def get_name(self):
        return self.name
    
    # Number of games in the GAME table - that is, number of games played
    # or in progress.
    def get_num_games(self):
        cur = self.db.cursor();
        cur.execute("select count(*) from game");
        row = cur.fetchone();
        count = row[0];
        cur.close();
        return count;
    
    def get_next_free_table_number_in_round(self, round_no):
        cur = self.db.cursor()
        cur.execute("select max(table_no) from game g where g.round_no = ?", (round_no,))
        row = cur.fetchone()
        if row is None or row[0] is None:
            next_table_no = 1
        else:
            next_table_no = row[0] + 1
        cur.close()
        return next_table_no
    
    def get_next_free_seq_number_in_round(self, round_no):
        cur = self.db.cursor()
        cur.execute("select max(seq) from game g where g.round_no = ?", (round_no,))
        row = cur.fetchone()
        if row is None or row[0] is None:
            next_seq_no = 1
        else:
            next_seq_no = row[0] + 1
        cur.close()
        return next_seq_no
    
    def get_next_free_round_number_for_division(self, div):
        cur = self.db.cursor()
        cur.execute("select max(round_no) from game g where g.division = ?", (div,))
        row = cur.fetchone()
        if row is None or row[0] is None:
            round_no = 1
        else:
            round_no = row[0] + 1
        cur.close()
        return round_no
    
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
    
    def get_short_round_name(self, round_no):
        cur = self.db.cursor();
        cur.execute("select cast(id as text) short_name from rounds where id = ?", (round_no,));
        row = cur.fetchone();
        if not row:
            cur.close();
            return None;
        else:
            cur.close();
            return row[0];
    
    def get_rounds(self):
        cur = self.db.cursor();
        cur.execute("select g.round_no, r.name from game g left outer join rounds r on g.round_no = r.id group by g.round_no");
        rounds = [];
        for row in cur:
            rdict = dict();
            if row[1] is None:
                rdict["name"] = "Round " + str(row[0]);
            else:
                rdict["name"] = row[1];
            rdict["num"] = row[0];
            rounds.append(rdict);
        cur.close();
        return rounds;

    def get_round(self, round_no):
        cur = self.db.cursor();
        cur.execute("select r.id, r.name from rounds r where id = ?", (round_no,));
        row = cur.fetchone()
        d = None
        if row is not None:
            d = dict()
            d["num"] = row[0]
            d["name"] = row[1]
        cur.close()
        return d
    
    def name_round(self, round_no, round_name):
        # Does round_no already exist?
        cur = self.db.cursor();
        cur.execute("select id from rounds where id = ?", (round_no,));
        rows = cur.fetchall();
        if len(rows) > 0:
            cur.close();
            cur = self.db.cursor();
            cur.execute("update rounds set name = ?, type = null where id = ?", (round_name, round_no));
        else:
            cur.close();
            cur = self.db.cursor();
            cur.execute("insert into rounds(id, name, type) values (?, ?, null)", (round_no, round_name));
        self.db.commit();
        cur.close()

    def get_largest_table_game_count(self, round_no):
        cur = self.db.cursor()
        cur.execute("select max(num_games) from (select table_no, count(*) num_games from game where round_no = ? group by table_no) x", (round_no,))
        result = cur.fetchone()
        if result[0] is None:
            count = 0
        else:
            count = int(result[0])
        self.db.commit()
        cur.close()
        return count;
    
    def player_name_exists(self, name):
        cur = self.db.cursor()
        cur.execute("select count(*) from player where lower(name) = ?", (name.lower(),))
        row = cur.fetchone()
        if row[0]:
            cur.close()
            return True
        else:
            cur.close()
            return False

    def set_player_avoid_prune(self, name, value):
        if self.db_version < (0, 7, 7):
            return
        cur = self.db.cursor()
        cur.execute("update player set avoid_prune = ? where lower(name) = ?", (1 if value else 0, name.lower()))
        cur.close()
        self.db.commit()
    
    def get_player_avoid_prune(self, name):
        if self.db_version < (0, 7, 7):
            return False
        cur = self.db.cursor()
        cur.execute("select avoid_prune from player where lower(name) = ?", (name.lower(),))
        row = cur.fetchone()
        if row:
            retval = bool(row[0])
        else:
            raise PlayerDoesNotExistException("Can't get whether player \"%s\" is allowed to play prunes because there is no player with that name." % (name))
        cur.close()
        self.db.commit()
        return retval
    
    def add_player(self, name, rating, division=0):
        if self.player_name_exists(name):
            raise PlayerExistsException("Can't add player \"%s\" because there is already a player with that name." % (name))
        cur = self.db.cursor()
        cur.execute("insert into player(name, rating, team_id, short_name, withdrawn, division, division_fixed) values(?, ?, ?, ?, ?, ?, ?)",
                (name, rating, None, "", 0, division, 0))
        cur.close()
        self.db.commit()

        # Recalculate everyone's short names
        cur = self.db.cursor()
        players = self.get_players()
        for p in players:
            short_name = get_short_name(p.get_name(), players)
            cur.execute("update player set short_name = ? where lower(name) = ?", (short_name, p.get_name().lower()))
        self.db.commit()

    # players must be a list of 2-tuples or 3-tuples. Each tuple is (name,
    # rating) or (name, rating, division).
    # Alternatively they can be Player objects, which pretend to be 2-tuples.
    # Rating should be a number. The rating may be None for all players,
    # in which case the first player is given a rating of 2000 and subsequent
    # players are rated progressively lower. It is an error to specify a
    # rating for some players and not others.
    # This function removes any players currently registered.
    def set_players(self, players, auto_rating_behaviour=RATINGS_UNIFORM):
        # If there are any games, in this tournament, it's too late to
        # replace the player list. You can, however, withdraw players or
        # add individual players.
        if self.get_num_games() > 0:
            raise TourneyInProgressException("Replacing the player list is not permitted once the tournament has started.");

        # Strip leading and trailing whitespace from player names
        new_player_list = [ (x[0].strip(), x[1], x[2]) for x in players ]
        players = new_player_list

        # Make sure no player names are blank
        for p in players:
            if p[0] == "":
                raise InvalidPlayerNameException()

        # Make sure all the player names are case-insensitively unique
        for pi in range(len(players)):
            for opi in range(pi + 1, len(players)):
                if players[pi][0].lower() == players[opi][0].lower():
                    raise DuplicatePlayerException("No two players are allowed to have the same name, and you've got more than one %s." % (players[pi][0]))

        # For each player, work out a "short name", which will be the first
        # of their first name, first name and last initial, and full name,
        # which is unique for that player.
        new_players = []
        for p in players:
            short_name = get_short_name(p[0], players)
            new_players.append((p[0], p[1], short_name, p[2]))

        players = new_players

        # Check the ratings, if given, are sane, and convert them to integers
        new_players = [];
        for p in players:
            try:
                if p[3] < 0:
                    raise InvalidDivisionNumberException("Player \"%s\" has been given a division number of %d. It's not allowed to be negative." % (p[0], p[3]))
                if p[1] is not None:
                    rating = float(p[1]);
                    if rating != 0 and auto_rating_behaviour != RATINGS_MANUAL:
                        # Can't specify any non-zero ratings if automatic
                        # rating is enabled.
                        raise InvalidRatingException("Player \"%s\" has been given a rating (%g) but you have not selected manual rating. If manual rating is not used, players may not be given manual ratings in the initial player list except a rating of 0 to indicate a prune or bye." % (p[0], rating))
                else:
                    if auto_rating_behaviour == RATINGS_MANUAL:
                        # Can't have unrated players if automatic rating
                        # has been disabled.
                        raise InvalidRatingException("Player \"%s\" does not have a rating. If manual rating is selected, all players must be given a rating." % (p[0]))
                    rating = None;
                new_players.append((p[0], rating, p[2], p[3]));
            except ValueError:
                raise InvalidRatingException("Player \"%s\" has an invalid rating \"%s\". A player's rating must be a number." % (p[0], p[1]));
        players = new_players;

        #ratings = map(lambda x : x[1], filter(lambda x : x[1] is not None, players));
        #if len(ratings) != 0 and len(ratings) != len(players):
        #    raise IncompleteRatingsException("Either every player must be given a rating, or no players may be given ratings in which case ratings will be automatically assigned.");

        if auto_rating_behaviour != RATINGS_MANUAL:
            if auto_rating_behaviour == RATINGS_GRADUATED:
                max_rating = 2000
                min_rating = 1000
            else:
                max_rating = 1000
                min_rating = 1000

            new_players = [];
            rating = max_rating;
            num_unrated_players = len(filter(lambda x : x[1] is None, players))
            num_players_given_auto_rating = 0

            if max_rating != min_rating and num_unrated_players > max_rating - min_rating:
                raise TooManyPlayersException("I don't know what kind of crazy-ass tournament you're running here, but it appears to have more than %d players in it. Automatic rating isn't going to work, and to be honest I'd be surprised if anything else did." % num_unrated_players)

            for p in players:
                if num_unrated_players == 1:
                    rating = max_rating
                else:
                    rating = float(max_rating - num_players_given_auto_rating * (max_rating - min_rating) / (num_unrated_players - 1))
                if p[1] is None:
                    new_players.append((p[0], rating, p[2], p[3]));
                    num_players_given_auto_rating += 1
                else:
                    new_players.append((p[0], p[1], p[2], p[3]));
            players = new_players;

        self.set_attribute("autoratingbehaviour", auto_rating_behaviour);

        self.db.execute("delete from player");

        self.db.executemany("insert into player(name, rating, team_id, short_name, withdrawn, division, division_fixed) values (?, ?, null, ?, 0, ?, 0)", players);
        self.db.commit();

    def get_auto_rating_behaviour(self):
        return self.get_int_attribute("autoratingbehaviour", RATINGS_UNIFORM)
    
    def get_active_players(self):
        # Return the list of players in the tournament who are not marked
        # as withdrawn.
        return self.get_players(exclude_withdrawn=True)
    
    def get_withdrawn_players(self):
        return filter(lambda x : x.withdrawn, self.get_players())
    
    def get_players(self, exclude_withdrawn=False):
        cur = self.db.cursor();
        if self.db_version < (0, 7, 7):
            avoid_prune_value = "0"
        else:
            avoid_prune_value = "p.avoid_prune"
        if exclude_withdrawn:
            condition = "where p.withdrawn = 0"
        else:
            condition = ""

        cur.execute("select p.name, p.rating, t.id, t.name, t.colour, p.short_name, p.withdrawn, p.division, p.division_fixed, p.id, %s from player p left outer join team t on p.team_id = t.id %s order by p.rating desc, p.name" % (avoid_prune_value, condition))
        players = [];
        for row in cur:
            if row[2] is not None:
                team = Team(row[2], row[3], row[4])
            else:
                team = None
            players.append(Player(row[0], row[1], team, row[5], bool(row[6]), row[7], row[8], row[9], row[10]));
        cur.close();
        return players;
    
    def rerate_player(self, name, rating):
        try:
            rating = float(rating)
        except ValueError:
            raise InvalidRatingException("Cannot set %s's rating - invalid rating." % name);
        cur = self.db.cursor();
        cur.execute("update player set rating = ? where lower(name) = ?", (rating, name.lower()));
        if cur.rowcount < 1:
            self.db.rollback();
            raise PlayerDoesNotExistException("Cannot change the rating of player \"" + name + "\" because no player by that name exists.");
        cur.close();
        self.db.commit();
    
    def rename_player(self, oldname, newname):
        players = self.get_players();
        newname = newname.strip();
        if newname == "":
            raise InvalidPlayerNameException()

        for p in players:
            if p.name == newname:
                raise PlayerExistsException("Cannot rename player \"%s\" to \"%s\" because there's already another player called %s." % (oldname, newname, newname));
        cur = self.db.cursor();
        cur.execute("update player set name = ? where lower(name) = ?", (newname, oldname.lower()));
        if cur.rowcount < 1:
            self.db.rollback();
            raise PlayerDoesNotExistException("Cannot rename player \"" + oldname + "\" because no player by that name exists.");
        cur.close();

        # Recalculate everyone's short names, because this name change might
        # mean that short names are no longer unique
        cur = self.db.cursor()
        players = self.get_players()
        for p in players:
            short_name = get_short_name(p.get_name(), players)
            cur.execute("update player set short_name = ? where lower(name) = ?", (short_name, p.get_name().lower()))

        cur.close()
        self.db.commit();

    def set_player_division(self, player_name, new_division):
        cur = self.db.cursor()
        cur.execute("update player set division = ? where lower(name) = ?", (new_division, player_name.lower()))
        cur.close()
        self.db.commit()

    # Put each player in a division. The active players are split into
    # num_divisions divisions, each of which must have a multiple of
    # division_size_multiple players. Names listed as strings in
    # automatic_top_div_players are put in the top division. Beyond that,
    # players are distributed among the divisions so as to make their sizes
    # as equal as possible, while still preserving that the size of every
    # division must be a multiple of division_size_multiple.
    def set_player_divisions(self, num_divisions, division_size_multiple, by_rating=True, automatic_top_div_players=[]):
        players = self.get_players(exclude_withdrawn=True)

        # Make a player_ranks map. Players with lower numbers go in higher
        # divisions. This may be derived from the player's rating (in which
        # case we need to negate it so highly-rated players go in higher
        # divisions) or from the player's position in the standings.
        player_ranks = dict()
        if by_rating:
            for p in self.get_players(exclude_withdrawn=False):
                player_ranks[p.get_name()] = -p.get_rating()
        else:
            for s in self.get_standings():
                player_ranks[s.name] = s.position

        if len(players) % division_size_multiple != 0:
            raise IllegalDivisionException()

        div_players = [ [] for i in range(num_divisions) ]

        remaining_players = []
        for p in players:
            if p.get_name() in automatic_top_div_players:
                div_players[0].append(p)
            else:
                remaining_players.append(p)

        remaining_players = sorted(remaining_players, key=lambda x : player_ranks[x.get_name()]);

        # Number of players in the top division is at least
        # num_players / num_divisions rounded up to the nearest multiple of
        # division_size_multiple.
        players_in_div = len(players) / num_divisions
        if players_in_div % division_size_multiple > 0:
            players_in_div += division_size_multiple - (players_in_div % division_size_multiple)

        max_tables_in_div = (len(players) / division_size_multiple) / num_divisions
        if (len(players) / division_size_multiple) % num_divisions > 0:
            max_tables_in_div += 1

        while len(div_players[0]) < players_in_div:
            div_players[0].append(remaining_players[0])
            remaining_players = remaining_players[1:]

        # If division 1 now has an illegal number of players, which is possible
        # if, for example, there are 64 players in total but 21 players have
        # opted in to division 1, add enough players to satisfy the multiple.
        if len(div_players[0]) % division_size_multiple > 0:
            num_to_add = division_size_multiple - (len(div_players[0]) % division_size_multiple)
            div_players[0] += remaining_players[0:num_to_add]
            remaining_players = remaining_players[num_to_add:]

        # Sanity check that we've got the right number of players left
        if len(remaining_players) % division_size_multiple != 0:
            raise IllegalDivisionException()

        # Number of tables in total
        num_tables = len(players) / division_size_multiple

        # If we need an unequal number of players in each division, make
        # sure the top divisions get more players
        if num_tables % num_divisions > 0 and len(div_players[0]) < max_tables_in_div * division_size_multiple:
            # Add another table to division 1
            div_players[0] += remaining_players[0:division_size_multiple]
            remaining_players = remaining_players[division_size_multiple:]

        if num_divisions > 1:
            # Distribute the remaining players among the remaining divisions as
            # evenly as possible while keeping the size of each division a
            # multiple of division_size_multiple.
            if len(remaining_players) < division_size_multiple * (num_divisions - 1):
                raise ImpossibleDivisionException()

            # Number of tables in the divisions after division 1
            num_tables = len(remaining_players) / division_size_multiple

            # Distribute players amongst divisions, and if we have to have some
            # divisions larger than others, make it the higher divisions.
            for division in range(1, num_divisions):
                div_players[division] += remaining_players[0:((num_tables / (num_divisions - 1)) * division_size_multiple)]
                remaining_players = remaining_players[((num_tables / (num_divisions - 1)) * division_size_multiple):]
                if num_tables % (num_divisions - 1) >= division:
                    # This division needs an extra tablesworth
                    div_players[division] += remaining_players[0:division_size_multiple]
                    remaining_players = remaining_players[division_size_multiple:]

        # Finally, take the withdrawn players, which we haven't put into any
        # division, and put them into the division appropriate for their rank.

        div_rank_ranges = []
        for div_index in range(num_divisions):
            div_rank_ranges.append(
                    (min(player_ranks[x.get_name()] for x in div_players[div_index]), 
                     max(player_ranks[x.get_name()] for x in div_players[div_index])
            ))

        withdrawn_players = filter(lambda x : x.is_withdrawn(), self.get_players(exclude_withdrawn=False))
        for p in withdrawn_players:
            for div in range(num_divisions):
                if div == num_divisions - 1 or player_ranks[p.get_name()] <= div_rank_ranges[div][1]:
                    div_players[div].append(p)
                    break

        sql_params = []
        division = 0
        for l in div_players:
            for p in l:
                sql_params.append((division, int(p.get_name() in automatic_top_div_players), p.get_name().lower()))
            division += 1

        cur = self.db.cursor()
        cur.executemany("update player set division = ?, division_fixed = ? where lower(name) = ?", sql_params)
        cur.close()
        self.db.commit()

    def set_player_withdrawn(self, name, withdrawn):
        withdrawn = bool(withdrawn)
        cur = self.db.cursor()
        cur.execute("update player set withdrawn = ? where name = ?", (1 if withdrawn else 0, name))
        if cur.rowcount < 1:
            self.db.rollback()
            raise PlayerDoesNotExistException("Cannot change withdrawn status for player \"%s\" because no player by that name exists." % (name))
        cur.close()
        self.db.commit()

    def withdraw_player(self, name):
        # Set a player as withdrawn, so that the player is not included in the
        # player list supplied to the fixture generator for future rounds.
        self.set_player_withdrawn(name, 1)

    def unwithdraw_player(self, name):
        # Change a players withdrawn status to 0
        self.set_player_withdrawn(name, 0)
 
    def get_player_name(self, player_id):
        cur = self.db.cursor();
        cur.execute("select name from player where id = ?", (player_id));
        rows = cur.fetchall();
        if len(rows) < 1:
            raise PlayerDoesNotExistException();
        cur.close();
        self.db.commit();
        return rows[0];

    def get_player_tournament_rating(self, name):
        cur = self.db.cursor()
        cur.execute("select tournament_rating from tournament_rating where lower(name) = ?", (name.lower(),))
        row = cur.fetchone()
        if row is None:
            raise PlayerDoesNotExistException()
        tournament_rating = row[0]
        cur.close()
        return tournament_rating

    def get_tournament_rating_bonus_value(self):
        cur = self.db.cursor()
        cur.execute("select bonus from tr_opts")
        row = cur.fetchone()
        if row is None:
            bonus = 50
        else:
            bonus = row[0]
        cur.close()
        return bonus
    
    def get_tournament_rating_diff_cap(self):
        cur = self.db.cursor()
        cur.execute("select rating_diff_cap from tr_opts")
        row = cur.fetchone()
        if row is None:
            diff_cap = 40
        else:
            diff_cap = row[0]
        cur.close()
        return diff_cap

    def set_tournament_rating_config(self, bonus=50, diff_cap=40):
        cur = self.db.cursor()
        cur.execute("update tr_opts set bonus = ?, rating_diff_cap = ?", (bonus, diff_cap))
        cur.close()
        self.db.commit()

    def get_show_tournament_rating_column(self):
        return bool(self.get_int_attribute("showtournamentratingcolumn", 0))
    
    def set_show_tournament_rating_column(self, value):
        self.set_attribute("showtournamentratingcolumn", str(int(value)))

    # games is a list of tuples:
    # (round_no, seq, table_no, game_type, name1, score1, name2, score2, tiebreak)
    def merge_games(self, games):
        try:
            known_games = filter(lambda x : x.are_players_known(), games);
            pending_games = filter(lambda x : not x.are_players_known(), games);

            # Records to insert into game_staging, where we use NULL if the
            # player isn't known yet
            game_records = map(lambda x : (x.round_no, x.seq, x.table_no,
                x.division, x.game_type,
                x.p1.name if x.p1.is_player_known() else None, x.s1,
                x.p2.name if x.p2.is_player_known() else None, x.s2,
                x.tb), games);

            cur = self.db.cursor();

            cur.execute("""create temporary table if not exists game_staging(
                round_no int, seq int, table_no int, division int,
                game_type text, name1 text, score1 integer,
                name2 text, score2 integer, tiebreak integer)""");
            cur.execute("""create temporary table if not exists game_staging_ids(
                round_no int, seq int, table_no int, division int,
                game_type text, p1 integer, score1 integer,
                p2 integer, score2 integer, tiebreak integer)""");
            cur.execute("""create temporary table if not exists game_pending_staging(
                round_no int, seq int, seat int, player_id int)""");
            cur.execute("delete from temp.game_staging");
            cur.execute("delete from temp.game_staging_ids");
            cur.execute("delete from temp.game_pending_staging");

            cur.executemany("insert into temp.game_staging values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", game_records);
            cur.execute("""insert into temp.game_staging_ids
                select g.round_no, g.seq, g.table_no, g.division, g.game_type,
                p1.id, g.score1, p2.id, g.score2, g.tiebreak
                from temp.game_staging g left outer join player p1
                    on g.name1 = p1.name left outer join player p2
                    on g.name2 = p2.name""");
                #where g.name1 = p1.name and g.name2 = p2.name""");

            cur.execute("select count(*) from temp.game_staging_ids")
            results = cur.fetchone()

            # Remove any rows that are already in GAME
            cur.execute("""delete from temp.game_staging_ids
                where exists(select * from game g where
                    g.round_no = game_staging_ids.round_no and
                    g.seq = game_staging_ids.seq and
                    g.table_no = game_staging_ids.table_no and
                    g.division = game_staging_ids.division and
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
                    ts, round_no, round_seq, table_no, division, game_type,
                    p1, p1_score, p2, p2_score, tiebreak, log_type)
                select current_timestamp, round_no, seq, table_no, division,
                    game_type, p1, score1, p2, score2, tiebreak, 1
                from temp.game_staging_ids gs
                where score1 is not null and score2 is not null and
                    p1 is not null and p2 is not null and
                    not exists(select * from game g where
                    g.round_no = gs.round_no and
                    g.seq = gs.seq and
                    g.table_no = gs.table_no and
                    g.division = gs.division and
                    g.game_type = gs.game_type and
                    g.p1 = gs.p1 and
                    g.p2 = gs.p2 and
                    g.p1_score is not null and
                    g.p2_score is not null)""");

            # And write "correction" logs for rows that do have a matching
            # entry in game for (round_no, table_no, game_type, p1, p2)
            # with a non-NULL score.
            cur.execute("""insert into game_log(
                    ts, round_no, round_seq, table_no, division, game_type,
                    p1, p1_score, p2, p2_score, tiebreak, log_type)
                select current_timestamp, round_no, seq, table_no, division,
                    game_type, p1, score1, p2, score2, tiebreak, 2
                from temp.game_staging_ids gs
                where p1 is not null and p2 is not null and
                    exists(select * from game g where
                    g.round_no = gs.round_no and
                    g.seq = gs.seq and
                    g.table_no = gs.table_no and
                    g.division = gs.division and
                    g.game_type = gs.game_type and
                    g.p1 = gs.p1 and
                    g.p2 = gs.p2 and
                    g.p1_score is not null and
                    g.p2_score is not null)""");

            # Insert rows into game if they're not there already
            cur.execute("""insert or replace into game(
                        round_no, seq, table_no, division, game_type,
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

    def delete_round_div(self, round_no, division):
        try:
            cur = self.db.cursor()
            cur.execute("delete from game where round_no = ? and division = ?", (round_no, division))
            num_deleted = cur.rowcount
            cur.execute("select count(*) from game where round_no = ?", (round_no,))
            row = cur.fetchone()
            games_left_in_round = -1
            if row is not None and row[0] is not None:
                games_left_in_round = row[0]
            if games_left_in_round == 0:
                cur.execute("delete from rounds where id = ?", (round_no,))
            cur.close()
            self.db.commit()
            return num_deleted
        except:
            self.db.rollback()
            raise

    def delete_round(self, round_no):
        latest_round_no = self.get_latest_round_no();
        if latest_round_no is None:
            raise NoGamesException()
        if latest_round_no != round_no:
            raise NotMostRecentRoundException()
        
        try:
            cur = self.db.cursor()
            cur.execute("delete from game where round_no = ?", (latest_round_no,))
            cur.execute("delete from rounds where id = ?", (latest_round_no,))
            self.db.commit()
        except:
            self.db.rollback()
            raise

    def alter_games(self, alterations):
        # alterations is (round_no, seq, p1, p2, game_type)
        # but we want (p1name, p2name, game_type, round_no, seq) for feeding
        # into the executemany() call.
        alterations_reordered = map(lambda x : (x[2].get_name().lower(), x[3].get_name().lower(), x[4], x[0], x[1]), alterations);
        cur = self.db.cursor();
        cur.executemany("""
update game
set p1 = (select id from player where lower(name) = ?),
p2 = (select id from player where lower(name) = ?),
game_type = ?
where round_no = ? and seq = ?""", alterations_reordered);
        rows_updated = cur.rowcount;
        cur.close();
        self.db.commit();
        return rows_updated;
    
    def get_player_from_name(self, name):
        sql = "select p.name, p.rating, t.id, t.name, t.colour, p.short_name, p.withdrawn, p.division, p.division_fixed, p.id, %s from player p left outer join team t on p.team_id = t.id where lower(p.name) = ?" % ("0" if self.db_version < (0, 7, 7) else "p.avoid_prune");
        cur = self.db.cursor();
        cur.execute(sql, (name.lower(),));
        row = cur.fetchone();
        cur.close();
        if row is None:
            raise PlayerDoesNotExistException("Player with name \"%s\" does not exist." % name);
        else:
            if row[2] is not None:
                team = Team(row[2], row[3], row[4])
            else:
                team = None
            return Player(row[0], row[1], team, row[5], row[6], row[7], row[8], row[9], row[10]);
    
    def get_player_from_id(self, player_id):
        sql = "select p.name, p.rating, t.id, t.name, t.colour, p.short_name, p.withdrawn, p.division, p.division_fixed, %s from player p left outer join team t on p.team_id = t.id where p.id = ?" % ("0" if self.db_version < (0, 7, 7) else "p.avoid_prune");
        cur = self.db.cursor();
        cur.execute(sql, (player_id,));
        row = cur.fetchone();
        cur.close();
        if row is None:
            raise PlayerDoesNotExistException("No player exists with ID %d" % player_id);
        else:
            if row[2] is None:
                team = None
            else:
                team = Team(row[2], row[3], row[4])
            return Player(row[0], row[1], team, row[5], row[6], row[7], row[8], player_id, row[9]);

    def get_latest_started_round(self):
        cur = self.db.cursor()
        sql = "select max(r.id) from rounds r where (exists(select * from completed_game cg where cg.round_no = r.id) or r.id = (select min(id) from rounds where id >= 0))"
        cur.execute(sql)
        row = cur.fetchone()
        round_no = None
        if row is not None and row[0] is not None:
            round_no = row[0]
        cur.close()
        if round_no is None:
            return None
        return self.get_round(round_no)
    
    def is_round_finished(self, round_no):
        cur = self.db.cursor()
        cur.execute("select count(*) from game g where round_no = ?", (round_no,))
        row = cur.fetchone()
        if row is None or row[0] is None:
            num_games = 0
        else:
            num_games = row[0]
        cur.execute("select count(*) from completed_game cg where round_no = ?", (round_no,))
        row = cur.fetchone()
        if row is None or row[0] is None:
            num_completed_games = 0
        else:
            num_completed_games = row[0]
        cur.close()
        return (num_games > 0 and num_games == num_completed_games)

    def get_current_round(self):
        # Return the latest started round, or if that round is finished and
        # there's a next round, the next round.
        r = self.get_latest_started_round()
        if r is None:
            return None
        if self.is_round_finished(r["num"]):
            cur = self.db.cursor()
            cur.execute("select min(id) from rounds where id > ?", (r["num"],))
            row = cur.fetchone()
            if row is not None and row[0] is not None:
                # There is a next round
                r = self.get_round(row[0])
            cur.close()
        return r
    
    def get_latest_round_no(self):
        cur = self.db.cursor();
        cur.execute("select max(id) from rounds");
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

    def count_games_between(self, p1, p2):
        sql = """select count(*) from game g
where g.p1 is not null and g.p2 is not null
and (g.p1 = ? and g.p2 = ?) or (g.p1 = ? and g.p2 = ?)"""
        cur = self.db.cursor()
        cur.execute(sql, (p1.get_id(), p2.get_id(), p2.get_id(), p1.get_id()))
        row = cur.fetchone()
        cur.close()
        if row and row[0]:
            return row[0]
        else:
            return 0

    def get_games_between(self, round_no, player_name_1, player_name_2):
        conditions = []
        params = []

        if round_no is not None:
            conditions.append("g.round_no = ?")
            params.append(round_no)

        conditions.append("((lower(p1.name) = ? and lower(p2.name) = ?) or (lower(p2.name) = ? and lower(p1.name) = ?))")
        params.append(player_name_1.lower())
        params.append(player_name_2.lower())
        params.append(player_name_1.lower())
        params.append(player_name_2.lower())

        conditions.append("(g.p1 is not null and g.p2 is not null)")

        cur = self.db.cursor()
        sql = """select g.round_no, g.seq, g.table_no, g.division, g.game_type,
                 g.p1, g.p1_score, g.p2, g.p2_score, g.tiebreak
                 from game g, player p1 on g.p1 = p1.id,
                 player p2 on g.p2 = p2.id
                 where g.p1 is not null and g.p2 is not null """;
        for c in conditions:
            sql += " and " + c
        sql += "\norder by g.round_no, g.division, g.seq";
        if len(params) == 0:
            cur.execute(sql)
        else:
            cur.execute(sql, params)

        games = []
        for row in cur:
            (round_no, game_seq, table_no, division, game_type, p1, p1_score, p2, p2_score, tb) = row
            if tb is not None:
                if tb:
                    tb = True
                else:
                    tb = False
            p1 = self.get_player_from_id(p1)
            p2 = self.get_player_from_id(p2)
            game = Game(round_no, game_seq, table_no, division, game_type, p1, p2, p1_score, p2_score, tb)
            games.append(game);

        cur.close();
        self.db.commit();

        return games;



    def get_games(self, round_no=None, table_no=None, game_type=None, only_players_known=True, division=None):
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
        if division is not None:
            conditions.append("g.division = ?")
            params.append(division)

        cur = self.db.cursor();
        sql = """select g.round_no, g.seq, g.table_no, g.division, g.game_type,
                g.p1, g.p1_score, g.p2, g.p2_score, g.tiebreak,
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
        sql += "\norder by g.round_no, g.division, g.seq";
        if len(params) == 0:
            cur.execute(sql);
        else:
            cur.execute(sql, params);

        rounds = self.get_rounds();

        games = [];
        for row in cur:
            (round_no, game_seq, table_no, division, game_type, p1, p1_score, p2, p2_score, tb, seat1_which, seat1_round_no, seat1_seq, seat2_which, seat2_round_no, seat2_seq) = row
            if tb is not None:
                if tb:
                    tb = True
                else:
                    tb = False
            for p_index in (1,2):
                if p_index == 1:
                    p_id = p1;
                else:
                    p_id = p2;
                if p_id is None:
                    if p_index == 1:
                        winner = bool(seat1_which);
                        of_round_no = int(seat1_round_no);
                        of_seq = int(seat1_seq);
                    else:
                        winner = bool(seat2_which);
                        of_round_no = int(seat2_round_no);
                        of_seq = int(seat2_seq);

                    short_name = "R" + str(of_round_no)
                    p = PlayerPending(of_round_no, of_seq, winner, short_name);
                else:
                    p = self.get_player_from_id(p_id);
                if p_index == 1:
                    p1 = p;
                else:
                    p2 = p;
            game = Game(round_no, game_seq, table_no, division, game_type, p1, p2, p1_score, p2_score, tb)
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

    def set_teleost_colour_palette(self, value):
        self.set_attribute("teleostcolourpalette", value)

    def get_teleost_colour_palette(self):
        return self.get_attribute("teleostcolourpalette", "Standard")

    def get_auto_use_vertical(self):
        return self.get_int_attribute("autousevertical", 0) != 0

    def set_auto_use_vertical(self, value):
        self.set_attribute("autousevertical", str(int(value)))

    def set_teleost_animate_scroll(self, value):
        self.set_attribute("teleostanimatescroll", str(int(value)))
    
    def get_teleost_animate_scroll(self):
        return self.get_int_attribute("teleostanimatescroll", 1) != 0

    def set_auto_use_table_index(self, value):
        self.set_attribute("autousetableindex", str(int(value)))

    def get_auto_use_table_index(self):
        return self.get_int_attribute("autousetableindex", 0) != 0
    
    def get_rank_method(self):
        return self.get_int_attribute("rankmethod", RANK_WINS_POINTS);
    
    def is_ranking_by_wins(self):
        return self.get_rank_method() in [ RANK_WINS_POINTS, RANK_WINS_SPREAD ]
    
    def is_ranking_by_points(self):
        return self.get_rank_method() in [ RANK_WINS_POINTS, RANK_POINTS ]
    
    def is_ranking_by_spread(self):
        return self.get_rank_method() == RANK_WINS_SPREAD

    def set_rank_method(self, method):
        if method not in [RANK_WINS_POINTS, RANK_WINS_SPREAD, RANK_POINTS]:
            raise UnknownRankMethodException("Can't rank tourney by method %d because I don't know what that is." % method);
        self.set_attribute("rankmethod", method);
    
    def set_table_size(self, table_size):
        if table_size not in [2,3]:
            raise InvalidTableSizeException("Number of players to a table must be 2 or 3.");
        self.set_attribute("tablesize", int(table_size));
    
    def get_table_size(self):
        return self.get_int_attribute("tablesize", 3);
    
    def set_show_draws_column(self, value):
        self.set_attribute("showdrawscolumn", 1 if value else 0)

    def get_show_draws_column(self):
        return True if self.get_int_attribute("showdrawscolumn", 0) != 0 else False

    def get_num_divisions(self):
        cur = self.db.cursor()
        cur.execute("select max(division) + 1 from player")
        row = cur.fetchone()
        value = row[0]
        if value is None:
            value = 1
        cur.close()
        return value

    def get_num_active_players(self, div_index=None):
        cur = self.db.cursor()
        if div_index is not None:
            cur.execute("select count(*) from player where division = %d and withdrawn = 0" % (div_index))
        else:
            cur.execute("select count(*) from player where withdrawn = 0")
        row = cur.fetchone()
        value = int(row[0])
        cur.close()
        return value
 
    def get_division_name(self, num):
        name = self.get_attribute("div%d_name" % (num))
        if name:
            return name
        else:
            return get_general_division_name(num)

    def set_division_name(self, num, name):
        self.set_attribute("div%d_name" % (num), name)
    
    def get_short_division_name(self, num):
        return get_general_short_division_name(num)

    def get_standings(self, division=None):
        method = self.get_rank_method();
        if method == RANK_WINS_POINTS:
            orderby = "order by s.wins * 2 + s.draws desc, s.points desc, p.name";
            rankcols = [10,4];
        elif method == RANK_WINS_SPREAD:
            orderby = "order by s.wins * 2 + s.draws desc, s.points - s.points_against desc, p.name"
            rankcols = [10,6]
        elif method == RANK_POINTS:
            orderby = "order by s.points desc, p.name";
            rankcols = [4];
        else:
            raise UnknownRankMethodException("This tourney's standings are ranked by method %d, which I don't recognise." % method);

        if division is not None:
            condition = "where s.division = %d " % (division)
        else:
            condition = ""

        results = self.ranked_query("select p.name, s.played, s.wins, s.points, s.draws, s.points - s.points_against spread, s.played_first, p.rating, tr.tournament_rating, s.wins * 2 + s.draws from player_standings s, player p on p.id = s.id left outer join tournament_rating tr on tr.id = p.id " + condition + orderby, rankcols);

        return [ StandingsRow(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9]) for x in results ]
    
    def get_logs_since(self, seq=None, include_new_games=False, round_no=None, maxrows=None):
        cur = self.db.cursor();
        sql = """select seq, datetime(ts, 'localtime') ts, round_no,
                round_seq, table_no, game_type, p1.name p1, p1_score,
                p2.name p2, p2_score, tiebreak, log_type, gl.division,
                case when exists(
                    select * from game_log gl2
                    where gl.round_no = gl2.round_no
                    and gl.round_seq = gl2.round_seq
                    and gl.log_type > 0 and gl2.log_type > 0
                    and gl2.seq > gl.seq
                ) then 1 else 0 end superseded
                from game_log gl, player p1, player p2
                where p1 = p1.id and p2 = p2.id""";
        if seq is not None:
            sql += " and seq > ?"
        if round_no is not None:
            sql += " and round_no = %d" % (round_no)
        if not(include_new_games):
            sql += " and log_type > 0";
        sql += " order by seq desc";
        if maxrows:
            sql += " limit %d" % (maxrows)

        if seq is not None:
            cur.execute(sql, (seq,));
        else:
            cur.execute(sql)

        results = cur.fetchall();
        cur.close();
        return results[::-1]

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

    def set_teleost_options(self, options):
        if self.db_version < (0, 7, 7):
            print self.db_version
            return
        cur = self.db.cursor()
        options_rows = []
        for o in options:
            options_rows.append((o.mode, o.seq, o.name, o.control_type, o.desc, o.value))

        # Insert option metadata
        cur.execute("delete from teleost_options")
        cur.executemany("insert into teleost_options(mode, seq, name, control_type, desc, default_value) values (?, ?, ?, ?, ?, ?)", options_rows)

        cur.close()
        self.db.commit()

    def get_teleost_options(self, mode=None):
        if self.db_version < (0, 7, 7):
            return []
        cur = self.db.cursor()
        options = []
        if mode is not None:
            mode_clause = "where telo.mode = %d" % (mode)
        else:
            mode_clause = ""
        cur.execute("select telo.mode, telo.seq, telo.name, telo.control_type, telo.desc, telo.default_value, att.value from teleost_options telo left outer join options att on telo.name = att.name " + mode_clause + " order by telo.mode, telo.seq")
        for row in cur:
            options.append(TeleostOption(int(row[0]), int(row[1]), row[2], row[3], row[4], row[6] if row[6] is not None else row[5]))
        cur.close()
        self.db.commit()
        return options
    
    def get_teleost_option_value(self, name):
        if self.db_version < (0, 7, 7):
            return None
        cur = self.db.cursor()
        cur.execute("select telo.default_value, att.value from teleost_options telo left outer join options att on telo.name = att.name where telo.name = ?", (name,))
        row = cur.fetchone()
        value = None
        if row is not None:
            if row[1] is not None:
                value = row[1]
            else:
                value = row[0]
        cur.close()
        self.db.commit()
        return value
    
    def set_teleost_option_value(self, name, value):
        self.set_attribute(name, value)

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
    
    def get_max_games_per_table(self, round_no=None):
        sql = """select max(game_count) from (
            select table_no, count(*) game_count
            from game""";
        if round_no is not None:
            sql += " where round_no = %d" % (round_no)
        sql += " group by table_no) x"

        cur = self.db.cursor()
        cur.execute(sql)
        row = cur.fetchone()
        value = None
        if row is not None:
            if row[0] is not None:
                value = row[0]
        cur.close()
        return value
    
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

    def get_teams(self):
        sql = "select id, name, colour from team order by id"
        cur = self.db.cursor()
        cur.execute(sql)
        teams = []
        for (team_id, team_name, colour) in cur:
            teams.append(Team(team_id, team_name, colour))
        cur.close()
        return teams
    
    def get_team_from_id(self, team_id):
        sql = "select id, name, colour from team where id = ?"
        cur = self.db.cursor()
        cur.execute(sql, (team_id,))
        (team_id, team_name, colour) = cur.fetchone();
        cur.close()
        return Team(team_id, team_name, colour)

    def set_player_teams(self, player_teams):
        # argument is list of 2-tuples, containing player name and team ID
        sql = "update player set team_id = ? where name = ?"
        params = []
        for pt in player_teams:
            params.append((None if pt[1] < 0 else pt[1], pt[0]))
        self.db.executemany(sql, params)
        self.db.commit()

    def get_player_teams(self):
        sql = "select p.id, t.id from player p left outer join team t on p.team_id = t.id order by p.name"
        cur = self.db.cursor()
        cur.execute(sql)
        player_team_ids = []
        for (player_id, team_id) in cur:
            player_team_ids.append((player_id, team_id))
        cur.close()

        player_teams = []
        for (p_id, t_id) in player_team_ids:
            if t_id is None or t_id < 0:
                team = None
            else:
                team = self.get_team_from_id(t_id)
            player = self.get_player_from_id(p_id)
            player_teams.append((player, team))
        return player_teams

    def are_players_assigned_teams(self):
        sql = "select count(*) from player where team_id is not null"
        cur = self.db.execute(sql)
        (num,) = cur.fetchone()
        cur.close()
        return num > 0
    
    def get_team_scores(self, round_no=None):
        sql = """
select t.id, sum(case when p1.team_id != t.id and p2.team_id != t.id then 0
                      when p1.team_id == p2.team_id then 0
                      when p1.team_id is null or p2.team_id is null then 0
                      when p1.team_id = t.id and g.p1_score > g.p2_score then 1
                      when p2.team_id = t.id and g.p2_score > g.p1_score then 1
                      else 0 end) score
from team t, game g, player p1, player p2
where g.p1 = p1.id
and g.p2 = p2.id
"""
        if round_no is not None:
            sql += " and g.round_no = %d" % round_no
        sql += " group by t.id order by t.id"

        cur = self.db.cursor();
        cur.execute(sql)
        team_score = []
        for (team_id, score) in cur:
            team_score.append((self.get_team_from_id(team_id), score))
        cur.close()
        return team_score
    
    def store_fixgen_settings(self, fixgen_name, settings):
        cur = self.db.cursor()
        cur.execute("delete from fixgen_settings where fixgen = ?", (fixgen_name,))
        rows = []
        for name in settings:
            rows.append((fixgen_name, name, settings[name]))
        cur.executemany("insert into fixgen_settings values (?, ?, ?)", rows)
        self.db.commit()

    def get_fixgen_settings(self, fixgen_name):
        cur = self.db.cursor()
        cur.execute("select name, value from fixgen_settings where fixgen = ?", (fixgen_name,))
        settings = dict()
        for row in cur:
            settings[row[0]] = row[1]
        self.db.commit()
        return settings

    def close(self):
        self.db.commit();
        self.db.close();

    def get_max_table_number_in_round(self, round_no):
        cur = self.db.cursor()
        cur.execute("select max(table_no) from game where round_no = ?", (round_no,))
        retval = cur.fetchone()[0]
        cur.close()
        return retval

    def get_max_game_seq_in_round(self, round_no):
        cur = self.db.cursor()
        cur.execute("select max(seq) from game where round_no = ?", (round_no,))
        retval = cur.fetchone()[0]
        cur.close()
        return retval

    def make_fixtures_from_groups(self, groups, existing_fixtures, round_no, repeat_threes=False, division=0, game_type='P'):
        start_table_no = self.get_max_table_number_in_round(round_no)
        if start_table_no is None:
            start_table_no = 1
        else:
            start_table_no += 1

        if existing_fixtures:
            max_existing_table_no = max([f.table_no for f in existing_fixtures if f.round_no == round_no] + [0])
            if start_table_no <= max_existing_table_no:
                start_table_no = max_existing_table_no + 1

        start_round_seq = self.get_max_game_seq_in_round(round_no)
        if start_round_seq is None:
            start_round_seq = 1
        else:
            start_round_seq += 1

        if existing_fixtures:
            max_existing_round_seq = max([f.seq for f in existing_fixtures])
            if start_round_seq <= max_existing_round_seq:
                start_round_seq = max_existing_round_seq + 1

        fixtures = [];
        table_no = start_table_no;
        round_seq = start_round_seq;
        for group in groups:
            if len(group) % 2 == 1:
                # If there are an odd number of players on this table, then
                # each player takes a turn at hosting, and the player X places
                # clockwise from the host plays the player X places
                # anticlockwise from the host,
                # for X in 1 .. (len(group) - 1) / 2.
                for host in range(len(group)):
                    for x in range(1, (len(group) - 1) / 2 + 1):
                        left = (host + len(group) + x) % len(group)
                        right = (host + len(group) - x) % len(group)
                        p1 = group[left]
                        p2 = group[right]
                        fixture = Game(round_no, round_seq, table_no, division, game_type, p1, p2)
                        fixtures.append(fixture)
                        round_seq += 1
                        if repeat_threes and len(group) == 3:
                            fixture = Game(round_no, round_seq, table_no, division, game_type, p2, p1)
                            fixtures.append(fixture)
                            round_seq += 1
            else:
                # There are an even number of players. Each player X from
                # X = 0 .. len(group) - 1 plays each player Y for
                # Y in X + 1 .. len(group) - 1
                for x in range(len(group)):
                    for y in range(x + 1, len(group)):
                        p1 = group[x]
                        p2 = group[y]
                        if round_seq % 2 == 0 and len(group) > 2:
                            (p1, p2) = (p2, p1)
                        fixture = Game(round_no, round_seq, table_no, division, game_type, p1, p2)
                        fixtures.append(fixture)
                        round_seq += 1
            table_no += 1
        return fixtures
    
    def get_players_tuff_luck(self, num_losing_games):
        p_id_to_losing_margins = dict()
        cur = self.db.cursor()
        rows = cur.execute("select case when p1_score > p2_score " +
                "then p2 else p1 end p_id, " +
                "case when tiebreak then 0 else abs(p1_score - p2_score) end margin " +
                "from game " +
                "where p1_score is not null and p2_score is not null " +
                "and p1 is not null and p2 is not null and " +
                "p1_score <> p2_score and " +
                "game_type = 'P' " +
                "order by 1")
        for row in rows:
            p_id = row[0]
            margin = row[1]
            p_id_to_losing_margins[p_id] = p_id_to_losing_margins.get(p_id, []) + [margin]
        cur.close()

        new_margin_map = dict()
        for p_id in p_id_to_losing_margins:
            # Limit each player to a maximum of num_losing_games, and remove
            # from the list any player who has fewer losses than that
            margin_list = p_id_to_losing_margins[p_id]
            if len(margin_list) >= num_losing_games:
                new_margin_map[p_id] = sorted(margin_list)[0:num_losing_games]

        p_id_to_losing_margins = new_margin_map

        # Return a list of tuples of the form (player, tuffness, margin_list)
        tuffness_list = []
        for p_id in p_id_to_losing_margins:
            margin_list = p_id_to_losing_margins[p_id]
            p = self.get_player_from_id(p_id)
            if p:
                tuffness_list.append((p, sum(margin_list), margin_list))

        return sorted(tuffness_list, key=lambda x : x[1])
    
    def get_players_overachievements(self, div_index):
        # Get every player's standing position in this division
        standings = self.get_standings(div_index)
        p_id_to_standings_pos = dict()
        p_id_to_rating = dict()
        for s in standings:
            player = self.get_player_from_name(s.name)
            if player:
                p_id_to_standings_pos[player.get_id()] = s.position
                p_id_to_rating[player.get_id()] = s.rating

        p_ids_by_rating = sorted(p_id_to_rating, key=lambda x : p_id_to_rating[x], reverse=True)

        # Work out each player's seed, remembering that two players might have
        # the same rating
        p_id_to_seed = dict()
        seed = 0
        joint = 1
        prev_rating = None
        for p_id in p_ids_by_rating:
            rating = p_id_to_rating[p_id]
            if prev_rating is None or prev_rating != rating:
                seed += joint
                joint = 1
            else:
                joint += 1
            p_id_to_seed[p_id] = seed
            prev_rating = rating

        overachievements = []

        for p_id in p_id_to_standings_pos:
            position = p_id_to_standings_pos[p_id]
            seed = p_id_to_seed[p_id]

            # We want positive numbers to indicate overachievement
            overachievement = seed - position;
            player = self.get_player_from_id(p_id)
            if player:
                overachievements.append((player, seed, position, overachievement))
        return sorted(overachievements, key=lambda x : (x[3], x[1]), reverse=True)
    
    # Return true if all player ratings in a division are the same, with the
    # exception of players with a zero rating.
    def are_player_ratings_uniform(self, div_index):
        cur = self.db.cursor()
        cur.execute("select p.id, p.rating from player p where p.rating > 0 and p.division = ?", (div_index,))
        rating = None
        found_difference = False
        for row in cur:
            if rating is None:
                rating = row[1]
            else:
                if row[1] != rating:
                    found_difference = True
                    break
        cur.close()
        return not found_difference

    def get_banner_text(self):
        return self.get_attribute("teleost_banner_text", "")

    def set_banner_text(self, text):
        self.set_attribute("teleost_banner_text", text)

    def clear_banner_text(self):
        self.set_attribute("teleost_banner_text", "")


def get_5_3_table_sizes(num_players):
    if num_players < 8:
        return []
    table_sizes = []
    players_left = num_players
    while players_left % 5 != 0:
        table_sizes.append(3)
        players_left -= 3
    while players_left > 0:
        table_sizes = [5] + table_sizes
        players_left -= 5
    return table_sizes

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
        tourney = Tourney(dbpath, dbname, versioncheck=True);

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
    tourney = Tourney(dbpath, dbname, versioncheck=False);
    tourney.db_version = SW_VERSION_SPLIT;
    tourney.db.executescript(create_tables_sql);
    tourney.db.execute("insert into options values ('atropineversion', ?)", (SW_VERSION,)) 
    tourney.db.commit();
    return tourney;
