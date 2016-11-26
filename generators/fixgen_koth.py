#!/usr/bin/python

import random;
import countdowntourney;
import htmlform;
import cgi;
import urllib;
import gencommon

name = "King of the Hill"
description = "Players are grouped based on their current position in the standings. If the group size is N, the top N players go on the first table, the next N players go on the second table, and so on. No attempt is made to avoid rematches, but patzers are kept apart.";

def lookup_player(players, name):
    for p in players:
        if p.get_name() == name:
            return p;
    raise countdowntourney.PlayerDoesNotExistException("Player %s does not exist! I haven't a clue who they are." % name);

def get_user_form(tourney, settings, div_rounds):
    return gencommon.get_user_form_div_table_size(tourney, settings, div_rounds)

def check_ready(tourney, div_rounds):
    return gencommon.check_ready_existing_games_and_table_size(tourney, div_rounds)

def generate(tourney, settings, div_rounds):
    (ready, excuse) = check_ready(tourney, div_rounds)
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    table_no = 1;
    fixtures = [];
    round_numbers_added = []
    rounds = []
    for div_index in sorted(div_rounds):
        players = filter(lambda x : x.get_division() == div_index, tourney.get_active_players());
        group_size = int(settings.get("d%d_groupsize" % (div_index)))

        groups = [];
        games = tourney.get_games(game_type='P');
        round_no = div_rounds[div_index]
        if games:
            # This is not the first round.
            standings = tourney.get_standings(div_index);
            ordered_players = []
            patzers = []
            for s in standings:
                p = lookup_player(players, s.name)
                if p.rating == 0:
                    patzers.append(p)
                else:
                    ordered_players.append(p)
        else:
            # This is the first round. Put the top rated players on the top
            # table, and so on.
            ordered_players = sorted(players, key=lambda x : x.rating, reverse=True)
            patzers = filter(lambda x : x.rating == 0, ordered_players)
            ordered_players = filter(lambda x : x.rating != 0, ordered_players)

        if group_size == -5:
            group_sizes = countdowntourney.get_5_3_table_sizes(len(players))
        else:
            group_sizes = [ group_size for i in range(len(players) / group_size) ]

        groups = [ [] for i in group_sizes ]

        # Put patzers on the lowest groups
        for i in range(len(patzers)):
            groups[len(groups) - 1 - (i % len(groups))].append(patzers[i])

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

        fixtures += tourney.make_fixtures_from_groups(groups, fixtures, round_no, group_size == -5, division=div_index)
        if round_no not in round_numbers_added:
            rounds.append({"round": round_no, "name" : "Round %d" % (round_no)})
            round_numbers_added.append(round_no)

    d = dict();
    d["fixtures"] = fixtures;
    d["rounds"] = rounds;

    return d;

def save_form_on_submit():
    return False
