#!/usr/bin/python3

import random;
import countdowntourney;
import htmlform;
import cgi;
import urllib.request, urllib.parse, urllib.error;
import re

name = "Fully Manual Fixtures"
description = "Organiser has full control over how many matches are in the round and who plays whom. There are no table groups, and there is no requirement that all players play."

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

def make_past_form_strings(tourney, div_index, players, games, this_round_number):
    standings = tourney.get_standings(div_index)
    name_to_position = {}
    name_to_form = {}
    name_to_results = {}

    # If nobody has played a game yet, use seedings
    found_game = False
    for s in standings:
        if s.played > 0:
            found_game = True
            break
    
    if found_game:
        for s in standings:
            name_to_position[s.name] = "P%d" % (s.position)
    else:
        seedings = sorted(standings, key=lambda x : x.rating, reverse=True)
        # If everyone has the same rating, not including 0, then there are no
        # seedings.
        seen_rating = None
        players_are_rated = False
        for s in seedings:
            if s.rating != 0:
                if seen_rating:
                    if s.rating != seen_rating:
                        players_are_rated = True
                        break

                seen_rating = s.rating

        if players_are_rated:
            seed = 0
            joint = 0
            prev_rating = None
            for s in seedings:
                if prev_rating is not None and s.rating == prev_rating:
                    joint += 1
                else:
                    seed += joint + 1
                    joint = 0
                name_to_position[s.name] = "S%d" % (seed)
                prev_rating = s.rating

    for g in games:
        if g.is_complete() and g.are_players_known() and g.get_round_no() < this_round_number:
            for p in g.get_players():
                score = g.get_player_score(p)
                opp_score = g.get_opponent_score(p)

                score_string = "%d%s-%d%s" % (score,
                        "*" if g.is_tiebreak() and score > opp_score else "",
                        opp_score,
                        "*" if g.is_tiebreak() and opp_score >= score else "")
                
                if score > opp_score:
                    form = "W"
                elif score < opp_score:
                    form = "L"
                else:
                    form = "D"

                name = p.get_name()
                name_to_form[name] = name_to_form.get(name, "") + form
                if name in name_to_results:
                    name_to_results[name] = name_to_results[name] + " " + score_string
                else:
                    name_to_results[name] = score_string

    past_form_strings = {}
    for p in players:
        name = p.get_name()
        form_str_list = []
        for d in (name_to_position, name_to_form, name_to_results):
            if name in d:
                form_str_list.append(d[name])
        past_form_strings[name] = " ".join(form_str_list)

    return past_form_strings


def get_user_form(tourney, settings, div_rounds):
    num_divisions = tourney.get_num_divisions()
    div_num_games = dict()
    div_default_game_types = dict()

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
    elements.append(htmlform.HTMLFormHiddenInput("numgamessubmit", "1"))
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
        num_games_name = "d%d_numgames" % (div_index)
        default_game_type_name = "d%d_defaultgametype" % (div_index)

        if settings.get(num_games_name, None) is not None:
            try:
                div_num_games[div_index] = int(settings.get(num_games_name))
                if div_num_games[div_index] < 0:
                    div_num_games[div_index] = 0
            except ValueError:
                div_num_games[div_index] = 0
        else:
            div_num_games[div_index] = 0

        if settings.get(default_game_type_name, None) is not None:
            try:
                div_default_game_types[div_index] = settings.get(default_game_type_name)
            except ValueError:
                div_default_game_types[div_index] = None

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h3>%s</h3>" % (cgi.escape(tourney.get_division_name(div_index)))))

        elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        num_games_element = htmlform.HTMLFormTextInput("Number of games to create", num_games_name, "")
        elements.append(num_games_element)
        elements.append(htmlform.HTMLFragment("</div>"))

        elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        elements.append(htmlform.HTMLFragment("Create games of this type: "))

        game_type_options = [ htmlform.HTMLFormDropDownOption(x["code"], x["name"] + " (" + x["code"] + ")") for x in countdowntourney.get_game_types() ]
        default_type_element = htmlform.HTMLFormDropDownBox("d%d_defaultgametype" % (div_index), game_type_options)

        current_setting = settings.get("d%d_defaultgametype" % (div_index))
        if current_setting:
            default_type_element.set_value(current_setting)
        elements.append(default_type_element)
        elements.append(htmlform.HTMLFragment("</div>"))

    num_games_total = sum( [ div_num_games[x] for x in div_num_games ] )

    if num_games_total == 0 or not(settings.get("numgamessubmit", "")):
        elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Continue"))
        elements.append(htmlform.HTMLFragment("</div>"))
        return htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s" % (urllib.parse.quote_plus(tourney.name)), elements)
    
    show_already_assigned_players = bool(settings.get("showallplayers"))

    div_set_players = dict()
    div_empty_slots = dict()
    div_invalid_slots = dict()
    div_game_types = dict()
    div_default_game_types = dict()
    div_num_games = dict()

    all_filled = True
    for div_index in div_rounds:
        num_games = int(settings.get("d%d_numgames" % (div_index), "0"))
        div_players = [x for x in players if x.get_division() == div_index];
        set_players = [ None for i in range(0, num_games * 2) ];
        game_types = [ None for i in range(num_games) ]

        if num_games is None:
            num_games = 0

        default_game_type = settings.get("d%d_defaultgametype" % (div_index), "P")

        # Ask the user to fill in N little drop-down boxes, where N is twice
        # the number of games, to decide who's playing.
        for slot_index in range(num_games * 2):
            name = settings.get("d%d_player%d" % (div_index, slot_index));
            if name:
                set_players[slot_index] = lookup_player(div_players, name);
            else:
                set_players[slot_index] = None
    
        for game_index in range(num_games):
            game_types[game_index] = settings.get("d%d_type%d" % (div_index, game_index))
        
        # Slot numbers which don't contain a player
        empty_slots = [];
        slot_index = 0;
        for p in set_players:
            if p is None:
                empty_slots.append(slot_index);
                all_filled = False;
            slot_index += 1;

        invalid_slots = []
        # Make sure no player is playing themselves - if they are, then set
        # all_filled to false because we haven't completed setup, and mark them
        # as invalid slots
        for game_index in range(num_games):
            slot1 = set_players[game_index * 2]
            slot2 = set_players[game_index * 2 + 1]
            if slot1 is not None and slot2 is not None and slot1 == slot2:
                all_filled = False
                invalid_slots.append(game_index * 2)
                invalid_slots.append(game_index * 2 + 1)

        div_set_players[div_index] = set_players
        div_invalid_slots[div_index] = invalid_slots
        div_empty_slots[div_index] = empty_slots
        div_game_types[div_index] = game_types
        div_default_game_types[div_index] = default_game_type
        div_num_games[div_index] = num_games

    if all_filled and settings.get("submitplayers"):
        # All slots are filled, so we can now generate fixtures
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
    elements.append(htmlform.HTMLFragment("<p>Use the drop-down boxes to select who is playing in each game.</p>\n"));
    elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
    elements.append(htmlform.HTMLFormCheckBox("showallplayers", "Show all players in drop-down boxes, even those already assigned a game", show_already_assigned_players))
    elements.append(htmlform.HTMLFragment("</div>"))

    table_no = 1;
    for div_index in div_rounds:
        div_players = [x for x in players if x.get_division() == div_index];
        player_index = 0;
        table_size = 2
        invalid_slots = div_invalid_slots[div_index]
        empty_slots = div_empty_slots[div_index]
        set_players = div_set_players[div_index]
        default_game_type = div_default_game_types[div_index]
        game_types = div_game_types[div_index]
        num_games = div_num_games[div_index]

        div_games = tourney.get_games(division=div_index)
        past_form_strings = make_past_form_strings(tourney, div_index, div_players, div_games, latest_round_no + 1)

        elements.append(htmlform.HTMLFormHiddenInput("d%d_numgames" % (div_index), str(div_num_games[div_index])))
        elements.append(htmlform.HTMLFormHiddenInput("d%d_defaultgametype" % (div_index), str(div_default_game_types[div_index])))

        if num_games == 0:
            continue

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h3>%s</h3>" % (cgi.escape(tourney.get_division_name(div_index)))))
        elements.append(htmlform.HTMLFragment("<p>%d game%s of type %s</p>" % (num_games, "" if num_games == 1 else "s", cgi.escape(default_game_type))))

        #elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        #elements.append(htmlform.HTMLFormCheckBox("d%d_heats" % (div_index), "Count the results of these matches in the standings table", div_count_in_standings[div_index]))
        #elements.append(htmlform.HTMLFragment("</div>"))

        elements.append(htmlform.HTMLFragment("<table class=\"seltable\">\n"));
        prev_table_no = None;
        unselected_names = [x.get_name() for x in div_players];

        for p in set_players:
            if p and p.get_name() in unselected_names:
                unselected_names.remove(p.get_name())

        for game_index in range(num_games):
            elements.append(htmlform.HTMLFragment("<tr>\n"))
            elements.append(htmlform.HTMLFragment("<td>Table %d</td>\n" % table_no));
            for i in range(table_size):
                p = set_players[player_index]
                td_style = "";
                if player_index in invalid_slots:
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
                    past_form = past_form_strings.get(q, "")
                    label = q;
                    if past_form:
                        label += " (" + past_form + ")"

                    opt = htmlform.HTMLFormDropDownOption(q, label)
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

        if invalid_slots:
            elements.append(htmlform.HTMLFragment("<p>You have players playing themselves: these are highlighted in <font color=\"#ff0000\"><strong>red</strong></font>.</p>"));
        if empty_slots:
            elements.append(htmlform.HTMLFragment("<p>Some slots are not yet filled: these are highlighted in <font color=\"#ffaa00\"><strong>orange</strong></font>.</p>"));

        if unselected_names:
            elements.append(htmlform.HTMLFragment("<p>Players not yet assigned a game:</p>\n"));
            elements.append(htmlform.HTMLFragment("<blockquote>\n"));
            for name in unselected_names:
                elements.append(htmlform.HTMLFragment("<li>%s</li>\n" % cgi.escape(name)));
            elements.append(htmlform.HTMLFragment("</blockquote>\n"));

    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s" % (urllib.parse.quote_plus(tourney.name)), elements);
    return form;

def check_ready(tourney, div_rounds):
    for div in div_rounds:
        round_no = div_rounds[div]
        existing_games = tourney.get_games(round_no=round_no, division=div)
        if existing_games:
            return (False, "%s: round %d already has %d games in it." % (tourney.get_division_name(div), round_no, len(existing_games)))
    return (True, None)

def generate(tourney, settings, div_rounds):
    num_divisions = tourney.get_num_divisions()
    table_size = 2

    players = tourney.get_active_players();

    (ready, excuse) = check_ready(tourney, div_rounds);
    if not ready:
        raise countdowntourney.FixtureGeneratorException(excuse);

    fixtures = []
    round_numbers_generated = []
    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        groups = [];
        div_players = [x for x in players if x.get_division() == div_index]
        num_games = int(settings.get("d%d_numgames" % (div_index), "0"))
        default_game_type = settings.get("d%d_defaultgametype" % (div_index))

        if num_games == 0:
            continue

        # Player names should have been specified by a series of drop-down
        # boxes.
        player_names = [];
        for i in range(num_games * 2):
            name = settings.get("d%d_player%d" % (div_index, i));
            if name:
                player_names.append(name);
            else:
                raise countdowntourney.FixtureGeneratorException("%s: Slot %d has no player in it. This is probably a bug, as the form should have made you fill in all the boxes." % (tourney.get_division_name(div_index), i));

        selected_players = [lookup_player(div_players, x) for x in player_names];

        groups = []
        for game_index in range(num_games):
            groups.append([ selected_players[game_index * 2], selected_players[game_index * 2 + 1] ])

        if round_no not in round_numbers_generated:
            round_numbers_generated.append(round_no)

        fixtures += tourney.make_fixtures_from_groups(groups, fixtures, round_no, False, division=div_index, game_type=default_game_type)

    d = dict();
    d["fixtures"] = fixtures;
    d["rounds"] = [
            {
                "round" : round_no
            } for round_no in round_numbers_generated
    ];

    return d;

def save_form_on_submit():
    return True
