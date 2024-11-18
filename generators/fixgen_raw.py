#!/usr/bin/python3

import re

import countdowntourney
import htmlform
import htmlcommon
import fixgen_manual

name = "Raw"
description = "You have full control over how many matches are in the round and who plays whom. There are no table groups, and there is no requirement that all players play. Use this generator if you want a knockout stage or one-off game."

special_round_names = {
        "QF" : "Quarter-finals",
        "SF" : "Semi-finals",
        "3P" : "Third-place playoff",
        "F" : "Final"
}

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

def get_user_form(tourney, settings, div_rounds):
    num_divisions = tourney.get_num_divisions()
    div_num_games = dict()
    div_game_types = dict()

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

    # When we pass these settings to fixgen_manual, we don't want it asking
    # awkward questions about the number of players in a group when we're
    # fixing at it two, so tell it that's already been submitted.
    settings["tablesizesubmit"] = "1"

    for div_index in div_rounds:
        num_games_name = "d%d_num_groups" % (div_index)
        game_type_name = "d%d_game_type" % (div_index)

        # For fully-manual, number of players per group is always 2,
        # we're allowed to put a player on more than one table, and there is
        # no requirement that all players play.
        settings["d%d_groupsize" % (div_index)] = "2"
        settings["d%d_allow_player_repetition" % (div_index)] = "1"
        settings["d%d_allow_unselected_players" % (div_index)] = "1"

        # Also we want fixgen_manual to show the standings table for each
        # division.
        settings["d%d_show_standings" % (div_index)] = "1"

        if settings.get(num_games_name, None) is not None:
            try:
                div_num_games[div_index] = int(settings.get(num_games_name))
                if div_num_games[div_index] < 0:
                    div_num_games[div_index] = 0
            except ValueError:
                div_num_games[div_index] = 0
        else:
            div_num_games[div_index] = 0

        if settings.get(game_type_name, None) is not None:
            try:
                div_game_types[div_index] = settings.get(game_type_name)
                if div_game_types[div_index] in special_round_names:
                    settings["d%d_round_name" % (div_index)] = special_round_names[div_game_types[div_index]]
            except ValueError:
                div_game_types[div_index] = None

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h2>%s</h2>" % (htmlcommon.escape(tourney.get_division_name(div_index)))))

        elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        num_games_element = htmlform.HTMLFormNumberInput("Number of games to create", num_games_name, 1, other_attrs={"min" : 1})
        elements.append(num_games_element)
        elements.append(htmlform.HTMLFragment("</div>"))

        elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        elements.append(htmlform.HTMLFragment("Create games of this type: "))

        game_type_options = [ htmlform.HTMLFormDropDownOption(x["code"], x["name"] + " (" + x["code"] + ")") for x in countdowntourney.get_game_types() ]
        type_element = htmlform.HTMLFormDropDownBox("d%d_game_type" % (div_index), game_type_options)

        current_setting = settings.get("d%d_game_type" % (div_index))
        if current_setting:
            type_element.set_value(current_setting)
        elements.append(type_element)
        elements.append(htmlform.HTMLFragment("</div>"))

    num_games_total = sum( [ div_num_games[x] for x in div_num_games ] )

    if num_games_total == 0 or not(settings.get("numgamessubmit", "")):
        elements.append(htmlform.HTMLFragment("<div class=\"fixgenoption\">"))
        elements.append(htmlform.HTMLFormSubmitButton("submit", "Continue"))
        elements.append(htmlform.HTMLFragment("</div>"))
        return htmlform.HTMLForm("POST", None, elements)
    else:
        return fixgen_manual.get_user_form(tourney, settings, div_rounds)

def check_ready(tourney, div_rounds):
    for div in div_rounds:
        round_no = div_rounds[div]
        existing_games = tourney.get_games(round_no=round_no, division=div)
        if existing_games:
            return (False, "%s: round %d already has %d games in it." % (tourney.get_division_name(div), round_no, len(existing_games)))
    return (True, None)

def generate(tourney, settings, div_rounds):
    return fixgen_manual.generate(tourney, settings, div_rounds, check_ready)

def save_form_on_submit():
    return True
