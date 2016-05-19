#!/usr/bin/python

import countdowntourney
import htmlform
import cgi

def check_ready_existing_games_and_table_size(tourney, div_rounds):
    num_divisions = tourney.get_num_divisions()
    for div_index in div_rounds:
        round_no = div_rounds[div_index]
        players = filter(lambda x : x.get_division() == div_index, tourney.get_active_players());

        existing_games = tourney.get_games(round_no=round_no, division=div_index)
        if existing_games:
            return (False, "%s: there are already %d games generated for round %d in this division." % (tourney.get_division_name(div_index), len(existing_games), round_no))

        for size in (2,3,4,5):
            if len(players) % size == 0:
                break
        else:
            if len(players) < 8:
                return (False, "%s: Number of players (%d) not compatible with any supported table configuration" % (tourney.get_division_name(div_index), len(players)))
    return (True, None)

def get_user_form_div_table_size(tourney, settings, div_rounds):
    prev_settings = settings.get_previous_settings()
    for key in prev_settings:
        if key not in settings and key != "submit":
            settings[key] = prev_settings[key]

    elements = []
    valid_table_sizes_submitted = []
    for div_index in div_rounds:
        valid_table_size_submitted = False
        players = filter(lambda x : x.get_division() == div_index, tourney.get_active_players());
        table_size = None
        if settings.get("d%d_groupsize" % (div_index), None) is not None:
            try:
                table_size = int(settings.get("d%d_groupsize" % (div_index)))
            except ValueError:
                table_size = None

        if table_size is not None:
            if table_size == -5 and len(players) >= 8:
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
            elif len(players) < 8:
                table_size = -5
            elif len(players) % 4 == 0:
                table_size = 4

        table_size_choices = []
        for size in (2,3,4,5):
            if len(players) % size == 0:
                table_size_choices.append(htmlform.HTMLFormChoice(str(size), str(size), table_size == size))
        if len(players) >= 8:
            table_size_choices.append(htmlform.HTMLFormChoice("-5", "5&3", table_size == -5))

        elements.append(htmlform.HTMLFragment("<h3>%s (%d players)</h3>" % (cgi.escape(tourney.get_division_name(div_index)), tourney.get_num_active_players(div_index))))
        elements.append(htmlform.HTMLFormRadioButton("d%d_groupsize" % (div_index), "Players per table", table_size_choices))
        valid_table_sizes_submitted.append(valid_table_size_submitted)

    if False not in valid_table_sizes_submitted and "submit" in settings:
        return None

    elements.append(htmlform.HTMLFragment("<p>"))
    elements.append(htmlform.HTMLFormSubmitButton("submit", "Generate Fixtures"));
    elements.append(htmlform.HTMLFragment("</p>"))
    form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py", elements)
    return form;

