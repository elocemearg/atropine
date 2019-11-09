#!/usr/bin/python3

import sys;
import cgi;
import cgitb;
import os;
import cgicommon;
import urllib.request, urllib.parse, urllib.error;
import importlib;
import json;

cgitb.enable();

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/fixturegen.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");
popular_fixgens = [ "fixgen_swiss", "fixgen_random", "fixgen_random_seeded" ]

cgicommon.set_module_path();

import generators;
import countdowntourney;
import htmlform;

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


def show_fixtures_to_accept(tourney, generator_name, fixtures, fixgen_settings):
    tourney_name = tourney.get_name()
    cgicommon.writeln("<form method=\"POST\" action=\"/cgi-bin/fixturegen.py\">");
    cgicommon.writeln("<div class=\"fixtureacceptbox\">")
    cgicommon.writeln("<p>I've generated the following fixtures. They won't be saved until you click the <em>Accept Fixtures</em> button.</p>");
    cgicommon.writeln("<input type=\"submit\" name=\"accept\" class=\"bigbutton\" value=\"Accept Fixtures\" />");
    cgicommon.writeln("<a href=\"/cgi-bin/fixturegen.py?tourney=%s&generator=%s\" class=\"fixturecancellink\">Discard and return to fixture generator</a>" % (
        urllib.parse.quote_plus(tourney_name),
        urllib.parse.quote_plus(generator_name)
    ))
    cgicommon.writeln("</div>")
    num_divisions = tourney.get_num_divisions()
    for r in generated_groups.get_rounds():
        round_no = r.get_round_no()
        cgicommon.writeln("<h2>%s</h2>" % cgicommon.escape(r.get_round_name()))

        for div_index in range(num_divisions):
            round_fixtures = [x for x in fixtures if x.round_no == round_no and x.division == div_index];
            if len(round_fixtures) == 0:
                continue

            standings = tourney.get_standings(division=div_index)
            standings_dict = dict()
            for s in standings:
                standings_dict[s.name] = s
            if num_divisions > 1:
                cgicommon.writeln("<h3>%s</h3>" % (cgicommon.escape(tourney.get_division_name(div_index))))
            cgicommon.writeln("<table class=\"fixturetable\">");
            cgicommon.writeln("<tr><th>Table</th><th>Type</th><th></th><th></th><th></th><th></th></tr>");

            fixnum = 0;
            last_table_no = None;
            for f in round_fixtures:
                if last_table_no is None or last_table_no != f.table_no:
                    num_games_on_table = len([x for x in round_fixtures if x.table_no == f.table_no]);
                    first_game_on_table = True;
                    cgicommon.writeln("<tr class=\"firstgameintable\">");
                else:
                    first_game_on_table = False;
                    cgicommon.writeln("<tr>");

                if first_game_on_table:
                    cgicommon.writeln("<td class=\"tableno\" rowspan=\"%d\">%d</td>" % (num_games_on_table, f.table_no));

                cgicommon.writeln("<td class=\"gametype\">%s</td>" % cgicommon.escape(f.game_type));
                player_td_html = []
                for player in [f.p1, f.p2]:
                    name = player.name
                    standings_row = standings_dict.get(name, None)
                    if standings_row is None:
                        player_td_html.append(cgicommon.player_to_link(player, tourney_name, emboldenise=True, disable_tab_order=False, open_in_new_window=True) + " ?")
                    else:
                        player_td_html.append(cgicommon.player_to_link(player, tourney_name, emboldenise=True, disable_tab_order=False, open_in_new_window=True) +
                                " (%s, %d win%s%s)" % (
                                    cgicommon.ordinal_number(standings_row.position),
                                    standings_row.wins,
                                    "" if standings_row.wins == 1 else "s",
                                    "" if standings_row.draws == 0 else ", %d draw%s" % (standings_row.draws, "" if standings_row.draws == 1 else "s")))

                cgicommon.writeln("<td class=\"gameplayer1\">%s</td><td class=\"gamescore\">v</td><td class=\"gameplayer2\">%s</td>" % tuple(player_td_html));
                num_repeats = tourney.count_games_between(f.p1, f.p2)
                if num_repeats:
                    cgicommon.writeln("<td class=\"gamerepeats\">%s repeat</td>" % (cgicommon.ordinal_number(num_repeats)))
                else:
                    cgicommon.writeln("<td class=\"gameremarks\"></td>")
                cgicommon.writeln("</tr>");
                fixnum += 1;
                last_table_no = f.table_no;

            cgicommon.writeln("</table>");
    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgicommon.escape(tourney_name, True));
    cgicommon.writeln("<input type=\"hidden\" name=\"generator\" value=\"%s\" />" % cgicommon.escape(generator_name, True));

    # Remember all the _div* settings, or check_ready might
    # object when we do try to submit the fixtures
    for name in fixgen_settings:
        if name[0:4] == "_div":
            cgicommon.writeln("<input type=\"hidden\" name=\"%s\" value=\"%s\" />" % (cgicommon.escape(name, True), cgicommon.escape(fixgen_settings[name], True)))

    fixture_plan = {
            "fixtures" : [
                x.make_dict() for x in fixtures
            ],
            "rounds" : [
                {
                    "round" : x.get_round_no(),
                    "name" : x.get_round_name()
                } for x in generated_groups.get_rounds()
            ]
    }
    json_fixture_plan = json.dumps(fixture_plan);
    cgicommon.writeln("<input type=\"hidden\" name=\"jsonfixtureplan\" value=\"%s\" />" % cgicommon.escape(json_fixture_plan, True));
    cgicommon.writeln("<div class=\"fixtureacceptbox\">")
    cgicommon.writeln("<input type=\"submit\" name=\"accept\" value=\"Accept Fixtures\" class=\"bigbutton\" />");
    cgicommon.writeln("<a href=\"/cgi-bin/fixturegen.py?tourney=%s&generator=%s\" class=\"fixturecancellink\">Discard and return to fixture generator</a>" % (
        urllib.parse.quote_plus(tourney_name),
        urllib.parse.quote_plus(generator_name)
    ))
    cgicommon.writeln("</div>")
    cgicommon.writeln("</form>");

cgicommon.print_html_head("Fixture Generator: " + str(tourney_name));

cgicommon.writeln("<body>");

cgicommon.assert_client_from_localhost()

if tourney_name is None:
    cgicommon.show_error_text("No tourney specified.");
    cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>");
    cgicommon.writeln("</body>");
    cgicommon.writeln("</html>");
    sys.exit(0);

exception_content = None
exceptions_to_show = []
warning_content = None
show_fixgen_list = False
fixgen_ask_divisions = False
show_fixgen_settings_form = None
new_fixtures_to_accept = None
success_content = None
show_link_to_round = None
tourney = None
module_list = []
fixgen_settings = None

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

    generator_name = form.getfirst("generator");
    if generator_name:
        fixgen_settings = FixtureGeneratorSettings(tourney.get_fixgen_settings(generator_name));
    else:
        fixgen_settings = None

    module_list = generators.get_fixture_generator_list();
    num_divisions = tourney.get_num_divisions()
    if len(tourney.get_active_players()) == 0:
        exception_content = "You can't generate fixtures because the tournament doesn't have any active players."
    elif generator_name is None:
        num_players_requiring_accessible_table = tourney.get_num_active_players_requiring_accessible_table()
        num_accessible_tables = tourney.get_num_accessible_tables()
        if num_accessible_tables is not None and num_players_requiring_accessible_table > num_accessible_tables:
            warning_content = "You have %d active player%s who %s, but %s. This means the fixture generator cannot ensure %s. You can define accessible tables in <a href=\"/cgi-bin/tourneysetup.py?tourney=%s\">General Setup</a>." % (
                num_players_requiring_accessible_table,
                "s" if num_players_requiring_accessible_table != 1 else "",
                "requires an accessible table" if num_players_requiring_accessible_table == 1 else "require accessible tables",
                "you haven't defined any accessible tables" if num_accessible_tables == 0 else ("you have only defined %d accessible table%s" % (num_accessible_tables, "" if num_accessible_tables == 1 else "s")),
                "this player is given an accessible table" if num_players_requiring_accessible_table == 1 else "these players are given accessible tables",
                urllib.parse.quote_plus(tourney.get_name())
            )

        show_fixgen_list = True

    elif generator_name not in module_list:
        exception_content = "No such generator %s." % (cgicommon.escape(generator_name))
    elif num_divisions > 1 and not form.getfirst("_divsubmit") and "accept" not in form:
        fixgen_ask_divisions = True
    else:
        fixturegen = importlib.import_module(generator_name);
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

                new_fixtures_to_accept = tourney.make_fixtures_from_groups(generated_groups)
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
                        if name1:
                            p1 = tourney.get_player_from_name(name1);
                        else:
                            p1 = countdowntourney.PlayerPending.from_dict(f["p1pending"]);
                        name2 = f.get("p2");
                        if name2:
                            p2 = tourney.get_player_from_name(name2);
                        else:
                            p2 = countdowntourney.PlayerPending.from_dict(f["p2pending"]);

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
                settings_form.add_element(htmlform.HTMLFormHiddenInput("tourney", tourney_name));
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
            exception_content = "Couldn't generate fixtures: %s" % (excuse)

except countdowntourney.TourneyException as e:
    exceptions_to_show.append(e)


# We haven't written any body HTML yet, because if the user has just accepted
# a list of fixtures, we want to write those to the database before we display
# the sidebar, so that the sidebar contains a link to the new round.

if tourney:
    cgicommon.show_sidebar(tourney);

cgicommon.writeln("<div class=\"mainpane\">");

# First, write a heading, which is the fixture generator name if we know it,
# or the words "Fixture Generator" if that hasn't been selected yet.
if generator_name:
    fixturegen = importlib.import_module(generator_name);
else:
    fixturegen = None

if fixturegen:
    cgicommon.writeln("<h1>%s</h1>" % (fixturegen.name))
else:
    cgicommon.writeln("<h1>Fixture Generator</h1>")

# If exception_content is set, show the exception box.
if exception_content:
    cgicommon.show_error_text(exception_content)

# Also show an exception box for each exception in the list exceptions_to_show.
if exceptions_to_show:
    for e in exceptions_to_show:
        cgicommon.show_tourney_exception(e);

if exception_content or exceptions_to_show:
    cgicommon.writeln("<p>")
    if generator_name:
        cgicommon.writeln("<a href=\"/cgi-bin/fixturegen.py?tourney=%s&amp;generator=%s\">Sigh...</a>" % (urllib.parse.quote_plus(tourney_name), urllib.parse.quote_plus(generator_name)))
    else:
        cgicommon.writeln("<a href=\"/cgi-bin/fixturegen.py?tourney=%s\">Sigh...</a>" % (urllib.parse.quote_plus(tourney_name)))
    cgicommon.writeln("</p>")

# Show any warning...
if warning_content:
    cgicommon.show_warning_box(warning_content)

# And a success box, if we've just saved the new fixtures to the db.
if success_content:
    cgicommon.show_success_box(success_content)


# show_fixgen_list is set when the user hasn't yet picked a fixture generator.
if show_fixgen_list:
    cgicommon.writeln("<p>Choose a fixture generator from the table below.</p>");
    cgicommon.writeln("<p>")
    cgicommon.writeln("The most commonly-used fixture generators are ")

    links = []
    for module_name in module_list:
        if module_name in popular_fixgens:
            fixgen_module = importlib.import_module(module_name)
            links.append("<a href=\"/cgi-bin/fixturegen.py?generator=%s&amp;tourney=%s\">%s</a>" % (
                    urllib.parse.quote_plus(module_name),
                    urllib.parse.quote_plus(tourney_name),
                    fixgen_module.name
                )
            )
    for i in range(len(links)):
        if i == len(links) - 1:
            cgicommon.write(" and ")
        elif i > 0:
            cgicommon.write(", ")
        cgicommon.write(links[i])
    cgicommon.writeln(".</p>")

    cgicommon.writeln("<table class=\"fixgentable\">");
    cgicommon.writeln("<tr><th class=\"fixgentable fixgenth\"></th><th class=\"fixgentable fixgenth\">Generator</th><th class=\"fixgentable fixgenth\">Description</th></tr>");
    for module_name in module_list:
        fixgen_module = importlib.import_module(module_name);
        cgicommon.writeln("<tr>");
        cgicommon.writeln("<td class=\"fixgentable fixgen\">");
        cgicommon.writeln("<a href=\"/cgi-bin/fixturegen.py?generator=%s&amp;tourney=%s\">" % (urllib.parse.quote_plus(module_name), urllib.parse.quote_plus(tourney_name)))
        cgicommon.writeln("<img src=\"/images/fixgen/%s.png\" alt=\"%s\" />" % (cgicommon.escape(module_name), cgicommon.escape(fixgen_module.name)))
        cgicommon.writeln("</a>")
        cgicommon.writeln("</td>")
        cgicommon.writeln("<td class=\"fixgentable fixgen\">");
        cgicommon.writeln("<a href=\"/cgi-bin/fixturegen.py?generator=%s&amp;tourney=%s\">%s</a>" % (urllib.parse.quote_plus(module_name), urllib.parse.quote_plus(tourney_name), cgicommon.escape(fixgen_module.name)));
        cgicommon.writeln("</td>");
        #cgicommon.writeln("<td class=\"fixgentable fixgenmodule\">%s</td>" % (cgicommon.escape(module_name)));
        cgicommon.writeln("<td class=\"fixgentable fixgendescription\">%s</td>" % (cgicommon.escape(fixgen_module.description)));
        cgicommon.writeln("</tr>");
    cgicommon.writeln("</table>");

# After picking a fixture generator, the user is asked to select which 
# divisions they want to generate fixtures for, if there's more than one
# division.
if fixgen_ask_divisions:
    elements = []
    elements.append(htmlform.HTMLFragment("<p>Which divisions do you want to generate fixtures for, starting from which rounds? By default, a division's fixtures will go in the round after the latest round which has games for that division.</p>"))
    num_divisions = tourney.get_num_divisions()
    elements.append(htmlform.HTMLFragment("<table class=\"fixdivselector\">"))
    elements.append(htmlform.HTMLFragment("<tr><th>Division</th><th>Round number</th></tr>"))
    for div in range(num_divisions):
        elements.append(htmlform.HTMLFragment("<tr><td>"))
        elements.append(htmlform.HTMLFormCheckBox("_div%d" % (div), tourney.get_division_name(div), True))
        next_free_round_number = tourney.get_next_free_round_number_for_division(div)
        elements.append(htmlform.HTMLFragment("</td><td>"))
        elements.append(htmlform.HTMLFormTextInput("", "_div%dround" % (div), str(next_free_round_number), other_attrs={"class": "fixdivroundsel"}))
        elements.append(htmlform.HTMLFragment("</td></tr>"))
    elements.append(htmlform.HTMLFragment("</table>"))
    elements.append(htmlform.HTMLFormSubmitButton("_divsubmit", "Next", other_attrs={"class" : "bigbutton"}))
    settings_form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s&generator=%s" % (urllib.parse.quote_plus(tourney.get_name()), urllib.parse.quote_plus(generator_name)), elements)
    cgicommon.writeln(settings_form.html());

# If the user has selected which divisions they want to generate fixtures for,
# or if there is only one division, we now show the settings form for that
# fixture generator. What it actually shows depends on which fixture generator
# it is, and how any previous questions served up in this step were answered.
elif show_fixgen_settings_form:
    cgicommon.writeln(show_fixgen_settings_form.html());

# If the user has generated a set of fixtures, they will be in
# new_fixtures_to_accept. Display them as a table with a button inviting the
# user to accept them.
elif new_fixtures_to_accept:
    show_fixtures_to_accept(tourney, generator_name, new_fixtures_to_accept, fixgen_settings)

# If the user has just accepted the table of fixtures, we will have displayed
# a "success" info box above, and we also want to show a link to the round
# we just generated, or the earliest such round if we generated for more than
# one round.
if show_link_to_round is not None:
    cgicommon.writeln("<p><a href=\"/cgi-bin/games.py?tourney=%s&round=%d\">Go to result entry page</a></p>" % (urllib.parse.quote_plus(tourney_name), show_link_to_round));

# end mainpane div
cgicommon.writeln("</div>");

cgicommon.writeln("</body>");
cgicommon.writeln("</html>");

