#!/usr/bin/python3

import random;
import countdowntourney;
import htmlform;
import cgi;
import urllib.request, urllib.parse, urllib.error;
import re
import fixgen

name = "Manual Pairings/Groups"
description = "Player groups are specified manually. A fixture is generated between each pair in a group. Use this fixture generator if you're generating fixtures yourself, for example by picking names out of a hat."

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def lookup_player(players, name):
    for p in players:
        if p.get_name() == name:
            return p;
    return None

def get_user_form(tourney, settings, div_rounds):
    num_divisions = tourney.get_num_divisions()
    div_table_sizes = dict()
    players = sorted(tourney.get_active_players(), key=lambda x : x.get_name());

    latest_round_no = tourney.get_latest_round_no()
    if latest_round_no is None:
        latest_round_no = 0

    prev_settings = settings.get_previous_settings()
    for key in prev_settings:
        if key not in settings and re.match("^d[0-9]*_groupsize$", key):
            settings[key] = prev_settings[key]
    if settings.get("submitrestore", None):
        for key in prev_settings:
            if key not in ["submit", "submitrestore", "submitplayers"]:
                settings[key] = prev_settings[key]

    elements = []
    elements.append(htmlform.HTMLFormHiddenInput("tablesizesubmit", "1"))
    elements.append(htmlform.HTMLFormHiddenInput("roundno", str(latest_round_no + 1)))

    # If there's a previously-saved form for this round, offer to load it
    prev_settings = settings.get_previous_settings()
    round_no = int_or_none(prev_settings.get("roundno", None))
    if round_no is not None and round_no == latest_round_no + 1:
        elements.append(htmlform.HTMLFragment("<div class=\"infoboxcontainer\">"))
        elements.append(htmlform.HTMLFragment("<div class=\"infoboximage\">"))
        elements.append(htmlform.HTMLFragment("<img src=\"/images/info.png\" alt=\"Info\" />"))
        elements.append(htmlform.HTMLFragment("</div>"))
        elements.append(htmlform.HTMLFragment("<div class=\"infoboxmessagecontainer\">"))
        elements.append(htmlform.HTMLFragment("<div class=\"infoboxmessage\">"))
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFragment("There is an incomplete fixtures form saved. Do you want to carry on from where you left off?"))
        elements.append(htmlform.HTMLFragment("</p>"))
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFormSubmitButton("submitrestore", "Restore previously-saved form"))
        elements.append(htmlform.HTMLFragment("</p>"))
        elements.append(htmlform.HTMLFragment("</div></div></div>"))

    for div_index in div_rounds:
        div_players = [x for x in players if x.get_division() == div_index]
        table_size = None
        table_size_name = "d%d_groupsize" % (div_index)
        if settings.get(table_size_name, None) is not None:
            try:
                div_table_sizes[div_index] = int(settings.get(table_size_name))
            except ValueError:
                div_table_sizes[div_index] = None
        else:
            div_table_sizes[div_index] = None
        choices = []
        for size in (2,3,4,5):
            if len(div_players) % size == 0:
                choices.append(htmlform.HTMLFormChoice(str(size), str(size), size == div_table_sizes[div_index]))
        if len(div_players) >= 8:
            choices.append(htmlform.HTMLFormChoice("-5", "5&3", div_table_sizes[div_index] == -5))
        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h2>%s</h2>" % (cgi.escape(tourney.get_division_name(div_index)))))
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFormRadioButton(table_size_name, "Players per table", choices))
        elements.append(htmlform.HTMLFragment("</p>"))

    all_table_sizes_given = True
    for div in div_table_sizes:
        if div_table_sizes.get(div) is None:
            all_table_sizes_given = False

    if not all_table_sizes_given or not(settings.get("tablesizesubmit", "")):
        elements.append(htmlform.HTMLFragment("<p>"))
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Submit table sizes and select players"))
        elements.append(htmlform.HTMLFragment("</p>"))
        return htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s" % (urllib.parse.quote_plus(tourney.name)), elements)
    
    show_already_assigned_players = bool(settings.get("showallplayers"))
    for div_index in div_rounds:
        div_players = [x for x in players if x.get_division() == div_index];
        table_size = div_table_sizes[div_index]
        if table_size > 0 and len(div_players) % table_size != 0:
            raise countdowntourney.FixtureGeneratorException("%s: table size of %d is not allowed, as the number of players (%d) is not a multiple of it." % (tourney.get_division_name(div_index), table_size, len(div_players)))

        if table_size == -5 and len(div_players) < 8:
            raise countdowntourney.FixtureGeneratorException("%s: can't use table sizes of five and three - you need at least 8 players and you have %d" % (tourney.get_division_name(div_index), len(div_players)))

        if table_size not in (2,3,4,5,-5):
            raise countdowntourney.FixtureGeneratorException("%s: invalid table size: %d" % (tourney.get_division_name(div_index), table_size))

    div_set_players = dict()
    div_duplicate_slots = dict()
    div_empty_slots = dict()
    div_count_in_standings = dict()
    all_filled = True
    for div_index in div_rounds:
        div_players = [x for x in players if x.get_division() == div_index];
        set_players = [ None for i in range(0, len(div_players)) ];

        if not settings.get("submitplayers"):
            count_in_standings = True
        else:
            count_in_standings = settings.get("d%d_heats" % (div_index))
            if count_in_standings is None:
                count_in_standings = False
            else:
                count_in_standings = True

        # Ask the user to fill in N little drop-down boxes, where N is the
        # number of players, to decide who's going on what table.
        for player_index in range(0, len(div_players)):
            name = settings.get("d%d_player%d" % (div_index, player_index));
            if name:
                set_players[player_index] = lookup_player(div_players, name);
            else:
                set_players[player_index] = None
    
        # Slot numbers which contain a player already contained in another slot
        duplicate_slots = [];

        # Slot numbers which don't contain a player
        empty_slots = [];
        player_index = 0;
        for p in set_players:
            if p is None:
                empty_slots.append(player_index);
                all_filled = False;
            else:
                count = 0;
                for q in set_players:
                    if q is not None and q.get_name() == p.get_name():
                        count += 1;
                if count > 1:
                    duplicate_slots.append(player_index);
                    all_filled = False;
            player_index += 1;

        div_set_players[div_index] = set_players
        div_duplicate_slots[div_index] = duplicate_slots
        div_empty_slots[div_index] = empty_slots
        div_count_in_standings[div_index] = count_in_standings

    if all_filled and settings.get("submitplayers"):
        return None

    elements = [];
    elements.append(htmlform.HTMLFormHiddenInput("roundno", str(latest_round_no + 1)))
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
    elements.append(htmlform.HTMLFragment("""<script>
function set_unsaved_data_warning() {
    if (window.onbeforeunload == null) {
        window.onbeforeunload = function() {
            return "You have modified entries on this page and not submitted them. If you navigate away from the page, these changes will be lost.";
        };
    }
}

function unset_unsaved_data_warning() {
    window.onbeforeunload = null;
}
</script>
"""));
    elements.append(htmlform.HTMLFragment("<p>Use the drop-down boxes to select which players are on each table.</p>\n"));
    elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
    elements.append(htmlform.HTMLFormCheckBox("showallplayers", "Show all players in drop-down boxes, even those already assigned a table", show_already_assigned_players))
    elements.append(htmlform.HTMLFragment("</div>"))

    table_no = 1;
    for div_index in div_rounds:
        div_players = [x for x in players if x.get_division() == div_index];
        player_index = 0;
        table_size = div_table_sizes[div_index]
        duplicate_slots = div_duplicate_slots[div_index]
        empty_slots = div_empty_slots[div_index]
        set_players = div_set_players[div_index]
        count_in_standings = div_count_in_standings[div_index]

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h2>%s</h2>" % (cgi.escape(tourney.get_division_name(div_index)))))

        elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        elements.append(htmlform.HTMLFormCheckBox("d%d_heats" % (div_index), "Count the results of these matches in the standings table", div_count_in_standings[div_index]))
        elements.append(htmlform.HTMLFragment("</div>"))

        elements.append(htmlform.HTMLFragment("<table class=\"seltable\">\n"));
        prev_table_no = None;
        unselected_names = [x.get_name() for x in div_players];

        if table_size > 0:
            table_sizes = [table_size for i in range(0, len(div_players) // table_size)]
        else:
            table_sizes = countdowntourney.get_5_3_table_sizes(len(div_players))

        for p in set_players:
            if p and p.get_name() in unselected_names:
                unselected_names.remove(p.get_name())

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

                # Make a drop down list with every unassigned player in it
                player_option_list = [];
                player_option_list.append(htmlform.HTMLFormDropDownOption("", " -- select --"));
                selected_name = "";
                
                if show_already_assigned_players:
                    name_list = [ x.get_name() for x in div_players ]
                else:
                    if p:
                        name_list = sorted(unselected_names + [p.get_name()])
                    else:
                        name_list = unselected_names

                for q in name_list:
                    opt = htmlform.HTMLFormDropDownOption(q, q)
                    if p is not None and q == p.get_name():
                        selected_name = p.get_name()
                    player_option_list.append(opt)

                # Select the appropriate player
                sel = htmlform.HTMLFormDropDownBox("d%d_player%d" % (div_index, player_index), player_option_list, other_attrs={"onchange": "set_unsaved_data_warning();"});
                sel.set_value(selected_name);

                elements.append(sel);
                elements.append(htmlform.HTMLFragment("</td>"));
                player_index += 1
            table_no += 1
            elements.append(htmlform.HTMLFragment("</tr>\n"))

        elements.append(htmlform.HTMLFragment("</table>\n"));
        elements.append(htmlform.HTMLFragment("<p>\n"))
        elements.append(htmlform.HTMLFormHiddenInput("submitplayers", "1"))
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Submit", other_attrs={ "onclick": "unset_unsaved_data_warning();" }));
        elements.append(htmlform.HTMLFragment("</p>\n"))

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

        elements.append(htmlform.HTMLFormHiddenInput("d%d_groupsize" % (div_index), str(div_table_sizes[div_index])))

    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s" % (urllib.parse.quote_plus(tourney.name)), elements);
    return form;

def check_ready(tourney, div_rounds):
    for div in div_rounds:
        round_no = div_rounds[div]
        existing_games = tourney.get_games(round_no=round_no, game_type="P", division=div)
        if existing_games:
            return (False, "%s: round %d already has %d games in it." % (tourney.get_division_name(div), round_no, len(existing_games)))
    return (True, None)

def generate(tourney, settings, div_rounds):
    num_divisions = tourney.get_num_divisions()
    div_table_sizes = dict()

    players = tourney.get_active_players();
    for div_index in div_rounds:
        table_size = settings.get("d%d_groupsize" % (div_index), None)
        div_players = [x for x in players if x.get_division() == div_index]

        if table_size is None:
            raise countdowntourney.FixtureGeneratorException("%s: No table size specified" % tourney.get_division_name(div_index))
        else:
            try:
                table_size = int(table_size)
            except ValueError:
                raise countdowntourney.FixtureGeneratorException("%s: Invalid table size %s" % (tourney.get_division_name(div_index), table_size))

        if table_size not in (2,3,4,5,-5):
            raise countdowntourney.FixtureGeneratorException("%s: Invalid table size: %d" % (tourney.get_division_name(div_index), table_size))
        
        if table_size > 0:
            if len(div_players) % table_size != 0:
                raise countdowntourney.FixtureGeneratorException("%s: Number of players (%d) is not a multiple of the table size (%d)" % (tourney.get_division_name(div_index), len(div_players), table_size))
            table_sizes = [ table_size for i in range(0, len(div_players) // table_size) ]
        else:
            if len(div_players) < 8:
                raise countdowntourney.FixtureGeneratorException("%s: Can't use a 5&3 configuration if there are fewer than 8 players, and there are %d" % (tourney.get_division_name(div_index), len(div_players)))
            table_sizes = countdowntourney.get_5_3_table_sizes(len(div_players))
        div_table_sizes[div_index] = table_sizes

    (ready, excuse) = check_ready(tourney, div_rounds);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    #latest_round_no = tourney.get_latest_round_no('P')
    #if latest_round_no is None:
    #    round_no = 1
    #else:
    #    round_no = latest_round_no + 1

    generated_groups = fixgen.GeneratedGroups()
    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        groups = [];
        table_sizes = div_table_sizes[div_index]
        div_players = [x for x in players if x.get_division() == div_index]
        if settings.get("d%d_heats" % (div_index)):
            game_type = "P"
        else:
            game_type = "N"

        # Player names should have been specified by a series of drop-down
        # boxes.
        player_names = [];
        for i in range(0, len(div_players)):
            name = settings.get("d%d_player%d" % (div_index, i));
            if name:
                player_names.append(name);
            else:
                raise countdowntourney.FixtureGeneratorException("%s: Player %d not specified. This is probably a bug, as the form should have made you fill in all the boxes." % (tourney.get_division_name(div_index), i));

        selected_players = [lookup_player(div_players, x) for x in player_names];

        player_index = 0
        groups = []
        for size in table_sizes:
            group = []
            for i in range(size):
                group.append(selected_players[player_index])
                player_index += 1
            groups.append(group)

        for g in groups:
            generated_groups.add_group(round_no, div_index, g)
        generated_groups.set_repeat_threes(round_no, div_index, table_size == -5)
        generated_groups.set_game_type(round_no, div_index, game_type)

    return generated_groups

def save_form_on_submit():
    return True
