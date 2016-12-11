#!/usr/bin/python

import sys;
import cgi;
import cgitb;
import os;
import cgicommon;
import urllib;
import importlib;
import json;

cgitb.enable();

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/fixturegen.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

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

cgicommon.print_html_head("Fixture Generator: " + str(tourney_name));

print "<body>";

if tourney_name is None:
    print "<h1>No tourney specified</h1>";
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
    print "</body>";
    print "</html>";
    sys.exit(0);

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);
    cgicommon.show_sidebar(tourney);

    print "<div class=\"mainpane\">";
    generator_name = form.getfirst("generator");
    module_list = generators.get_fixture_generator_list();
    num_divisions = tourney.get_num_divisions()
    if len(tourney.get_active_players()) == 0:
        print "<h1>Fixture Generator</h1>";
        print "<p>You can't generate fixtures because the tournament doesn't have any active players.</p>"
    elif generator_name is None:
        print "<h1>Fixture Generator</h1>";
        print "<p>The following fixture generators are available.</p>";

        print "<table class=\"fixgentable\">";
        print "<tr><th class=\"fixgentable fixgenth\">Fixture Generator</th><th class=\"fixgentable fixgenth\">Module Name</th><th class=\"fixgentable fixgenth\">Description</th></tr>";
        for module_name in module_list:
            fixgen_module = importlib.import_module(module_name);
            print "<tr>";
            print "<td class=\"fixgentable fixgen\">";
            print "<a href=\"/cgi-bin/fixturegen.py?generator=%s&amp;tourney=%s\">%s</a>" % (urllib.quote_plus(module_name), urllib.quote_plus(tourney_name), cgi.escape(fixgen_module.name));
            print "</td>";
            print "<td class=\"fixgentable fixgenmodule\">%s</td>" % (cgi.escape(module_name));
            print "<td class=\"fixgentable fixgendescription\">%s</td>" % (cgi.escape(fixgen_module.description));
            print "</tr>";
        print "</table>";
    elif generator_name not in module_list:
        print "<h1>Fixture Generator</h1>";
        print "<p>No such generator %s.</p>" % cgi.escape(generator_name);
    elif num_divisions > 1 and not form.getfirst("_divsubmit") and "accept" not in form:
        fixturegen = importlib.import_module(generator_name);
        print "<h1>%s</h1>" % (cgi.escape(fixturegen.name));
        fixgen_settings = FixtureGeneratorSettings(tourney.get_fixgen_settings(generator_name));
        elements = []
        elements.append(htmlform.HTMLFragment("<p>Which divisions do you want to generate fixtures for, starting from which rounds? By default, a division's fixtures will go in the round after the latest round which has games for that division.</p>"))
        for div in range(num_divisions):
            elements.append(htmlform.HTMLFragment("<p>"))
            elements.append(htmlform.HTMLFormCheckBox("_div%d" % (div), tourney.get_division_name(div), True))
            next_free_round_number = tourney.get_next_free_round_number_for_division(div)
            elements.append(htmlform.HTMLFormTextInput(" round ", "_div%dround" % (div), str(next_free_round_number)))
            elements.append(htmlform.HTMLFragment("</p>"))
        elements.append(htmlform.HTMLFormSubmitButton("_divsubmit", "Next"))
        settings_form = htmlform.HTMLForm("POST", "/cgi-bin/fixturegen.py?tourney=%s&amp;generator=%s" % (urllib.quote_plus(tourney.get_name()), urllib.quote_plus(generator_name)), elements)
        print settings_form.html();
    else:
        fixturegen = importlib.import_module(generator_name);
        print "<h1>%s</h1>" % (cgi.escape(fixturegen.name));
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
                fixture_plan = fixturegen.generate(tourney, fixgen_settings, div_rounds);
                fixtures = fixture_plan["fixtures"];
                rounds = fixture_plan["rounds"];
                
                # Persist the settings used to generate these fixtures,
                # in case the fixture generator wants to refer to them
                # when we call it later on
                tourney.store_fixgen_settings(generator_name, fixgen_settings)

                print "<p>I've generated the following fixtures. Click \"Accept Fixtures\" to commit them to the database.</p>";
                num_divisions = tourney.get_num_divisions()
                for r in rounds:
                    round_no = int(r["round"]);
                    print "<h2>%s</h2>" % r.get("name", "Round %d" % round_no);

                    for div_index in range(num_divisions):
                        round_fixtures = filter(lambda x : x.round_no == round_no and x.division == div_index, fixtures);
                        if len(round_fixtures) == 0:
                            continue

                        standings = tourney.get_standings(division=div_index)
                        standings_dict = dict()
                        for s in standings:
                            standings_dict[s.name] = s
                        if num_divisions > 1:
                            print "<h3>%s</h3>" % (cgi.escape(tourney.get_division_name(div_index)))
                        print "<table class=\"fixturetable\">";
                        print "<tr><th>Table</th><th>Type</th><th></th><th></th><th></th></tr>";

                        fixnum = 0;
                        last_table_no = None;
                        for f in round_fixtures:
                            if last_table_no is None or last_table_no != f.table_no:
                                num_games_on_table = len(filter(lambda x : x.table_no == f.table_no, round_fixtures));
                                first_game_on_table = True;
                                print "<tr class=\"firstgameintable\">";
                            else:
                                first_game_on_table = False;
                                print "<tr>";

                            if first_game_on_table:
                                print "<td class=\"tableno\" rowspan=\"%d\">%d</td>" % (num_games_on_table, f.table_no);

                            print "<td class=\"gametype\">%s</td>" % cgi.escape(f.game_type);
                            player_td_html = []
                            for name in [f.p1.name, f.p2.name]:
                                standings_row = standings_dict.get(name, None)
                                if standings_row is None:
                                    player_td_html.append("<strong>%s</strong>" % (cgi.escape(name)) + " ?")
                                else:
                                    player_td_html.append("<strong>%s</strong>" % (cgi.escape(name)) +
                                            " (%s, %d win%s%s)" % (
                                                cgicommon.ordinal_number(standings_row.position),
                                                standings_row.wins,
                                                "" if standings_row.wins == 1 else "s",
                                                "" if standings_row.draws == 0 else ", %d draw%s" % (standings_row.draws, "" if standings_row.draws == 1 else "s")))

                            print "<td class=\"gameplayer1\">%s</td><td class=\"gamescore\">v</td><td class=\"gameplayer2\">%s</td>" % tuple(player_td_html);
                            print "</tr>";
                            fixnum += 1;
                            last_table_no = f.table_no;

                        print "</table>";
                print "<form method=\"POST\" action=\"/cgi-bin/fixturegen.py\">";
                print "<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % cgi.escape(tourney_name, True);
                print "<input type=\"hidden\" name=\"generator\" value=\"%s\" />" % cgi.escape(generator_name, True);

                # Remember all the _div* settings, or check_ready might
                # object when we do try to submit the fixtures
                for name in fixgen_settings:
                    if name[0:4] == "_div":
                        print "<input type=\"hidden\" name=\"%s\" value=\"%s\" />" % (cgi.escape(name, True), cgi.escape(fixgen_settings[name], True))

                dict_fixtures = [];
                for f in fixtures:
                    dict_fixtures.append(f.make_dict());

                fixture_plan = {
                        "fixtures" : dict_fixtures,
                        "rounds" : rounds
                };
                json_fixture_plan = json.dumps(fixture_plan);
                print "<input type=\"hidden\" name=\"jsonfixtureplan\" value=\"%s\" />" % cgi.escape(json_fixture_plan, True);
                print "<p>"
                print "<input type=\"submit\" name=\"accept\" value=\"Accept Fixtures\" />";
                print "</p>"
                print "</form>";
            elif "accept" in form:
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
                    cgicommon.show_tourney_exception(e);
                    fixtures = None;
                except ValueError:
                    print "<p>Fixtures contained garbage. Not much else I can do now other than sit down and refuse to work.</p>";
                    fixtures = None;

                if fixtures:
                    try:
                        tourney.merge_games(fixtures);
                        print "<h2>%d fixtures added successfully</h2>" % (len(fixtures));
                        print "<p><a href=\"/cgi-bin/games.py?tourney=%s&round=%d\">View games</a></p>" % (urllib.quote_plus(tourney_name), earliest_round_no);
                    except countdowntourney.TourneyException as e:
                        print "<p>Failed to add new fixtures to database!</p>";
                        cgicommon.show_tourney_exception(e);

                if dict_rounds:
                    for r in dict_rounds:
                        try:
                            round_no = int(r["round"]);
                            round_name = r.get("name", "Round %d" % round_no);
                            tourney.name_round(round_no, round_name);
                        except countdowntourney.TourneyException as e:
                            print "<p>Failed to name a round</p>";
                            cgicommon.show_tourney_exception(e);

            else:
                print "<h2>Information this fixture generator needs from you...</h2>";
                settings_form.add_element(htmlform.HTMLFormHiddenInput("tourney", tourney_name));
                settings_form.add_element(htmlform.HTMLFormHiddenInput("generator", generator_name));
                for name in fixgen_settings:
                    if name[0:6] != "submit" and settings_form.get_value(name) is None:
                        settings_form.add_element(htmlform.HTMLFormHiddenInput(name, fixgen_settings.get(name, "")));
                if fixgen_settings.get("submit", None) and fixturegen.save_form_on_submit():
                    tourney.store_fixgen_settings(generator_name, fixgen_settings)
                print settings_form.html();
        else:
            # Can't use this fixture generator at the moment, and it's not
            # because the user needs to provide us information - it's
            # that there aren't the right number of players, or the
            # previous round hasn't finished, or something like that.
            print "<h2>Cannot generate fixtures...</h2>"
            print "<p>%s</p>" % excuse;
    print "</div>";

except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);
    generator_name = form.getfirst("generator");
    print "<p>"
    if generator_name:
        print "<a href=\"/cgi-bin/fixturegen.py?tourney=%s&amp;generator=%s\">Sigh...</a>" % (urllib.quote_plus(tourney_name), urllib.quote_plus(generator_name))
    else:
        print "<a href=\"/cgi-bin/fixturegen.py?tourney=%s\">Sigh...</a>" % (urllib.quote_plus(tourney_name))
    print "</p>"

print "</body>";
print "</html>";
