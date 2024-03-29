#!/usr/bin/python3

# Treat a draw or an unplayed finals stage (-) as if you won the corresponding
# finals stage.
win_letters = frozenset(['W', 'D', '-'])

# Convert finals form from quarter-final to final, e.g. "WLL" to a fixed
# position, e.g. 4.
def finals_form_to_position(form):
    # If form is not three characters or the player has not played in a final
    # or third place playoff, position is unaffected.
    if len(form) != 3 or form[2] == '-':
        return None

    # If you're playing a third-place match, behave as if you lost a semi-final
    # even if you didn't play one. Convert the string "form" to a list "f" and
    # make this change if necessary.
    f = list(form.upper())
    if form[2].islower():
        f[1] = 'L'

    # Now just do the obvious bit.
    return sum([ (0 if v in win_letters else 2 ** (2 - i)) for (i, v) in enumerate(f) ]) + 1

class RankMethod(object):
    def __init__(self):
        pass

    def get_name(self):
        return ""

    def get_rank_fields(self):
        return []

    def uses_wins(self):
        return "wins" in self.get_rank_fields()

    def uses_points(self):
        return "points" in self.get_rank_fields()

    def uses_spread(self):
        return "spread" in self.get_rank_fields()

    def uses_neustadtl(self):
        return "neustadtl" in self.get_rank_fields()

    def get_min_db_version(self):
        return (0, 0, 0)

    # A line or so of text to be written next to the radio button on the page
    # where the admin selects what rank method they want.
    def get_description(self):
        return ""

    # May contain HTML. Will always be displayed after the result of
    # get_description().
    def get_extra_description(self):
        return ""

    def get_secondary_rank_headings(self, short=False):
        return []

    def get_short_description(self):
        return self.get_description()

    # Key by which to sort the standings table, given a list of StandingsRows.
    def get_standings_row_sort_key_fn(self):
        return lambda s : (s.name,)

    def calculate_secondary_rank_values(self, standings_rows, heat_games, players):
        return

    def sort_standings_rows(self, standings_rows, heat_games, players, rank_finals=False):
        """
        Sort standings_rows according to the subclass rank method.

        standings_rows: a list of StandingsRow objects to sort. In divisioned
        tourneys this will be one for each player in the division. In
        undivisioned tourneys there'll be one for each player in the tourney.

        heat_games: a list of Game objects representing all heat games (type P)
        played or scheduled so far in the tourney, in all divisions. It's
        important to include all divisions, because the ranking method may need
        to know about games a player played when they were in another division
        or before players were split up into divisions.

        players: an array of Player objects representing all the players in
        the tourney, regardless of division.

        rank_finals: sort by the finals_points field in each StandingsRow
        object before anything else.
        """
        non_finals_sort_key_fn = self.get_standings_row_sort_key_fn()
        self.calculate_secondary_rank_values(standings_rows, heat_games, players)
        standings_rows.sort(key=non_finals_sort_key_fn, reverse=True)

        if rank_finals:
            # If someone has played in a final or third-place playoff then we
            # fix their position accordingly.
            relocate_indices_to = []
            for (i, s) in enumerate(standings_rows):
                if len(s.finals_form) >= 3 and s.finals_form[2] != '-':
                    fixed_pos = finals_form_to_position(s.finals_form)
                    if fixed_pos:
                        relocate_indices_to.append((i, fixed_pos))

            relocate_row_to = []
            for (i, fixed_pos) in reversed(relocate_indices_to):
                relocate_row_to.append((standings_rows[i], fixed_pos))
                del standings_rows[i]

            for (s, fixed_pos) in sorted(relocate_row_to, key=lambda x : x[1]):
                assert(fixed_pos >= 1 and fixed_pos <= 8)
                standings_rows.insert(fixed_pos - 1, s)

        if rank_finals:
            sort_key_fn = lambda s : (s.finals_points, non_finals_sort_key_fn(s))
        else:
            sort_key_fn = non_finals_sort_key_fn

        prev_s = None
        pos = 0
        joint = 0
        for s in standings_rows:
            if prev_s and sort_key_fn(prev_s) == sort_key_fn(s):
                joint += 1
            else:
                pos += joint + 1
                joint = 0
            s.position = pos
            prev_s = s
        standings_rows.sort(key=lambda s : (s.position, s.name))

class RankWinsPoints(RankMethod):
    def get_name(self):
        return "Wins then Points"

    def get_rank_fields(self):
        return [ "wins", "points" ]

    def get_standings_row_sort_key_fn(self):
        return lambda s : (s.wins * 2 + s.draws, s.points)

    def get_description(self):
        return "Players are ranked by number of wins then total points scored."

    def get_extra_description(self):
        return """
This is the ranking method used at almost all Countdown events.
If you're running a Countdown event and you're unsure which of these options to
choose, <span style="font-weight: bold;">this is the one you want.</span>
"""

    def get_secondary_rank_headings(self, short=False):
        if short:
            return [ "Pts" ]
        else:
            return [ "Points" ]

    def calculate_secondary_rank_values(self, standings_rows, heat_games, players):
        for s in standings_rows:
            s.set_secondary_rank_values([s.points])


class RankWinsSpread(RankMethod):
    def get_name(self):
        return "Wins then Spread"

    def get_rank_fields(self):
        return [ "wins", "spread" ]

    def get_standings_row_sort_key_fn(self):
        return lambda s : (s.wins * 2 + s.draws, s.spread)

    def get_description(self):
        return "Players are ranked by number of wins then cumulative winning margin (also known as spread or goal difference)."

    def get_short_description(self):
        return "Players are ranked by wins then spread (cumulative winning margin)."

    def get_extra_description(self):
        return "This has never been used at Countdown events but you probably want this one if you're running a Scrabble tournament."

    def get_secondary_rank_headings(self, short=False):
        if short:
            return [ "Spr" ]
        else:
            return [ "Spread" ]

    def calculate_secondary_rank_values(self, standings_rows, heat_games, players):
        for s in standings_rows:
            s.set_secondary_rank_values([s.spread], ["%+d" % (s.spread)])

class RankPoints(RankMethod):
    def get_name(self):
        return "Points only"

    def get_rank_fields(self):
        return ["points"]

    def get_standings_row_sort_key_fn(self):
        return lambda s : (s.points,)

    def get_description(self):
        return "Wins don't matter. Players are ranked by total points scored."

    def get_extra_description(self):
        return "This is only here for legacy reasons and isn't a great way to rank a standings table."

    def get_secondary_rank_headings(self, short=False):
        if short:
            return [ "Pts" ]
        else:
            return [ "Points" ]

    def calculate_secondary_rank_values(self, standings_rows, heat_games, players):
        for s in standings_rows:
            s.set_secondary_rank_values([s.points])

def to_quarters(n):
    whole = int(n)
    quarters = int(abs(n) * 4 + 0.5) % 4
    return str(whole) + ["", "¼", "½", "¾"][quarters]

class RankWinsSumOppWins(RankMethod):
    def __init__(self, neustadtl=False):
        self.neustadtl = neustadtl;

    def get_name(self):
        return "Wins then Solkoff score"

    def get_description(self):
        return "Players are ranked by number of wins, then Solkoff score, then points. Your Solkoff score is the total number of games won by all your opponents, regardless of your results against them."

    def get_extra_description(self):
        return """
<li>Your Solkoff score (also known as Buchholz score) is the total win count of
all your opponents. Unlike with the Neustadtl score, all your opponents count
regardless of whether you beat them.</li>
<li>If one of your opponents plays fewer games than you because they withdrew
or joined late, their missing games count as draws for the purpose of your
Solkoff score. However, this does not apply for Prune opponents.</li>"""

    def get_short_description(self):
        return "Players are ranked by wins, then Solkoff score (sum of opponents' wins), then points."

    def get_standings_row_sort_key_fn(self):
        return lambda s : (s.wins * 2 + s.draws, s.get_secondary_rank_values()[0], s.get_secondary_rank_values()[1])

    def get_secondary_rank_headings(self, short=False):
        if short:
            return [ "Solk", "Pts" ]
        else:
            return [ "Solkoff", "Points" ]

    def get_rank_fields(self):
        return ["wins", "sow", "points"]

    def calculate_secondary_rank_values(self, standings_rows, heat_games, players):
        # Record the number of games scheduled for each player. If someone
        # has played fewer games than the rest then that has special handling
        # (see below).
        name_to_games_scheduled = {}
        for g in heat_games:
            for name in g.get_player_names():
                name_to_games_scheduled[name] = name_to_games_scheduled.get(name, 0) + 1

        # Record the win count for each player mentioned in heat_games.
        # We can't use standings_rows for this because standings_rows contains
        # only the standings for this division, and players might have played
        # other players outside their division because the divisions might
        # have been created mid-tournament.
        name_to_effective_wins = {}
        prunes = set()
        for g in heat_games:
            for p in g.get_players():
                if p.is_prune():
                    prunes.add(p.get_name())
                name_to_effective_wins[p.get_name()] = name_to_effective_wins.get(p.get_name(), 0) + g.get_player_win_count(p)

        # Now for each player in the standings table we want to sort, work
        # out the total win counts of all their opponents (or only opponents
        # they beat, if self.neustadtl). Some of these opponents might not be
        # in standings_rows.
        for s in standings_rows:
            player_name = s.name
            neustadtl_score = 0
            player_num_games = name_to_games_scheduled.get(player_name, 0)
            for g in heat_games:
                if g.is_complete() and not g.is_double_loss() and g.has_player_name(player_name):
                    opp_name = g.get_opponent_name(player_name)
                    if self.neustadtl:
                        # Sum of opponents' wins, but only the opponents
                        # you beat.
                        multiplier = g.get_player_name_win_count(player_name)
                    else:
                        # Simple sum of opponents' wins, regardless of whether
                        # you beat them or not.
                        multiplier = 1
                    opp_num_games = name_to_games_scheduled.get(opp_name, 0)

                    # If this opponent joined late, or retired early, and so
                    # has had fewer games scheduled than we have, and they are
                    # not a Prune, behave as if they got draws for the missing
                    # games. This ensures a player is not disadvantaged if an
                    # opponent they beat early on withdraws.
                    if opp_num_games < player_num_games and opp_name not in prunes:
                        add_opp_draws = player_num_games - opp_num_games
                    else:
                        add_opp_draws = 0
                    neustadtl_score += multiplier * (name_to_effective_wins[opp_name] + add_opp_draws * 0.5)

            s.set_secondary_rank_values([neustadtl_score, s.points], [ to_quarters(neustadtl_score), str(s.points)])

class RankWinsNeustadtl(RankWinsSumOppWins):
    def __init__(self):
        super().__init__(neustadtl=True)

    def get_name(self):
        return "Wins then Neustadtl score"

    def get_rank_fields(self):
        return ["wins", "neustadtl", "points"]

    def get_description(self):
        return "Players are ranked by number of wins, then Neustadtl score, then points. Your Neustadtl score is the total number of games won by all the opponents you beat."

    def get_extra_description(self):
        return """
<li>Your Neustadtl score (also known as Sonneborn-Berger score) is the total
win count of all opponents you beat plus half the total win count of all
opponents you drew against.</li>
<li>Hence, a draw counts as half a win for the win count and the Neustadtl score.</li>
<li>If one of your opponents plays fewer games than you because they withdrew
or joined late, their missing games count as draws for the purpose of your
Neustadtl score. However, this does not apply for Prune opponents.</li>"""

    def get_short_description(self):
        return "Players are ranked by number of wins, then Neustadtl score (sum of defeated opponents' wins), then points."

    def get_secondary_rank_headings(self, short=False):
        if short:
            return [ "Neu", "Pts" ]
        else:
            return [ "Neustadtl", "Points" ]

class RankWinsCumulative(RankMethod):
    def get_name(self):
        return "Wins then Cumulative Win Count"

    def get_rank_fields(self):
        return [ "wins", "cumulwins", "points" ]

    def get_description(self):
        return "Players are ranked by number of wins, then sum of their cumulative win count after reach round, then points scored."

    def get_extra_description(self):
        return """
<li>Your Cumulative Win Count is the sum, for each round, of the total number
of wins you had accumulated up to the end of that round.</li>
<li>For example, suppose that in each of rounds 1, 2, and 3, you win 2 games, 0
games, and 1 game respectively. Your win count at the end of each round is 2,
then 2, then 3. The sum of these counts is 7, so your Cumulative Win Count
after three rounds is 7.</li>
<li>This ranking method gives earlier wins a greater weight than later wins,
reflecting the fact that a player who wins early on is likely to face stronger
opponents in later rounds than someone who got their wins later. For this
reason you should not use this ranking method unless you're using the
Swiss or King of the Hill fixture generator for round 2 onwards.</li>
<li>If a player does not play any games in a round, that round is disregarded
when calculating that player's cumulative win count.</li>
"""

    def get_secondary_rank_headings(self, short=False):
        if short:
            return [ "Cumul", "Pts" ]
        else:
            return [ "Cumulative", "Points" ]

    def get_standings_row_sort_key_fn(self):
        return lambda s : (s.wins * 2 + s.draws, s.get_secondary_rank_values()[0], s.get_secondary_rank_values()[1])

    def calculate_secondary_rank_values(self, standings_rows, heat_games, players):
        name_to_cumul = {}
        name_to_wins = {}
        for s in standings_rows:
            name_to_cumul[s.name] = 0
            name_to_wins[s.name] = 0

        # Sort the list of heat games by round, and work through each round
        # in order.
        round_games = {}
        for g in heat_games:
            game_list = round_games.get(g.get_round_no(), [])
            game_list.append(g)
            round_games[g.get_round_no()] = game_list

        for round_no in sorted(round_games):
            game_list = round_games[round_no]
            played_this_round = set()
            # Count wins in each game in this round
            for g in game_list:
                if g.is_complete() and not g.is_double_loss():
                    for p in g.get_players():
                        player_name = p.get_name()
                        if player_name not in name_to_wins:
                            # Don't need to keep the win count for players
                            # not listed in standings_rows.
                            continue
                        played_this_round.add(player_name)
                        name_to_wins[player_name] += g.get_player_win_count(p)
            # Only increase the cumulative win count of players who have
            # actually played a game in this round
            for name in played_this_round:
                name_to_cumul[name] += name_to_wins[name]

        for s in standings_rows:
            s.set_secondary_rank_values([name_to_cumul[s.name], s.points], [to_quarters(name_to_cumul[s.name]), str(s.points)])
