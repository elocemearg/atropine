import sys
import random
import countdowntourney
import htmlform
import urllib.request, urllib.parse, urllib.error
import cgi
import fixgen

name = "Round Robin"
description = "Pairs only. Every player plays every other player in their division once. We generate N-1 rounds, where N is the number of players in the largest selected division. Smaller selected divisions will sit out later rounds."

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
        div_players = [x for x in players if x.get_division() == div]
        if len(div_players) < 2:
            if num_divisions == 1:
                div_name = "The tournament"
            else:
                div_name = tourney.get_division_name(div)
            return (False, "%s does not have at least two players (it has %d). The Round Robin generator needs at least two players." % (div_name, len(div_players)))

    # It's not necessary that the games in the previous round have all been
    # completed.

    # It's also not necessary that there's an even number of players in a
    # division. If a division has an odd number of players, then one player
    # will sit out each round.
    return (True, None)

def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds)
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse)

    num_divisions = tourney.get_num_divisions()
    players = tourney.get_active_players()

    generated_groups = fixgen.GeneratedGroups()

    for div in div_rounds:
        div_players = sorted([x for x in players if x.get_division() == div], key=lambda x : x.get_rating(), reverse=True)

        # If there are an odd number of players, then add an imaginary dummy
        # player. If a player is drawn to play the dummy then no fixture is
        # generated for the player for that round, and they sit out that
        # round.
        if len(div_players) % 2 != 0:
            div_players.append(None)

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

        top_line = list(range(len(div_players) // 2))
        bottom_line = list(range(len(div_players) - 1, len(div_players) // 2 - 1, -1))
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
                if div_players[i1] is not None and div_players[i2] is not None:
                    generated_groups.add_group(start_round_no + round_offset, div, (div_players[i1], div_players[i2]))

            # Take the last element from top_line and put it on the end of
            # bottom_line, and take the first element of bottom_line and put
            # it after the first element of top_line
            bottom_line.append(top_line[-1])
            top_line = [top_line[0]] + [bottom_line[0]] + top_line[1:-1]
            bottom_line = bottom_line[1:]

    return generated_groups

def save_form_on_submit():
    return False
