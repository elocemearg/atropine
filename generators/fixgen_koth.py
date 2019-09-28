#!/usr/bin/python3

import random;
import countdowntourney;
import htmlform;
import cgi;
import urllib.request, urllib.parse, urllib.error;
import gencommon
import fixgen

name = "King of the Hill"
description = "Players are grouped based on their current position in the standings. If the group size is N, the top N players go on the first table, the next N players go on the second table, and so on. Prunes are kept apart, but no attempt is made to avoid rematches, which is why nobody ever uses this generator. Everyone uses the Swiss one instead.";

def lookup_player(players, name):
    for p in players:
        if p.get_name() == name:
            return p;
    return None
    #raise countdowntourney.PlayerDoesNotExistException("Player %s does not exist! I haven't a clue who they are." % name);

def get_user_form(tourney, settings, div_rounds):
    return gencommon.get_user_form_div_table_size(tourney, settings, div_rounds)

def check_ready(tourney, div_rounds):
    return gencommon.check_ready_existing_games_and_table_size(tourney, div_rounds)

def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds)
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    generated_groups = fixgen.GeneratedGroups()

    for div_index in sorted(div_rounds):
        players = [x for x in tourney.get_active_players() if x.get_division() == div_index];
        group_size = int(settings.get("d%d_groupsize" % (div_index)))

        groups = [];
        games = tourney.get_games(game_type='P');
        round_no = div_rounds[div_index]
        if games:
            # This is not the first round.
            standings = tourney.get_standings(div_index);
            ordered_players = []
            prunes = []
            for s in standings:
                p = lookup_player(players, s.name)
                if p:
                    if p.rating == 0:
                        prunes.append(p)
                    else:
                        ordered_players.append(p)
        else:
            # This is the first round. Put the top rated players on the top
            # table, and so on.
            ordered_players = sorted(players, key=lambda x : x.rating, reverse=True)
            prunes = [x for x in ordered_players if x.rating == 0]
            ordered_players = [x for x in ordered_players if x.rating != 0]

        if group_size == -5:
            group_sizes = countdowntourney.get_5_3_table_sizes(len(players))
        else:
            group_sizes = [ group_size for i in range(len(players) // group_size) ]

        groups = [ [] for i in group_sizes ]

        # Put prunes on the lowest groups
        for i in range(len(prunes)):
            groups[len(groups) - 1 - (i % len(groups))].append(prunes[i])

        # Put the other players in the groups with the top players on
        # higher tables.
        standings_index = 0
        current_group = 0
        for p in ordered_players:
            if len(groups[current_group]) >= group_sizes[current_group]:
                current_group += 1
            if current_group >= len(groups):
                break
            groups[current_group].append(p)

        for g in groups:
            generated_groups.add_group(round_no, div_index, g)
        generated_groups.set_repeat_threes(round_no, div_index, group_size == -5)

    return generated_groups

def save_form_on_submit():
    return False
