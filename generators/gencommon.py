#!/usr/bin/python3

import countdowntourney
import htmlform
import cgicommon
import urllib

def check_ready_existing_games_and_table_size(tourney, div_rounds, include_5and3=True):
    num_divisions = tourney.get_num_divisions()
    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        players = [x for x in tourney.get_active_players() if x.get_division() == div_index];

        existing_games = tourney.get_games(round_no=round_no, division=div_index)
        if existing_games:
            return (False, "%s: there are already %d games generated for round %d in this division." % (tourney.get_division_name(div_index), len(existing_games), round_no))

        for size in (2,3,4,5):
            if len(players) % size == 0:
                break
        else:
            if len(players) < 8 or not include_5and3:
                return (False, "%s: Number of players (%d) is not compatible with any supported table size." % (tourney.get_division_name(div_index), len(players)))
    return (True, None)

def get_user_form_div_table_size(tourney, settings, div_rounds, include_5and3=True, additional_elements=[]):
    prev_settings = settings.get_previous_settings()
    for key in prev_settings:
        if key not in settings and key != "submit":
            settings[key] = prev_settings[key]

    elements = []
    valid_table_sizes_submitted = []
    num_divisions = tourney.get_num_divisions()
    for div_index in div_rounds:
        valid_table_size_submitted = False
        players = [x for x in tourney.get_active_players() if x.get_division() == div_index];
        table_size = None
        if settings.get("d%d_groupsize" % (div_index), None) is not None:
            try:
                table_size = int(settings.get("d%d_groupsize" % (div_index)))
            except ValueError:
                table_size = None

        if table_size is not None:
            if table_size == -5 and len(players) >= 8 and include_5and3:
                valid_table_size_submitted = True
            elif len(players) % table_size == 0:
                valid_table_size_submitted = True

        if table_size is None:
            if len(players) % 3 == 0:
                table_size = 3
            elif len(players) % 2 == 0:
                table_size = 2
            elif len(players) % 5 == 0:
                table_size = 5
            elif len(players) >= 8 and include_5and3:
                table_size = -5
            elif len(players) % 4 == 0:
                table_size = 4

        table_size_choices = []
        for size in (2,3,4,5):
            table_size_choices.append(htmlform.HTMLFormChoice(str(size), str(size), table_size == size, len(players) % size == 0))
        if len(players) >= 8 and include_5and3:
            table_size_choices.append(htmlform.HTMLFormChoice("-5", "5&3", table_size == -5))

        if num_divisions > 1:
            elements.append(htmlform.HTMLFragment("<h2>%s</h2>" % (cgicommon.escape(tourney.get_division_name(div_index)))))
        num_active_players = tourney.get_num_active_players(div_index)
        elements.append(htmlform.HTMLFragment("<p>This %s has <strong>%d active players</strong>.</p>" % ("division" if num_divisions > 1 else "tournament", num_active_players)))
        if num_active_players % 2 != 0 and num_active_players % 3 != 0:
            elements.append(htmlform.HTMLWarningBox("unusualplayercountwarningbox", "The number of active players is not a multiple of 2 or 3. Do you want to add one or more Prune players on the <a href=\"/cgi-bin/player.py?tourney=%s\">Player Setup</a> page?</p>" % (
                urllib.parse.quote_plus(tourney.get_name())
            )))

        elements.append(htmlform.HTMLFormRadioButton("d%d_groupsize" % (div_index),
            "How many players per table? This must exactly divide the number of active players in %s." % ("this division" if num_divisions > 1 else "the tournament"),
            table_size_choices))
        valid_table_sizes_submitted.append(valid_table_size_submitted)

    if False not in valid_table_sizes_submitted and "submit" in settings:
        return None

    for element in additional_elements:
        elements.append(element)

    elements.append(htmlform.HTMLFragment("<p>"))
    elements.append(htmlform.HTMLFormSubmitButton("submit", "Generate Fixtures", other_attrs={"class" : "bigbutton"}));
    elements.append(htmlform.HTMLFragment("</p>"))
    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py", elements)
    return form;


def get_table_sizes(num_players, table_size):
    if table_size == -5:
        sizes = []
        if num_players < 8:
            raise countdowntourney.FixtureGeneratorException("Number of players (%d) not compatible with selected table configuration (5&3)." % (num_players))
        while num_players > 0 and num_players % 5 != 0:
            sizes.append(3)
            num_players -= 3
        sizes += [ 5 for x in range(num_players // 5) ]
    else:
        if num_players % table_size != 0:
            raise countdowntourney.FixtureGeneratorException("Number of players (%d) not compatible with selected table configuration (%d)." % (num_players, table_size))
        sizes = [ table_size for x in range(num_players // table_size) ]
    return sizes

