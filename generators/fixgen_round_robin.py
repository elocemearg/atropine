import sys
import random
import countdowntourney
import htmlform
import urllib
import cgi

name = "Round Robin"
description = "Pairs only. We generate N-1 rounds, where N is the number of players in the largest selected division. Smaller selected divisions will sit out later rounds. Every player plays every other player in their division once."

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def get_user_form(tourney, settings, div_rounds):
    return None

def check_ready(tourney, div_rounds):
    # Make sure all divisions have an even number of players
    num_divisions = tourney.get_num_divisions()
    players = tourney.get_active_players()
    for div in div_rounds:
        div_players = filter(lambda x : x.get_division() == div, players)
        if len(div_players) % 2 != 0:
            if num_divisions == 1:
                div_name = "The tournament"
            else:
                div_name = tourney.get_division_name(div)
            return (False, "%s does not have an even number of active players (it has %d). The Round Robin generator only works with two players to a table." % (div_name, len(div_players)))

    # It's not necessary that the games in the previous round have all been
    # completed
    return (True, None)

def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds)
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse)

    num_divisions = tourney.get_num_divisions()
    players = tourney.get_active_players()
    fixtures = []
    round_numbers_generated = []

    for div in div_rounds:
        div_players = sorted(filter(lambda x : x.get_division() == div, players), key=lambda x : x.get_rating(), reverse=True)
        num_rounds = len(div_players) - 1

        if num_rounds <= 0:
            # Erm...
            continue

        start_round_no = div_rounds[div]

        # Generate len(div_players) - 1 rounds.
        # Classical round robin algorithm: write the player in two lines
        # like this:
        #
        # 0 1 2 3
        # 7 6 5 4
        # 
        # That's the first round: 0v7, 1v6, etc.
        # Then keep player 0 fixed and rotate all the others clockwise:
        #
        # 0 7 1 2
        # 6 5 4 3
        # That's the second round.
        #
        # 0 6 7 1
        # 5 4 3 2
        # That's the third round. And so on.

        top_line = range(len(div_players) / 2)
        bottom_line = range(len(div_players) - 1, len(div_players) / 2 - 1, -1)
        for round_offset in range(num_rounds):
            # Check there aren't already games in this round for this division
            existing_games = tourney.get_games(round_no=(start_round_no + round_offset), division=div)
            if existing_games:
                raise countdowntourney.FixtureGeneratorException("%s: can't generate fixtures for round %d because there are already %d fixtures for this division in this round." % (tourney.get_division_name(div), start_round_no + round_offset, len(existing_games)))

            tables = []
            for i in range(len(top_line)):
                # The player on the top line goes first, and the player on
                # the bottom line second, with the exception of the first
                # column, which alternates each round otherwise player 0
                # would go first in every game.
                if i > 0 or round_offset % 2 == 0:
                    tables.append((top_line[i], bottom_line[i]))
                else:
                    tables.append((bottom_line[i], top_line[i]))
            groups = []
            for (i1, i2) in tables:
                groups.append((div_players[i1], div_players[i2]))

            if start_round_no + round_offset not in round_numbers_generated:
                round_numbers_generated.append(start_round_no + round_offset)

            fixtures += tourney.make_fixtures_from_groups(groups, fixtures,
                    start_round_no + round_offset, False, division=div)
            
            # Take the last element from top_line and put it on the end of
            # bottom_line, and take the first element of bottom_line and put
            # it after the first element of top_line
            bottom_line.append(top_line[-1])
            top_line = [top_line[0]] + [bottom_line[0]] + top_line[1:-1]
            bottom_line = bottom_line[1:]

    fixtures = sorted(fixtures, key=lambda x : (x.round_no, x.division, x.seq))

    rounds = []
    for round_no in round_numbers_generated:
        rounds.append({"round" : round_no, "name" : "Round %d" % (round_no)})

    d = dict()
    d["rounds"] = rounds
    d["fixtures"] = fixtures
    return d

def save_form_on_submit():
    return False
