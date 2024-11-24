#!/usr/bin/python3

import importlib
import json

import htmlcommon
import generators
import countdowntourney
import htmlform

import cttable

# When we load this module for the first time, also load all the fixture
# generation modules we have.

fixgens_r1 = [ "fixgen_manual", "fixgen_random", "fixgen_random_seeded", "fixgen_round_robin" ]
fixgens_not_r1 = [ "fixgen_swiss", "fixgen_random", "fixgen_final" ]

fixgen_module_list = generators.get_fixture_generator_list()
fixgen_modules = {}
for generator_name in fixgen_module_list:
    fixgen_modules[generator_name] = importlib.import_module(generator_name)

def int_or_none(s):
    try:
        value = int(s)
        return value
    except:
        return None

# Class representing the settings passed to a fixture generator. It emulates
# a dictionary. The settings that were passed to the generator the last time
# it generated something for this tourney are also stored in the object and
# individual name-value pairs can be loaded from that into the object's main
# dictionary by the fixture generator.
class FixtureGeneratorSettings(object):
    def __init__(self, default_settings=None):
        self.default_settings = dict()
        if default_settings:
            for k in default_settings:
                if k[0] != '_':
                    self.default_settings[k] = default_settings[k]
        self.settings = dict()

    def __len__(self):
        return len(self.settings)

    def __getitem__(self, key):
        return self.settings[key]

    def __setitem__(self, key, value):
        self.settings[key] = value

    def __delitem__(self, key):
        del self.settings[key]

    def __iter__(self):
        return self.settings.__iter__()

    def __contains__(self, key):
        return (key in self.settings)

    def get(self, key, default_value=None):
        return self.settings.get(key, default_value)

    def load_from_previous(self, key):
        if key in self.default_settings:
            self.settings[key] = self.default_settings[key]

    def get_previous(self, key, default_value=None):
        return self.default_settings.get(key, default_value)

    def get_previous_settings(self):
        return self.default_settings


def show_fixtures_to_accept(response, tourney, generator_name, fixtures, rounds, fixgen_settings):
    tourney_name = tourney.get_name()
    response.writeln("<form method=\"POST\">");
    response.writeln("<div class=\"fixtureacceptbox\">")
    response.writeln("<p>I've generated the following fixtures. You must click <em>Accept Fixtures</em> below if you want to use them.</p>");
    response.writeln("<input type=\"submit\" name=\"accept\" class=\"bigbutton\" value=\"&#x2705; Accept Fixtures\" />");
    response.writeln("<a href=\"/atropine/%s/fixturegen\" class=\"fixturecancellink\">&#x274c; Discard and return to fixture generator menu</a>" % (
        htmlcommon.escape(tourney_name)
    ))
    response.writeln("</div>")
    num_divisions = tourney.get_num_divisions()
    show_wins_and_played = False
    for r in rounds:
        round_no = r.get_round_no()
        response.writeln("<h2>%s</h2>" % htmlcommon.escape(r.get_round_name()))

        for div_index in range(num_divisions):
            round_fixtures = [x for x in fixtures if x.round_no == round_no and x.division == div_index];
            if len(round_fixtures) == 0:
                continue

            standings = tourney.get_standings(division=div_index)
            standings_dict = {}
            for s in standings:
                standings_dict[s.name] = s
            form_dict = tourney.get_player_win_loss_strings(division=div_index)

            if num_divisions > 1:
                response.writeln("<h3>%s</h3>" % (htmlcommon.escape(tourney.get_division_name(div_index))))
            response.writeln("<table class=\"fixturetable\">");
            response.writeln("<tr><th>Table</th><th>Type</th><th colspan=\"4\">Player 1</th><th></th><th colspan=\"4\">Player 2</th></tr>");

            fixnum = 0;
            last_table_no = None;
            for f in round_fixtures:
                if last_table_no is None or last_table_no != f.table_no:
                    num_games_on_table = len([x for x in round_fixtures if x.table_no == f.table_no]);
                    first_game_on_table = True;
                    response.writeln("<tr class=\"firstgameintable\">");
                else:
                    first_game_on_table = False;
                    response.writeln("<tr>");

                if first_game_on_table:
                    response.writeln("<td class=\"tableno\" rowspan=\"%d\"><div class=\"tablebadge\">%d</div></td>" % (num_games_on_table, f.table_no));

                response.writeln("<td class=\"gametype\">%s</td>" % htmlcommon.escape(f.game_type));
                player_td_html = []
                game_standings_info_td_html = [] # will be two lists of column contents, one for each player
                for player in [f.p1, f.p2]:
                    name = player.name
                    standings_row = standings_dict.get(name, None)
                    if player.is_auto_prune():
                        player_td_html.append(htmlcommon.player_to_non_link(player, emboldenise=True))
                        game_standings_info_td_html.append(["", "", ""])
                    elif standings_row is None:
                        player_td_html.append(htmlcommon.player_to_link(player, tourney_name, emboldenise=True, disable_tab_order=False, open_in_new_window=True) + " ?")
                        game_standings_info_td_html.append(["", "", ""])
                    else:
                        if show_wins_and_played:
                            # Display win count as e.g. "3" or "2½"
                            w = 2 * standings_row.wins + standings_row.draws
                            if w % 2 == 1:
                                wins_str = "%d&frac12;" % (w // 2)
                            else:
                                wins_str = "%d" % (w // 2)
                            win_loss_record = "%s/%d" % (wins_str, standings_row.played)
                        else:
                            # Display wins-losses[-draws]
                            win_loss_record = "%d-%d" % (standings_row.wins, standings_row.played - standings_row.wins - standings_row.draws)
                            if standings_row.draws:
                                win_loss_record += "-%d" % (standings_row.draws)
                        player_td_html.append(htmlcommon.player_to_link(player, tourney_name, emboldenise=True, disable_tab_order=False, open_in_new_window=True))
                        game_standings_info_td_html.append(
                                [
                                    htmlcommon.ordinal_number(standings_row.position),
                                    htmlcommon.win_loss_string_to_html(form_dict.get(name, "")),
                                    win_loss_record
                                ]
                        )

                for html in game_standings_info_td_html[0]:
                    response.writeln("<td class=\"gamestandingsinfo gamestandingsinfo1\">%s</td>" % (html))
                response.writeln("<td class=\"gameplayer1\">%s</td>" % (player_td_html[0]))
                response.writeln("<td class=\"gamescore\">v</td>")
                response.writeln("<td class=\"gameplayer2\">%s</td>" % (player_td_html[1]))
                for html in game_standings_info_td_html[1]:
                    response.writeln("<td class=\"gamestandingsinfo gamestandingsinfo2\">%s</td>" % (html))
                num_repeats = tourney.count_games_between(f.p1, f.p2)
                if num_repeats:
                    response.writeln("<td class=\"gamerepeats\">%s repeat</td>" % (htmlcommon.ordinal_number(num_repeats)))
                else:
                    response.writeln("<td class=\"gameremarks\"></td>")
                response.writeln("</tr>");
                fixnum += 1;
                last_table_no = f.table_no;

            response.writeln("</table>");
    response.writeln("<input type=\"hidden\" name=\"generator\" value=\"%s\" />" % htmlcommon.escape(generator_name, True));

    # Remember all the _div* settings, or check_ready might
    # object when we do try to submit the fixtures
    for name in fixgen_settings:
        if name[0:4] == "_div":
            response.writeln("<input type=\"hidden\" name=\"%s\" value=\"%s\" />" % (htmlcommon.escape(name, True), htmlcommon.escape(fixgen_settings[name], True)))

    fixture_plan = {
            "fixtures" : [
                x.make_dict() for x in fixtures
            ],
            "rounds" : [
                {
                    "round" : x.get_round_no(),
                    "name" : x.get_round_name()
                } for x in rounds
            ]
    }
    json_fixture_plan = json.dumps(fixture_plan);
    response.writeln("<input type=\"hidden\" name=\"jsonfixtureplan\" value=\"%s\" />" % htmlcommon.escape(json_fixture_plan, True));
    response.writeln("<div class=\"fixtureacceptbox\">")
    response.writeln("<input type=\"submit\" name=\"accept\" class=\"bigbutton\" value=\"&#x2705; Accept Fixtures\" />");
    response.writeln("<a href=\"/atropine/%s/fixturegen\" class=\"fixturecancellink\">&#x274c; Discard and return to fixture generator menu</a>" % (
        htmlcommon.escape(tourney_name)
    ))
    response.writeln("</div>")
    response.writeln("</form>");


def show_fixgen_table(response, tourney_name, module_list, title, description):
    response.writeln("<h2>%s</h2>" % (htmlcommon.escape(title)))
    if description:
        response.writeln("<p>")
        response.writeln(description)
        response.writeln("</p>")
    response.writeln("<table class=\"fixgentable\">");
    for module_name in module_list:
        fixgen_module = fixgen_modules[module_name]
        response.writeln("<tr>");
        response.writeln("<td class=\"fixgentable fixgen\">");
        response.writeln("<a href=\"/atropine/%s/fixturegen/%s\">" % (htmlcommon.escape(tourney_name), htmlcommon.escape(module_name)))
        response.writeln("<img src=\"/images/fixgen/%s.png\" alt=\"%s\" />" % (htmlcommon.escape(module_name), htmlcommon.escape(fixgen_module.name)))
        response.writeln("</a>")
        response.writeln("</td>")
        response.writeln("<td class=\"fixgentable fixgen\">");
        response.writeln("<a href=\"/atropine/%s/fixturegen/%s\">%s</a>" % (htmlcommon.escape(tourney_name), htmlcommon.escape(module_name), htmlcommon.escape(fixgen_module.name)));
        response.writeln("</td>");
        response.writeln("<td class=\"fixgentable fixgendescription\">%s</td>" % (htmlcommon.escape(fixgen_module.description)));
        response.writeln("</tr>");
    response.writeln("</table>");

def make_fixtures_from_group(group, round_no, division, table_no, next_round_seq, game_type, repeat_threes):
    group_fixtures = []
    round_seq = next_round_seq
    if len(group) % 2 == 1:
        # If there are an odd number of players on this table, then
        # each player takes a turn at hosting, and the player X places
        # clockwise from the host plays the player X places
        # anticlockwise from the host,
        # for X in 1 .. (len(group) - 1) / 2.
        for host in range(len(group)):
            for x in range(1, (len(group) - 1) // 2 + 1):
                left = (host + len(group) + x) % len(group)
                right = (host + len(group) - x) % len(group)
                p1 = group[left]
                p2 = group[right]
                fixture = countdowntourney.Game(round_no, round_seq, table_no, division, game_type, p1, p2)
                group_fixtures.append(fixture)
                round_seq += 1
                if repeat_threes and len(group) == 3:
                    fixture = countdowntourney.Game(round_no, round_seq, table_no, division, game_type, p2, p1)
                    group_fixtures.append(fixture)
                    round_seq += 1
    elif len(group) == 4:
        # Four players on each table. Don't do the general catch-all
        # thing in the next branch, instead show the matches in a
        # specific order so that the first two can be played
        # simultaneously, then the next two, then the last two.
        indices = [ (0,1), (2,3), (0,2), (1,3), (1,2), (3,0) ]
        for (x, y) in indices:
            fixture = countdowntourney.Game(round_no, round_seq, table_no, division, game_type, group[x], group[y])
            group_fixtures.append(fixture)
            round_seq += 1
    else:
        # There are an even number of players. Each player X from
        # X = 0 .. len(group) - 1 plays each player Y for
        # Y in X + 1 .. len(group) - 1
        for x in range(len(group)):
            for y in range(x + 1, len(group)):
                p1 = group[x]
                p2 = group[y]
                if round_seq % 2 == 0 and len(group) > 2:
                    (p1, p2) = (p2, p1)
                fixture = countdowntourney.Game(round_no, round_seq, table_no, division, game_type, p1, p2)
                group_fixtures.append(fixture)
                round_seq += 1
    return group_fixtures

# generated_groups is fixgen.GeneratedGroups object
def make_fixtures_from_groups(tourney, generated_groups):
    fixtures = []
    num_divisions = tourney.get_num_divisions()
    players = tourney.get_active_players()

    (all_accessible_tables, acc_default) = tourney.get_accessible_tables()

    for rd in generated_groups.get_rounds():
        round_no = rd.get_round_no()

        # Find out which tables (if any) already have players on, so we
        # can avoid giving out those table numbers
        occupied_tables = set(tourney.list_occupied_tables_in_round(round_no))

        # Build a list of the remaining players - that is, those players
        # who are not in generated_groups and who have not had any games
        # generated for them so far this round.
        # Also, while we're at it, populate natural_div_to_table numbers
        # based on the set of occupied table numbers and the number of
        # groups in each division.
        remaining_players = players[:]

        # remaining_players is all the active players who aren't being
        # assigned a game in this round right now.
        # Also remove from remaining_players all players who have
        # previously been assigned a table in this round. We'll be left
        # with the players whose games are yet to be decided, but who
        # might want to reserve their favourite table.
        games_this_round = tourney.get_games(round_no=round_no)
        for g in games_this_round:
            for p in g.get_players():
                if p in remaining_players:
                    remaining_players.remove(p)

        start_round_seq = tourney.get_max_game_seq_in_round(round_no)
        if start_round_seq is None:
            next_round_seq = 1
        else:
            next_round_seq = start_round_seq + 1

        candidate_tables = cttable.get_candidate_tables(rd, remaining_players, occupied_tables, all_accessible_tables, acc_default)

        for ct in candidate_tables:
            group_fixtures = make_fixtures_from_group(ct.get_group(),
                    ct.get_round_no(), ct.get_division(),
                    ct.get_table_no(), next_round_seq, ct.get_game_type(),
                    ct.get_repeat_threes())
            next_round_seq += len(group_fixtures)
            fixtures += group_fixtures
    return fixtures


def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    tourney_name = tourney.get_name()
    htmlcommon.print_html_head(response, "Generate Fixtures: " + str(tourney_name));

    response.writeln("<body>");

    exception_content = None
    exceptions_to_show = []
    warning_content = None
    show_fixgen_list = False
    fixgen_ask_divisions = False
    show_fixgen_settings_form = None
    new_fixtures_to_accept = None
    new_fixture_rounds = None
    success_content = None
    show_link_to_round = None
    fixgen_settings = None
    check_ready_failed = False
    no_players = False

    if len(extra_components) > 0:
        generator_name = extra_components[0]
    else:
        generator_name = None

    try:
        if generator_name:
            fixgen_settings = FixtureGeneratorSettings(tourney.get_fixgen_settings(generator_name));
        else:
            fixgen_settings = None

        num_divisions = tourney.get_num_divisions()
        if len(tourney.get_active_players()) == 0:
            exception_content = "You can't generate fixtures because the tournament doesn't have any active players."
            no_players = True
        elif generator_name is None:
            num_players_requiring_accessible_table = tourney.get_num_active_players_requiring_accessible_table()
            num_accessible_tables = tourney.get_num_accessible_tables()
            if num_accessible_tables is not None and num_players_requiring_accessible_table > num_accessible_tables:
                warning_content = "You have %d active player%s who %s, but %s. This means the fixture generator cannot ensure %s. You can define accessible tables in <a href=\"/atropine/%s/tourneysetup\">Tourney Setup</a>." % (
                    num_players_requiring_accessible_table,
                    "s" if num_players_requiring_accessible_table != 1 else "",
                    "requires an accessible table" if num_players_requiring_accessible_table == 1 else "require accessible tables",
                    "you haven't defined any accessible tables" if num_accessible_tables == 0 else ("you have only defined %d accessible table%s" % (num_accessible_tables, "" if num_accessible_tables == 1 else "s")),
                    "this player is given an accessible table" if num_players_requiring_accessible_table == 1 else "these players are given accessible tables",
                    htmlcommon.escape(tourney.get_name())
                )

            show_fixgen_list = True

        elif generator_name not in fixgen_modules:
            exception_content = "No such generator %s." % (htmlcommon.escape(generator_name))
        elif num_divisions > 1 and not form.getfirst("_divsubmit") and "accept" not in form:
            fixgen_ask_divisions = True
        else:
            fixturegen = fixgen_modules[generator_name]
            if "submit" not in form:
                fixgen_settings = FixtureGeneratorSettings(tourney.get_fixgen_settings(generator_name));
            else:
                fixgen_settings = FixtureGeneratorSettings()

            for key in form:
                fixgen_settings[key] = form.getfirst(key);

            if fixgen_settings.get("_divsubmit", None) is None:
                fixgen_settings["_divsubmit"] = "Next"
                for div in range(num_divisions):
                    next_free_round_number = tourney.get_next_free_round_number_for_division(div)
                    fixgen_settings["_div%d" % (div)] = "1"
                    fixgen_settings["_div%dround" % (div)] = str(next_free_round_number)

            div_rounds = dict()
            for div in range(num_divisions):
                if int_or_none(fixgen_settings.get("_div%d" % (div), "0")):
                    start_round = int_or_none(fixgen_settings.get("_div%dround" % (div), None))
                    if start_round is not None and start_round > 0:
                        div_rounds[div] = start_round

            if len(div_rounds) == 0:
                raise countdowntourney.FixtureGeneratorException("No divisions selected, so can't generate fixtures.")

            (ready, excuse) = fixturegen.check_ready(tourney, div_rounds);

            if ready:
                settings_form = fixturegen.get_user_form(tourney, fixgen_settings, div_rounds);
                if settings_form is None and "accept" not in form:
                    # We don't require any more information from the user, so
                    # generate the fixtures.
                    generated_groups = fixturegen.generate(tourney, fixgen_settings, div_rounds);

                    # Persist the settings used to generate these fixtures,
                    # in case the fixture generator wants to refer to them
                    # when we call it later on
                    tourney.store_fixgen_settings(generator_name, fixgen_settings)

                    new_fixtures_to_accept = make_fixtures_from_groups(tourney, generated_groups)
                    new_fixture_rounds = generated_groups.get_rounds()
                elif "accept" in form:
                    # Fixtures have been accepted - write them to the db
                    json_fixture_plan = form.getfirst("jsonfixtureplan");
                    if not json_fixture_plan:
                        raise countdowntourney.TourneyException("Accept fixtures form doesn't include the jsonfixtureplan field. This is probably a bug unless you built the HTTP request yourself rather than using the form. If you did that then you're being a smartarse.");

                    fixture_plan = json.loads(json_fixture_plan);

                    dict_fixtures = fixture_plan.get("fixtures", []);
                    dict_rounds = fixture_plan.get("rounds", None);
                    fixtures = [];
                    earliest_round_no = None;
                    try:
                        for f in dict_fixtures:
                            round_no = int(f["round_no"])
                            table_no = int(f["table_no"]);
                            round_seq = int(f["round_seq"]);
                            division = int(f["division"])
                            game_type = f["game_type"];
                            name1 = f.get("p1");
                            p1 = tourney.get_player_from_name(name1);
                            name2 = f.get("p2");
                            p2 = tourney.get_player_from_name(name2);

                            if earliest_round_no is None or earliest_round_no > round_no:
                                earliest_round_no = round_no;

                            f = countdowntourney.Game(round_no, round_seq, table_no,
                                    division, game_type, p1, p2);
                            fixtures.append(f);
                    except countdowntourney.TourneyException as e:
                        raise e
                    except ValueError:
                        raise countdowntourney.TourneyException("Fixtures contained garbage. Not much else I can do now other than sit down and refuse to work.")

                    if fixtures:
                        tourney.merge_games(fixtures);
                        success_content = "%d fixtures added successfully." % (len(fixtures))
                        show_link_to_round = earliest_round_no

                        if dict_rounds:
                            for r in dict_rounds:
                                try:
                                    round_no = int(r["round"]);
                                    round_name = r.get("name", "");
                                    tourney.name_round(round_no, round_name);
                                except countdowntourney.TourneyException as e:
                                    exceptions_to_show.append(e)

                else:
                    settings_form.add_element(htmlform.HTMLFormHiddenInput("generator", generator_name));
                    for name in fixgen_settings:
                        if name[0:6] != "submit" and settings_form.get_value(name) is None:
                            settings_form.add_element(htmlform.HTMLFormHiddenInput(name, fixgen_settings.get(name, "")));
                    if fixgen_settings.get("submit", None) and fixturegen.save_form_on_submit():
                        tourney.store_fixgen_settings(generator_name, fixgen_settings)
                    show_fixgen_settings_form = settings_form
            else:
                # Can't use this fixture generator at the moment, and it's not
                # because the user needs to provide us information - it's
                # that there aren't the right number of players, or the
                # previous round hasn't finished, or something like that.
                check_ready_failed = True
                exception_content = "Couldn't generate fixtures: %s" % (excuse)

    except countdowntourney.TourneyException as e:
        exceptions_to_show.append(e)


    # We haven't written any body HTML yet, because if the user has just
    # accepted a list of fixtures, we want to write those to the database
    # before we display the sidebar, so that the sidebar contains a link to the
    # new round.

    if tourney:
        htmlcommon.show_sidebar(response, tourney);

    response.writeln("<div class=\"mainpane\">");

    # First, write a heading, which is the fixture generator name if we know it,
    # or the words "Fixture Generator" if that hasn't been selected yet.
    if generator_name and generator_name in fixgen_modules:
        fixturegen = fixgen_modules[generator_name]
    else:
        fixturegen = None

    if fixturegen:
        response.writeln("<h1>%s</h1>" % (fixturegen.name))
    else:
        response.writeln("<h1>Generate Fixtures</h1>")

    # If exception_content is set, show the exception box.
    if exception_content:
        htmlcommon.show_error_text(response, exception_content)

    # Also show an exception box for each exception in the list exceptions_to_show.
    if exceptions_to_show:
        for e in exceptions_to_show:
            htmlcommon.show_tourney_exception(response, e);

    if exception_content or exceptions_to_show:
        response.writeln("<p>")
        if generator_name and not check_ready_failed:
            response.writeln("<a href=\"/atropine/%s/fixturegen/%s\">Sigh...</a>" % (htmlcommon.escape(tourney_name), htmlcommon.escape(generator_name)))
        elif no_players:
            response.writeln("<a href=\"/atropine/%s/tourneysetup\">Set the player list at the tourney setup page</a>" % (htmlcommon.escape(tourney_name)))
        else:
            response.writeln("<a href=\"/atropine/%s/fixturegen\">Sigh...</a>" % (htmlcommon.escape(tourney_name)))
        response.writeln("</p>")

    # Show any warning...
    if warning_content:
        htmlcommon.show_warning_box(response, warning_content)

    # And a success box, if we've just saved the new fixtures to the db.
    if success_content:
        htmlcommon.show_success_box(response, success_content)


    # show_fixgen_list is set when the user hasn't yet picked a fixture generator.
    if show_fixgen_list:
        num_divisions = tourney.get_num_divisions()

        response.writeln("<p>")
        response.writeln("When you want to generate the next round's fixtures, choose a fixture generator from the list below.")
        if num_divisions > 1:
            response.writeln("If you want to generate fixtures for only one division or a subset of divisions, you'll be asked which divisions to generate fixtures for on the next screen.")
        response.writeln("</p>");

        rounds = tourney.get_rounds()
        if rounds:
            suggested_fixgens = fixgens_not_r1
            suggested_title = "Suggested fixture generators"
            suggested_description = "Fixtures for the second round onwards are usually generated by one of these fixture generators."
        else:
            suggested_fixgens = fixgens_r1
            suggested_title = "Suggested fixture generators"
            suggested_description = "Fixtures for the first round are usually generated by one of these fixture generators."

        remaining_fixgens = []
        for fixgen_name in fixgen_modules:
            if fixgen_name not in suggested_fixgens:
                remaining_fixgens.append(fixgen_name)
        show_fixgen_table(response, tourney_name, suggested_fixgens, suggested_title, suggested_description)
        show_fixgen_table(response, tourney_name, remaining_fixgens, "Other fixture generators", "")

    # After picking a fixture generator, the user is asked to select which
    # divisions they want to generate fixtures for, if there's more than one
    # division.
    if fixgen_ask_divisions:
        elements = []
        elements.append(htmlform.HTMLFragment("<p>Which divisions do you want to generate fixtures for, starting from which rounds? By default, a division's fixtures will go in the round after the latest round which has games for that division.</p>"))
        num_divisions = tourney.get_num_divisions()
        elements.append(htmlform.HTMLFragment("<table class=\"misctable\" style=\"margin-bottom: 20px;\">"))
        elements.append(htmlform.HTMLFragment("<tr><th>Division</th><th>Round number</th></tr>"))
        for div in range(num_divisions):
            elements.append(htmlform.HTMLFragment("<tr><td class=\"control\" style=\"text-align: left;\">"))
            elements.append(htmlform.HTMLFormCheckBox("_div%d" % (div), tourney.get_division_name(div), True, other_attrs={"style" : "margin-right: 10px;"}))
            next_free_round_number = tourney.get_next_free_round_number_for_division(div)
            elements.append(htmlform.HTMLFragment("</td><td class=\"control\">"))
            elements.append(htmlform.HTMLFormNumberInput("", "_div%dround" % (div), str(next_free_round_number)))
            elements.append(htmlform.HTMLFragment("</td></tr>"))
        elements.append(htmlform.HTMLFragment("</table>"))
        elements.append(htmlform.HTMLFormSubmitButton("_divsubmit", "Next", other_attrs={"class" : "bigbutton"}))
        settings_form = htmlform.HTMLForm("POST", "/atropine/%s/fixturegen/%s" % (htmlcommon.escape(tourney.get_name()), htmlcommon.escape(generator_name)), elements)
        response.writeln(settings_form.html());

    # If the user has selected which divisions they want to generate fixtures
    # for, or if there is only one division, we now show the settings form for
    # that fixture generator. What it actually shows depends on which fixture
    # generator it is, and how any previous questions served up in this step
    # were answered.
    elif show_fixgen_settings_form:
        response.writeln(show_fixgen_settings_form.html());

    # If the user has generated a set of fixtures, they will be in
    # new_fixtures_to_accept. Display them as a table with a button inviting
    # the user to accept them.
    elif new_fixtures_to_accept:
        show_fixtures_to_accept(response, tourney, generator_name, new_fixtures_to_accept, new_fixture_rounds, fixgen_settings)

    # If the user has just accepted the table of fixtures, we will have
    # displayed a "success" info box above, and we also want to show a link to
    # the round we just generated, or the earliest such round if we generated
    # for more than one round.
    if show_link_to_round is not None:
        response.writeln("<p><a href=\"/atropine/%s/games/%d\">Go to result entry page</a></p>" % (htmlcommon.escape(tourney_name), show_link_to_round));

    # end mainpane div
    response.writeln("</div>");

    response.writeln("</body>");
    response.writeln("</html>");
