#!/usr/bin/python

import random;
import countdowntourney;
import htmlform;
import cgi;
import urllib;

name = "Manual Fixture Generator"
description = "Player groupings are specified manually by the tournament director."

def lookup_player(players, name):
    for p in players:
        if p.get_name() == name:
            return p;
    raise countdowntourney.PlayerDoesNotExistException("Player %s does not exist! I haven't a clue who they are." % name);

def get_user_form(tourney, settings):
    players = sorted(tourney.get_players(), key=lambda x : x.get_name());
    table_size = None
    if settings.get("tablesize", None) is not None:
        try:
            table_size = int(settings.get("tablesize"))
        except ValueError:
            table_size = None
    if table_size is None:
        elements = []
        choices = []
        for size in (2,3,4,5):
            if len(players) % size == 0:
                choices.append(htmlform.HTMLFormChoice(str(size), str(size), False))
        if len(players) >= 8:
            choices.append(htmlform.HTMLFormChoice("-5", "5&3", False))
        elements.append(htmlform.HTMLFormRadioButton("tablesize", "Players per table", choices))
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Next"))
        elements.append(htmlform.HTMLFragment("</p>"))
        return htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py", elements)
    
    if table_size > 0 and len(players) % table_size != 0:
        raise countdowntourney.FixtureGeneratorException("Table size of %d is not allowed, as the number of players (%d) is not a multiple of it." % (table_size, len(players)))

    if table_size == -5 and len(players) < 8:
        raise countdowntourney.FixtureGeneratorException("Can't use table sizes of five and three - you need at least 8 players and you have %d" % (len(players)))

    if table_size not in (2,3,4,5,-5):
        raise countdowntourney.FixtureGeneratorException("Invalid table size: %d" % table_size)

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

    # Slot numbers which don't contain a player
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
    elements.append(htmlform.HTMLFragment("<table class=\"seltable\">\n"));
    prev_table_no = None;
    unselected_names = map(lambda x : x.get_name(), players);

    if table_size > 0:
        table_sizes = [table_size for i in range(0, len(players) / table_size)]
    else:
        table_sizes = countdowntourney.get_5_3_table_sizes(len(players))

    table_no = 1
    for table_size in table_sizes:
        elements.append(htmlform.HTMLFragment("<tr>\n"))
        elements.append(htmlform.HTMLFragment("<td>Table %d</td>\n" % table_no));
        for i in range(table_size):
            p = set_players[player_index]
            td_style = "";
            if player_index in duplicate_slots:
                td_style = "class=\"duplicateplayer\"";
            elif player_index in empty_slots:
                td_style = "class=\"emptyslot\"";
            elements.append(htmlform.HTMLFragment("<td %s>" % td_style));

            # Make a drop down list with every player in it
            player_option_list = [];
            player_option_list.append(htmlform.HTMLFormDropDownOption("", " -- select --"));
            selected_name = "";
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
            player_index += 1
        table_no += 1
        elements.append(htmlform.HTMLFragment("</tr>\n"))

    elements.append(htmlform.HTMLFragment("</table>\n"));
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

    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s&tablesize=%d" % (urllib.quote_plus(tourney.name), table_size), elements);
    return form;

def check_ready(tourney):
    return (True, None)

def generate(tourney, settings):
    table_size = settings.get("tablesize", None)
    players = tourney.get_players();

    if table_size is None:
        raise countdowntourney.FixtureGeneratorException("No table size specified")
    else:
        try:
            table_size = int(table_size)
        except ValueError:
            raise countdowntourney.FixtureGeneratorException("Invalid table size %s" % table_size)

    if table_size not in (2,3,4,5,-5):
        raise countdowntourney.FixtureGeneratorException("Invalid table size: %d" % table_size)
    
    if table_size > 0:
        if len(players) % table_size != 0:
            raise countdowntourney.FixtureGeneratorException("Number of players (%d) is not a multiple of the table size (%d)" % (len(players), table_size))
        table_sizes = [ table_size for i in range(0, len(players) / table_size) ]
    else:
        if len(players) < 8:
            raise countdowntourney.FixtureGeneratorException("Can't use a 5&3 configuration if there are fewer than 8 players, and there are %d" % (len(players)))
        table_sizes = countdowntourney.get_5_3_table_sizes(len(players))

    (ready, excuse) = check_ready(tourney);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    groups = [];
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

    player_index = 0
    groups = []
    for size in table_sizes:
        group = []
        for i in range(size):
            group.append(selected_players[player_index])
            player_index += 1
        groups.append(group)
    
    latest_round_no = tourney.get_latest_round_no('P')
    if latest_round_no is None:
        round_no = 1
    else:
        round_no = latest_round_no + 1

    fixtures = countdowntourney.make_fixtures_from_groups(groups, round_no, table_size == -5)

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
