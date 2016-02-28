#!/usr/bin/python

import random;
import countdowntourney;
import htmlform;
import cgi;
import urllib;

name = "COEDI Fixture Generator"
description = "User-specified fixtures for the first round. Subsequent rounds put the top three players on the top table, the next three players on the second table and so on. Players may meet more than once.";

def lookup_player(players, name):
    for p in players:
        if p.get_name() == name:
            return p;
    raise countdowntourney.PlayerDoesNotExistException("Player %s does not exist! I haven't a clue who they are." % name);

def get_user_form(tourney, settings):
    table_size = tourney.get_table_size();
    games = tourney.get_games(game_type='P');
    if len(games):
        # Not the first round.
        return None;

    players = sorted(tourney.get_active_players(), key=lambda x : x.get_name());

    set_players = [ None for i in range(0, len(players)) ];

    # This is the first round.
    # Ask the user to fill in N little drop-down boxes, where N is the
    # number of players, to decide who's going on what table.
    for player_index in range(0, len(players)):
        name = settings.get("player%d" % player_index);
        if name:
            set_players[player_index] = lookup_player(players, name);
    
    # Slot numbers which contain a player already contained in another slot
    duplicate_slots = [];

    # Slot numbers which don't contain a player;
    empty_slots = [];
    player_index = 0;
    for p in set_players:
        if p is None:
            empty_slots.append(player_index);
        else:
            count = 0;
            for q in set_players:
                if q is not None and q.get_name() == p.get_name():
                    count += 1;
            if count > 1:
                duplicate_slots.append(player_index);
        player_index += 1;
    
    if not duplicate_slots and not empty_slots:
        # Yay!
        return None

    # Otherwise, assemble a whacking great HTML form.
    elements = [];
    player_index = 0;
    table_no = 1;
    elements.append(htmlform.HTMLFragment("""<style type=\"text/css\">
.seltable td {
    padding: 5px;
}
.duplicateplayer {
    background-color: red;
}
.emptyslot {
    background-color: #ffaa00;
}
</style>
"""));
    elements.append(htmlform.HTMLFragment("<p>Use the drop-down boxes to select which players are on each table.</p>\n"));
    elements.append(htmlform.HTMLFragment("<table class=\"seltable\">\n<tr><td>Table 1</td>\n"));
    prev_table_no = None;
    unselected_names = map(lambda x : x.get_name(), players);

    for p in set_players:
        table_no = 1 + player_index / table_size;
        
        # If there are three players per table and we don't have a multiple
        # of three and we're one over a multiple of three, the last two tables
        # should have one person each.
        if table_size == 3 and len(players) % 3 == 1:
            if player_index == len(players) - 2:
                table_no += 1;

        if prev_table_no is not None and table_no != prev_table_no:
            elements.append(htmlform.HTMLFragment("</tr>\n<tr>\n"));
            elements.append(htmlform.HTMLFragment("<td>Table %d</td>\n" % table_no));

        td_style = "";
        if player_index in duplicate_slots:
            td_style = "class=\"duplicateplayer\"";
        elif player_index in empty_slots:
            td_style = "class=\"emptyslot\"";
        elements.append(htmlform.HTMLFragment("<td %s>" % td_style));
        player_option_list = [];
        player_option_list.append(htmlform.HTMLFormDropDownOption("", " -- select --"));
        selected_name = "";

        # Build up our list of players for this drop-down box
        for q in players:
            opt = htmlform.HTMLFormDropDownOption(q.get_name(), q.get_name());
            if p is not None and q.get_name() == p.get_name():
                selected_name = p.get_name();
            player_option_list.append(opt);

        # Select the appropriate player
        sel = htmlform.HTMLFormDropDownBox("player%d" % player_index, player_option_list);
        sel.set_value(selected_name);

        if selected_name in unselected_names:
            unselected_names.remove(selected_name);

        elements.append(sel);
        elements.append(htmlform.HTMLFragment("</td>"));
        player_index += 1;
        prev_table_no = table_no;

    elements.append(htmlform.HTMLFragment("</tr></table>"));
    elements.append(htmlform.HTMLFormSubmitButton("submit", "Submit"));

    if duplicate_slots:
        elements.append(htmlform.HTMLFragment("<p>You have players in multiple slots: these are highlighted in <font color=\"#ff0000\"><strong>red</strong></font>.</p>"));
    if empty_slots:
        elements.append(htmlform.HTMLFragment("<p>Some slots are not yet filled: these are highlighted in <font color=\"#ffaa00\"><strong>orange</strong></font>.</p>"));

    if unselected_names:
        elements.append(htmlform.HTMLFragment("<p>Players still to be given a table:</p>\n"));
        elements.append(htmlform.HTMLFragment("<blockquote>\n"));
        for name in unselected_names:
            elements.append(htmlform.HTMLFragment("<li>%s</li>\n" % cgi.escape(name)));
        elements.append(htmlform.HTMLFragment("</blockquote>\n"));

    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s" % urllib.quote_plus(tourney.name), elements);
    return form;

def check_ready(tourney):
    players = tourney.get_active_players();
    table_size = tourney.get_table_size();

    if len(players) < 3:
        return (False, "At least three players are required.");

    if table_size != 3 and len(players) % table_size != 0:
        return (False, "If the table size isn't 3, then the number of player smust be a multiple of the table size.");

    games = tourney.get_games(game_type='P');
    if games:
        # This is not the first round. Are there any unplayed games in the
        # last round?
        latest_round_no = max(map(lambda x : x.round_no, games));
        latest_round_games = filter(lambda x : x.round_no == latest_round_no, games);
        for g in latest_round_games:
            if not g.is_complete():
                return (False, "Not all games in the latest round (%d) are complete." % latest_round_no);
    
    return (True, None);

def generate(tourney, settings):
    (ready, excuse) = check_ready(tourney);    
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    table_no = 1;
    round_seq = 1;
    fixtures = [];
    num_divisions = tourney.get_num_divisions()
    for div_index in range(num_divisions):
        players = filter(lambda x : x.get_division() == div_index, tourney.get_active_players());
        table_size = tourney.get_table_size();

        groups = [];
        games = tourney.get_games(game_type='P');
        if games:
            # This is not the first round.
            standings = tourney.get_standings(div_index);
            ordered_players = []
            for s in standings:
                try:
                    p = lookup_player(players, s.name)
                    ordered_players.append(p)
                except countdowntourney.PlayerDoesNotExistException:
                    pass
            for i in range(0, len(ordered_players), table_size):
                groups.append(ordered_players[i:(i + table_size)]);
            round_no = max(map(lambda x : x.round_no, games)) + 1;
        else:
            # This is the first round. Player names should have been specified
            # by a series of drop-down boxes.
            player_names = [];
            for i in range(0, len(players)):
                name = settings.get("player%d" % i);
                if name:
                    player_names.append(name);
                else:
                    raise countdowntourney.FixtureGeneratorException("Player %d not specified. This is probably a bug, as the form should have made you fill in all the boxes." % i);

            selected_players = map(lambda x : lookup_player(players, x), player_names);

            for i in range(0, len(selected_players), table_size):
                groups.append(selected_players[i:(i + table_size)]);
            round_no = 1;

        if table_size == 3:
            # If we've got one more than a multiple of three, then the bottom
            # four players ABCD are split across two tables. A plays B and C 
            # plays D, then B plays C and D plays A.
            # If we've got two more than a multiple of three, then the bottom
            # two players AB are put on one table. A plays B then B plays A.
            if len(players) % 3 == 1:
                offcuts = groups[-2] + groups[-1];
                groups = groups[:-2];
                groups.append([offcuts[0], offcuts[1]]);
                groups.append([offcuts[2], offcuts[3]]);
            elif len(players) % 3 == 2:
                offcuts = groups[-1];
                groups = groups[:-1];
                groups.append([offcuts[0], offcuts[1]]);
        
        # "groups" now contains a number of arrays, each of which contains the
        # same number of players, or any number of arrays of three players each,
        # followed by zero, one or two arrays of two players each.

        group_index = 0;
        for g in groups:
            for i in range(0, len(g)):
                for j in range(i + 1, len(g)):
                    p1 = g[i];
                    p2 = g[j];
                    if (i + j) % 2 == 0:
                        (p1, p2) = (p2, p1);
                    fixture = countdowntourney.Game(round_no, round_seq, table_no, div_index, 'P', p1, p2);
                    fixtures.append(fixture);
                    round_seq += 1;
            if table_size == 3 and len(g) == 2:
                if len(players) % 3 == 1:
                    fixture = None;
                    if group_index == len(groups) - 2:
                        # If this is the first of the two groups of two, add a
                        # fixture pairing the first player of this group with
                        # the second of the next group.
                        nextg = groups[group_index + 1];
                        fixture = countdowntourney.Game(round_no, round_seq, table_no, div_index, 'P', nextg[1], g[0]);
                    elif group_index == len(groups) - 1:
                        # If this is the second of the two groups of two, add a
                        # fixture pairing the first player of this group with the
                        # second of the previous two-person group.
                        prevg = groups[group_index - 1];
                        fixture = countdowntourney.Game(round_no, round_seq, table_no, div_index, 'P', prevg[1], g[0]);
                    if fixture:
                        fixtures.append(fixture);
                        round_seq += 1;
                elif len(players) % 3 == 2:
                    # One table of two... get these two players to play each other
                    # a second time.
                    fixture = countdowntourney.Game(round_no, round_seq, table_no, div_index, 'P', g[1], g[0]);
                    fixtures.append(fixture);
                    round_seq += 1;
            table_no += 1;
            group_index += 1;

    d = dict();
    d["fixtures"] = fixtures;
    d["rounds"] = [
            {
                "round" : round_no,
                "name" : "Round %d" % round_no,
                "type" : "P"
            }
    ];

    return d;

def save_form_on_submit():
    return False
