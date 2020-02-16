#!/usr/bin/python3

import random;
import countdowntourney;
import htmlform;
import cgicommon
import urllib.request, urllib.parse, urllib.error;
import re
import fixgen
import fixgen_manual

name = "Final between top two"
description = "A round is generated with a single game of type F (final) between the top two players in the standings table."

def check_ready(tourney, div_rounds):
    for div in div_rounds:
        round_no = div_rounds[div]

        existing_games = tourney.get_games(round_no=round_no, division=div)
        if existing_games:
            return (False, "%s: round %d already has %d games in it." % (tourney.get_division_name(div), round_no, len(existing_games)))

        standings = tourney.get_standings(division=div, calculate_qualification=False)
        if len(standings) < 2:
            return (False, "%s: can't generate a final because there are fewer than two players in this division." % (tourney.get_division_name(div)))

        if len(standings) > 2:
            first_place_names = [ x.name for x in standings if x.position == 1 ]
            second_place_names = [ x.name for x in standings if x.position == 2 ]
            if len(first_place_names) > 2:
                # There's a three or more way tie for first place
                problem_place = "first"
                place_names = first_place_names
            elif len(second_place_names) > 1:
                # There's a two or more way tie for second place
                problem_place = "second"
                place_names = second_place_names
            else:
                # Neither of these are true, which means we have an unambiguous
                # top two (either exactly two people in joint first, or one
                # person in first and one in second).
                problem_place = None
                place_names = None
            if problem_place:
                place_string = ", ".join(place_names[0:(len(place_names) - 1)]) + " and " + place_names[-1]
                return (False, "%s: can't automatically generate a final between the top two because there's a tie for %s place between %s. When you've decided who will play the final, use the Raw fixture generator to create the match." % (tourney.get_division_name(div), problem_place, place_string))

    return (True, None)

def generate(tourney, settings, div_rounds):
    generated_groups = fixgen.GeneratedGroups()

    # Check that these rounds don't already have games in them, and that each
    # division we're generating a final for has at least two players in it,
    # and that there isn't a tie for joint second.
    (ready, excuse) = check_ready(tourney, div_rounds)
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse)

    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        standings = tourney.get_standings(division=div_index, calculate_qualification=False)
        final_players = [ tourney.get_player_from_name(s.name) for s in standings[0:2] ]
        generated_groups.add_group(round_no, div_index, final_players)
        generated_groups.set_round_name(round_no, "Final");
        generated_groups.set_game_type(round_no, div_index, "F")

    return generated_groups

def save_form_on_submit():
    return False

def get_user_form(tourney, settings, div_rounds):
    return None
