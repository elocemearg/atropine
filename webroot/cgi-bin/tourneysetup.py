#!/usr/bin/python3

import cgicommon
import csv
import json
import io
import time
import urllib.request, urllib.parse, urllib.error
import countdowntourney

baseurl = "/cgi-bin/tourneysetup.py"

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

def float_or_none(s):
    if s is None:
        return None;
    try:
        return float(s);
    except ValueError:
        return None;

def show_player_drop_down_box(response, players, control_name):
    response.writeln("<select name=\"%s\">" % (control_name))
    response.writeln("<option value=\"\">-- select player --</option>")
    for p in players:
        response.writeln("<option value=\"%s\">%s (%g)</option>" % (cgicommon.escape(p.name, True), cgicommon.escape(p.name), p.rating));
    response.writeln("</select>")

def make_double_quoted_string(s):
    new_string = ['\"']
    for l in s:
        if l == '\n':
            new_string += ['\\', 'n']
        elif l == '\r':
            new_string += ['\\', 'r']
        elif l == '\t':
            new_string += ['\\', 't']
        else:
            if l == '\\' or l == '\"':
                new_string.append('\\')
            new_string.append(l)
    new_string.append('\"')
    return "".join(new_string)

player_list_example_uniform = """Sleve McDichael
Darryl Archideld
Kevin Nogilny
Bobson Dugnutt
Willie Dustice
Todd Bonzalez"""

player_list_example_graduated = """Sleve McDichael
Darryl Archideld
Kevin Nogilny
Bobson Dugnutt
Willie Dustice
Todd Bonzalez"""

player_list_example_manual = """Sleve McDichael,1953
Darryl Archideld,1901
Kevin Nogilny,1874
Bobson Dugnutt,1640
Willie Dustice,1559
Todd Bonzalez,1551"""

player_list_rating_help = "To give a player a rating, put a comma after the player's name and put the rating number after that, e.g. <span class=\"fixedwidth\">Harry Peters,1860</span>"

def handle(httpreq, response, tourney, request_method, form, query_string):
    tourneyname = tourney.get_name()
    playerlist = form.getfirst("playerlist");
    player_list_submit = form.getfirst("playerlistsubmit");
    auto_rating_behaviour = int_or_none(form.getfirst("autoratingbehaviour"))
    if auto_rating_behaviour is None:
        auto_rating_behaviour = countdowntourney.RATINGS_UNIFORM
    modify_player_submit = form.getfirst("modifyplayersubmit");
    full_name = form.getfirst("fullname")
    venue = form.getfirst("venue")
    date_year = form.getfirst("dateyear")
    date_month = form.getfirst("datemonth")
    date_day = form.getfirst("dateday")
    show_draws_column = int_or_none(form.getfirst("showdrawscolumn"))
    accessible_tables_default = int_or_none(form.getfirst("accessibletablesdefault"))
    accessible_tables_string = form.getfirst("accessibletables")
    if not accessible_tables_string:
        accessible_tables_string = ""
    rules_submit = form.getfirst("rulessubmit");

    cgicommon.print_html_head(response, "Tourney Setup: " + str(tourneyname));

    response.writeln("<body onload=\"textAreaChange(); playerListExtraHelpShow();\">");

    response.writeln("<script>")
    response.writeln("""
function set_player_list_example(which) {
    var element = document.getElementById("playerlistexamplepre");
    if (element == null)
        return;

    switch (which) {
""")

    for (num, text) in [
            (countdowntourney.RATINGS_UNIFORM, player_list_example_uniform),
            (countdowntourney.RATINGS_GRADUATED, player_list_example_graduated),
            (countdowntourney.RATINGS_MANUAL, player_list_example_manual)]:
        response.writeln("""
        case %d:
            element.innerText = %s;
            break;
        """ % (num, json.dumps(text)))

    response.writeln("""
    }
}

function splitCSVRecord(line) {
    var inQuote = false;
    var fields = [];
    var currentField = "";

    for (var i = 0; i < line.length; ++i) {
        var c = line[i];
        var out = null;
        if (inQuote) {
            if (c == '\\"') {
                if (i + 1 < line.length && line[i+1] == '\\"') {
                    // escaped quote
                    out = c;
                }
                else {
                    inQuote = false;
                }
            }
            else {
                out = c;
            }
        }
        else {
            if (c == '\\"') {
                inQuote = true;
            }
            else if (c == ',') {
                fields.push(currentField);
                currentField = "";
            }
            else if (c != '\\r' && c != '\\n') {
                out = c;
            }
        }
        if (out != null) {
            currentField += out;
        }
    }
    fields.push(currentField);
    return fields;
}

/* Called when the textarea of player names changes. We parse the list and
   count the number of active players in each division, and in total, and
   update the label below the textarea. */
function textAreaChange() {
    var element = document.getElementById("playerlist");
    if (element == null)
        return;

    var text = element.value;
    var textPos = 0;
    var numDivisions = 1;
    var totalPlayers = 0;
    var totalWithdrawnPlayers = 0;
    var playersThisDivision = 0;
    var withdrawnPlayersThisDivision = 0;
    var divisionPlayerCounts = [];
    var divisionWithdrawnPlayerCounts = [];
    var numPrunes = 0;

    var lastRecord = false;
    var prevName = "-";
    do {
        var recordEndPos = text.indexOf("\\n", textPos);
        if (recordEndPos == -1) {
            recordEndPos = text.length;
            lastRecord = true;
        }
        var record = text.substring(textPos, recordEndPos).trim();
        if (record.length > 0) {
            var fields = splitCSVRecord(record);
            if (fields[0].trim() == "-") {
                if (prevName != "-") {
                    if (playersThisDivision > 0) {
                        divisionPlayerCounts.push(playersThisDivision);
                        divisionWithdrawnPlayerCounts.push(withdrawnPlayersThisDivision);
                        playersThisDivision = 0;
                        withdrawnPlayersThisDivision = 0;
                    }
                    numDivisions++;
                }
            }
            else {
                var isWithdrawn = false;
                for (var i = 0; i < fields.length; ++i) {
                    if (fields[i].trim().toUpperCase() == "W") {
                        isWithdrawn = true;
                        break;
                    }
                    else {
                        var rating = parseInt(fields[i].trim());
                        if (!isNaN(rating) && rating == 0) {
                            numPrunes++;
                        }
                    }
                }
                if (isWithdrawn) {
                    withdrawnPlayersThisDivision++;
                    totalWithdrawnPlayers++;
                }
                playersThisDivision++;
                totalPlayers++;
            }
            prevName = fields[0].trim();
        }
        textPos = recordEndPos + 1;
    } while (!lastRecord);

    if (prevName == "-") {
        /* If the list ends with "-", that doesn't mean there's an empty
           division on the end. */
        numDivisions--;
    }

    if (playersThisDivision > 0) {
        divisionPlayerCounts.push(playersThisDivision);
        divisionWithdrawnPlayerCounts.push(withdrawnPlayersThisDivision);
        playersThisDivision = 0;
        withdrawnPlayersThisDivision = 0;
    }

    var summary = (totalPlayers - totalWithdrawnPlayers).toString() + " active players";
    if (numDivisions > 1) {
        summary += "<br />" + numDivisions.toString() + " divisions (";
        for (var div = 0; div < numDivisions; ++div) {
            if (div > 0) {
                summary += ", ";
            }
            summary += (divisionPlayerCounts[div] - divisionWithdrawnPlayerCounts[div]).toString();
        }
        summary += ")";
    }

    var summaryElement = document.getElementById("playerlistsummary");
    if (summaryElement != null) {
        summaryElement.innerHTML = summary;
    }

    let pruneWarningElement = document.getElementById("prunewarning");
    if (pruneWarningElement) {
        if (numPrunes > 0) {
            pruneWarningElement.className = "prunewarninghighlight";
        }
        else {
            pruneWarningElement.className = "prunewarningnormal";
        }
    }
}

var extraHelpShowing = true;

/* Called when the user clicks the "show more" or "show less" link on the
   player list help box. */
function playerListExtraHelpShow() {
    var linkElement = document.getElementById("playerlistextrahelpshow");
    var extraHelpElement = document.getElementById("playerlistextrahelp");

    if (extraHelpElement != null) {
        extraHelpElement.style.display = (extraHelpShowing ? "none" : null);
    }

    extraHelpShowing = !extraHelpShowing;

    if (linkElement != null) {
        linkElement.innerText = (extraHelpShowing ? "Show less" : "Show more");
    }
}

function setDateToday() {
    var today = new Date();
    var yearBox = document.getElementById("dateyear");
    var monthBox = document.getElementById("datemonth");
    var dayBox = document.getElementById("dateday");

    yearBox.value = today.getFullYear().toString();
    monthBox.value = (today.getMonth() + 1).toString();
    dayBox.value = today.getDate().toString();
}

</script>
""")

    show_success_box = None
    show_exception = None

    if request_method == "POST" and player_list_submit:
        div_index = 0
        if not playerlist:
            playerlist = ""
        lines = playerlist.split("\n");
        lines = [x for x in [x.rstrip() for x in lines] if len(x) > 0];
        reader = csv.reader(lines);
        player_list = [];
        prev_player_name = "-"
        for row in reader:
            player_name = row[0].strip()
            player_rating = None
            player_avoid_prune = False
            player_withdrawn = False
            player_requires_accessible_table = False
            player_team_id = None
            player_table_pref = None
            player_is_newbie = False

            if player_name == "-":
                # This is a division separator, not a player name. It tells us
                # that the players listed after this point go in the next
                # division down.
                if prev_player_name != "-":
                    div_index += 1
            else:
                # For each field after the name:
                # * If it parses as a number, it is the player's rating.
                # * If it's "A", it indicates the player requires an accessible
                #   table.
                # * If it's "N", it indicates the player is a newbie, someone
                #   who may be unfamiliar with how the competition and gameplay
                #   works. It's not mandatory for Atropine to know about this,
                #   but fixture generators may have an option to ensure there
                #   are no all-newbie tables.
                # * If it's "NP", it indicates the player shouldn't play Prune.
                # * If it's "W", it indicates the player is withdrawn.
                # * If it's "T" followed immediately by an integer, then the
                #   player is on a team: 1 or 2.
                # * If it's "P" followed immediately by an integer, then the
                #   player's preferred table is that number.
                # * Otherwise, it is ignored.
                for field in row[1:]:
                    try:
                        player_rating = float(field)
                    except ValueError:
                        field = field.upper().strip()
                        if field == "A":
                            player_requires_accessible_table = True
                        elif field == "NP":
                            player_avoid_prune = True
                        elif field == "W":
                            player_withdrawn = True
                        elif field == "N":
                            player_is_newbie = True
                        elif field and field[0] == "T":
                            try:
                                player_team_id = int(field[1:])
                            except ValueError:
                                player_team_id = None
                        elif field and field[0] == "P":
                            try:
                                player_table_pref = int(field[1:])
                                if player_table_pref < 1:
                                    player_table_pref = None
                            except ValueError:
                                player_table_pref = None

                player_list.append(countdowntourney.EnteredPlayer(player_name,
                    player_rating, div_index, player_team_id,
                    player_avoid_prune, player_withdrawn,
                    player_requires_accessible_table, player_table_pref,
                    player_is_newbie))
            prev_player_name = player_name
        try:
            tourney.set_players(player_list, auto_rating_behaviour);
            show_success_box = "Player list updated."
        except countdowntourney.TourneyException as e:
            show_exception = e

    num_divisions = tourney.get_num_divisions()

    if request_method == "POST" and rules_submit:
        try:
            # User submitted new tourney rules, so set them

            # Accessible tables
            try:
                if not accessible_tables_string:
                    accessible_tables = []
                else:
                    accessible_tables = [ int(x) for x in accessible_tables_string.split(",") ]
                    for x in accessible_tables:
                        if x <= 0:
                            raise countdowntourney.TourneyException("The accessible table list, if set, must be a comma-separated list of positive integers.")
                tourney.set_accessible_tables(accessible_tables, accessible_tables_default != 0)
            except ValueError:
                raise countdowntourney.TourneyException("The accessible table list, if set, must be a comma-separated list of positive integers.")

            # Full name
            if full_name is None:
                full_name = ""
            tourney.set_full_name(full_name)

            if venue is not None:
                tourney.set_venue(venue)

            date_year = int_or_none(date_year)
            date_month = int_or_none(date_month)
            date_day = int_or_none(date_day)
            if date_year and date_month and date_day:
                tourney.set_event_date(date_year, date_month, date_day)
            else:
                tourney.set_event_date(None, None, None)

            # Whether draws are a thing
            tourney.set_show_draws_column(show_draws_column);

            # Qualification analysis
            for div_index in range(num_divisions):
                div_prefix = "div%d_" % (div_index)
                suffixes = [ "lastround", "numgamesperplayer", "qualplaces" ]
                for suffix in suffixes:
                    name = div_prefix + suffix
                    value = form.getfirst(name)
                    if value is None:
                        value = 0
                    else:
                        try:
                            value = int(value)
                        except ValueError:
                            value = 0
                        if value < 0:
                            value = 0
                    tourney.set_attribute(name, value)
            show_success_box = "Tourney properties updated."
        except countdowntourney.TourneyException as e:
            show_exception = e


    # All POST data taken care of, and we've updated the state of the tourney
    # enough that we can now show the sidebar and open the main div. It's
    # important we handle the player list submission before showing the
    # sidebar, because the sidebar won't show most things until there are
    # players submitted.

    cgicommon.show_sidebar(response, tourney);

    response.writeln("<div class=\"mainpane\">");
    response.writeln("<h1>Tourney Setup</h1>");

    if show_success_box:
        cgicommon.show_success_box(response, show_success_box)
    if show_exception:
        cgicommon.show_tourney_exception(response, show_exception);

    players = tourney.get_players();
    players = sorted(players, key=lambda x : x.name);

    response.writeln("<p>")
    if tourney.get_num_games() > 0:
        response.writeln("The tournament has started.")
    if len(players) == 0:
        response.writeln("This isn't much of a tourney yet. It hasn't got any players.")
    else:
        response.writeln("There are <a href=\"player.py?tourney=%s\">%d players</a>," % (urllib.parse.quote_plus(tourney.get_name()), len(players)))
        num_active = len([x for x in players if not x.is_withdrawn()])
        if num_active != len(players):
            response.writeln("of whom %d %s active and %d %s withdrawn." % (num_active, "is" if num_active == 1 else "are", len(players) - num_active, "has" if len(players) - num_active == 1 else "have"))
        else:
            response.writeln("none withdrawn.")
    response.writeln("</p>")

    if tourney.get_num_games() == 0:
        if players:
            cgicommon.show_info_box(response, """<p>
    Set the <a href="#tourneyprops">tourney properties</a> below, then you can
    optionally go to the
    <a href="/cgi-bin/checkin.py?tourney={tourneyname}">Player Check-In</a>
    page to mark people as present or withdrawn.
    </p><p>
    If you're happy with the player list, head to
    <a href="/cgi-bin/fixturegen.py?tourney={tourneyname}">Generate fixtures</a>
    to generate the first games. Once you've generated the first games, you won't
    be able to delete players, but you can always withdraw them, edit names and
    ratings, or add new players.</p>""".format(tourneyname=urllib.parse.quote_plus(tourney.get_name())))
        else:
            cgicommon.show_info_box(response, """
    <p>Welcome to your new tourney!</p>
    <p>First, enter or paste a list of player names into the text box below.</p>
    <p>Don't worry, this isn't final. For now, just include everyone you're
    expecting to play. You can add new players or withdraw existing players
    at any time.</p>""")

    if num_divisions > 1:
        response.writeln("<p>The players are distributed into <a href=\"divsetup.py?tourney=%s\">%d divisions</a>.</p>" % (urllib.parse.quote_plus(tourney.get_name()), num_divisions))
        response.writeln("<blockquote>")
        for div_index in range(num_divisions):
            response.writeln("<li>%s: %d active players.</li>" % (tourney.get_division_name(div_index), tourney.get_num_active_players(div_index)))
        response.writeln("</blockquote>")

    if tourney.get_players():
        # Tourney properties. We'll only show these controls when the user has
        # entered some player names, but once we have player names, we'll show
        # these before the player list so that the user sees they're there.
        response.writeln("<hr />")
        response.writeln("<h2 id=\"tourneyprops\">Tourney properties</h2>");
        response.writeln(('<form action="%s?tourney=%s" method="post">' % (baseurl, urllib.parse.quote_plus(tourneyname))));
        response.writeln(('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True)));

        response.writeln("<h3>Event details</h3>")
        response.writeln("<p>These details will appear at the top of exported tournament reports, on the public-facing welcome screen, and on the event's webpage if you use the broadcast feature.</p>")

        response.writeln("<div class=\"generalsetupcontrolgroup generalsetuptourneydetails\">")
        response.writeln("<div class=\"generalsetuptourneydetailslabel\"><label for=\"fullname\">Event name </label></div><div class=\"generalsetuptourneydetailsbox\"><input type=\"text\" name=\"fullname\" value=\"%s\" id=\"fullname\" /></div>" % (cgicommon.escape(tourney.get_full_name(), True)))

        response.writeln("<span class=\"generalsetupinputexample\">(e.g. \"CoTrod %d\")</span>" % (time.localtime().tm_year))
        response.writeln("</div>")
        response.writeln("<div class=\"generalsetupcontrolgroup generalsetuptourneydetails\">")
        response.writeln("<div class=\"generalsetuptourneydetailslabel\"><label for=\"venue\">Venue</label></div><div class=\"generalsetuptourneydetailsbox\"><input type=\"text\" name=\"venue\" value=\"%s\" id=\"venue\" /></div>" % (cgicommon.escape(tourney.get_venue(), True)))
        response.writeln("<span class=\"generalsetupinputexample\">(e.g. \"St Quinquangle's Village Hall, Trodmore\")</span>")
        response.writeln("</div>")
        response.writeln("<div class=\"generalsetupcontrolgroup generalsetuptourneydetails\">")
        response.writeln("<div class=\"generalsetuptourneydetailslabel\"><label for=\"dateyear\">Event date</label></div><div class=\"generalsetuptourneydetailsbox\">")

        (date_year, date_month, date_day) = tourney.get_event_date()
        if date_year:
            year_str = str(date_year)
        else:
            year_str = ""
        if date_month:
            month_str = str(date_month)
        else:
            month_str = ""
        if date_day:
            day_str = str(date_day)
        else:
            day_str = ""
        response.writeln("<input type=\"number\" name=\"dateyear\" value=\"%s\" id=\"dateyear\" placeholder=\"YYYY\" min=\"0\" max=\"9999\" style=\"width: 5em;\" /> -" % (cgicommon.escape(year_str)))
        response.writeln("<input type=\"number\" name=\"datemonth\" value=\"%s\" id=\"datemonth\" placeholder=\"MM\" min=\"1\" max=\"12\" style=\"width: 3em;\" /> -" % (cgicommon.escape(month_str)))
        response.writeln("<input type=\"number\" name=\"dateday\" value=\"%s\" id=\"dateday\" placeholder=\"DD\" min=\"1\" max=\"31\" style=\"width: 3em;\" />" % (cgicommon.escape(day_str)))

        response.writeln("<button type=\"button\" onclick=\"setDateToday();\" style=\"margin-left: 10px;\">Today</button>");
        response.writeln("</div>") #generalsetuptourneydetailsbox
        response.writeln("</div>") #generalsetupcontrolgroup

        (table_list, accessible_default) = tourney.get_accessible_tables()
        response.writeln("<h3>Accessibility</h3>")
        response.writeln("<p>If a player requires an accessible table, you can set this on the <a href=\"/cgi-bin/player.py?tourney=%s\">configuration page for that player</a>.</p>" % (urllib.parse.quote_plus(tourney.get_name())))
        response.writeln("<div class=\"generalsetupcontrolgroup\">")
        response.writeln("<span style=\"padding-right: 10px;\">Table numbers</span> <input type=\"text\" name=\"accessibletables\" value=\"%s\" />" % (", ".join([ str(x) for x in table_list ])))
        response.writeln(" <span style=\"color: #808080; font-size: 10pt\">(Enter table numbers separated by commas, e.g. <span class=\"fixedwidth\">1,2,5</span>)</span>")
        response.writeln("</div>")
        response.writeln("<div class=\"generalsetupcontrolgroup\">")
        response.writeln("<input type=\"radio\" name=\"accessibletablesdefault\" value=\"0\" id=\"accessibletablesdefault_0\" %s /><label for=\"accessibletablesdefault_0\"> The above table numbers are the accessible tables.</label>" % ("" if accessible_default else "checked"))
        response.writeln("<br />")
        response.writeln("<input type=\"radio\" name=\"accessibletablesdefault\" value=\"1\" id=\"accessibletablesdefault_1\" %s /><label for=\"accessibletablesdefault_1\"> All tables are accessible <em>except</em> for the table numbers listed above.</label>" % ("checked" if accessible_default else ""))
        response.writeln("</div>")

        response.writeln("<h3>Intended number of rounds, and qualification</h3>")
        response.writeln("<p>")
        response.writeln("If you fill in these values, Atropine will automatically work out when a player is guaranteed to finish in the qualification zone, and highlight them in green in the standings table.")
        response.writeln("If you don't fill these in, or if you set them to zero, Atropine won't do that.")
        response.writeln("</p>")

        for div_index in range(num_divisions):
            if num_divisions > 1:
                response.writeln("<h4>%s</h4>" % (cgicommon.escape(tourney.get_division_name(div_index))))
            div_prefix = "div%d_" % (div_index)

            last_round = str(tourney.get_attribute(div_prefix + "lastround", ""))
            if last_round == "0":
                last_round = ""

            num_games_per_player = str(tourney.get_attribute(div_prefix + "numgamesperplayer", ""))
            if num_games_per_player == "0":
                num_games_per_player = ""

            qual_places = str(tourney.get_attribute(div_prefix + "qualplaces", ""))
            if qual_places == "0":
                qual_places = ""

            response.writeln("<div class=\"tourneyqualifyingcontrols\">")
            response.writeln("The last round is expected to be round number <input class=\"tourneysetupnumber\" type=\"number\" name=\"%slastround\" value=\"%s\" />" % (div_prefix, cgicommon.escape(last_round, True)))
            response.writeln("</div>")
            response.writeln("<div class=\"tourneyqualifyingcontrols\">")
            response.writeln("Each player is expected to play <input class=\"tourneysetupnumber\" type=\"number\" name=\"%snumgamesperplayer\" value=\"%s\" /> games" % (div_prefix, cgicommon.escape(num_games_per_player, True)))
            response.writeln("</div>")
            response.writeln("<div class=\"tourneyqualifyingcontrols\">")
            response.writeln("The qualification zone is the top <input class=\"tourneysetupnumber\" type=\"number\" name=\"%squalplaces\" value=\"%s\" /> places in the standings table" % (div_prefix, cgicommon.escape(qual_places, True)))
            response.writeln("</div>")
        response.writeln("<div class=\"generalsetupcontrolgroup\">")
        response.writeln(("<input type=\"checkbox\" name=\"showdrawscolumn\" id=\"showdrawscolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_draws_column() else "")))
        response.writeln("<label for=\"showdrawscolumn\">Draws are possible</label>")
        response.writeln("</div>")

        response.writeln('<div class="rulessubmit"><input type="submit" class="bigbutton" name="rulessubmit" value="Save Changes" /></div>')
        response.writeln("</form>");

        if tourney.get_num_games() > 0:
            response.writeln("<hr />")
            response.writeln('<h2>Delete rounds</h2>')
            response.writeln('<p>Press this button to delete the most recent round. You\'ll be asked to confirm on the next screen.</p>')
            response.writeln('<form action="/cgi-bin/delround.py" method="get">')
            response.writeln(('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname)))
            response.writeln('<input type="submit" class="bigbutton" name="delroundsetupsubmit" value="Delete most recent round" />')
            response.writeln('</form>')

    # Display the player list, and let the user resubmit it, only if there
    # haven't been any games generated yet.
    if tourney.get_num_games() == 0:
        players = sorted(tourney.get_players(), key=lambda x : (x.get_division(), x.get_id()))
        response.writeln("<hr />")
        response.writeln("<h2>Ratings setup</h2>");

        response.writeln(("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname))))

        response.writeln("<p>")
        response.writeln("How do you want to assign ratings to players? Ratings are used by the Overachievers table and some fixture generators. If you don't know what ratings are, or you don't care, select \"This tournament is not seeded\".")
        response.writeln("</p>")
        response.writeln("<blockquote>")
        auto_rating_behaviour = tourney.get_auto_rating_behaviour()
        response.writeln(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" id=\"autoratingbehaviourmanual\" %s />" % (countdowntourney.RATINGS_MANUAL, countdowntourney.RATINGS_MANUAL, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_MANUAL else "")))
        response.writeln("<label for=\"autoratingbehaviourmanual\"><strong>Ratings are specified manually in the player list.</strong></label> If you select this option, it is an error if you try to submit a player without a rating.")
        response.writeln("<br />")

        response.writeln(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" id=\"autoratingbehaviourgraduated\" %s />" % (countdowntourney.RATINGS_GRADUATED, countdowntourney.RATINGS_GRADUATED, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_GRADUATED else "")))
        response.writeln("<label for=\"autoratingbehaviourgraduated\"><strong>The player list is in rating order with the highest-rated player at the top.</strong></label>")
        response.writeln("Ratings will be assigned automatically, with the player at the top of the list receiving a rating of 2000, and the player at the bottom 1000. If you select this option, it is an error to specify any ratings manually in the player list.")
        response.writeln("<br />")

        response.writeln(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" id=\"autoratingbehaviouruniform\" %s />" % (countdowntourney.RATINGS_UNIFORM, countdowntourney.RATINGS_UNIFORM, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_UNIFORM else "")))
        response.writeln("<label for=\"autoratingbehaviouruniform\"><strong>This tournament is not seeded.</strong></label>")
        response.writeln("Assign every player a rating of 1000. If you select this option, it is an error to specify any ratings manually in the player list. If unsure, select this option.")
        response.writeln("</blockquote>")

        response.writeln("<p>")
        response.writeln("A player's rating may still be changed after the tournament has started.")
        response.writeln("</p>")

        response.writeln("<h2>Player list</h2>");
        response.writeln("<p>")
        response.writeln("Enter player names in this box, one player per line, then click <em>Save Player List</em>.")
        response.writeln("</p>")

        response.writeln("<div class=\"playerlist\">")
        response.writeln("<div class=\"playerlistpane\">")
        response.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname));
        response.writeln('<textarea rows="30" cols="40" name="playerlist" id="playerlist" oninput="textAreaChange();">');
        if request_method == "POST" and playerlist:
            # If the user has submitted something, display what the user
            # submitted rather than what's in the database - this gives them
            # a chance to correct any errors without typing in the whole
            # change again.
            response.write(cgicommon.escape(playerlist).strip())
        else:
            string_stream = io.StringIO()
            auto_rating = tourney.get_auto_rating_behaviour()
            writer = csv.writer(string_stream);
            prev_div_index = 0
            # Write player names, or player names and ratings if the user
            # specified the players' ratings.
            for p in players:
                div_index = p.get_division()
                if div_index != prev_div_index:
                    writer.writerow(("-",))
                row = []
                row.append(cgicommon.escape(p.get_name()))
                if auto_rating == countdowntourney.RATINGS_MANUAL or p.is_prune():
                    row.append("%g" % (p.get_rating()))
                if p.get_team_id() is not None:
                    row.append("T%d" % (p.get_team_id()))
                if p.is_newbie():
                    row.append("N")
                if p.is_requiring_accessible_table():
                    row.append("A")
                if p.get_preferred_table() is not None:
                    row.append("P%d" % (p.get_preferred_table()))
                if p.is_withdrawn():
                    row.append("W")
                if p.is_avoiding_prune():
                    row.append("NP")
                writer.writerow(tuple(row))
                prev_div_index = div_index
            response.write(string_stream.getvalue())
        response.writeln("</textarea>");

        response.writeln("<div class=\"playerlistclear\"></div>")
        response.writeln("<div class=\"playerlistsubmitpanel\">")
        response.writeln("<div class=\"playerlistsubmitdiv\">")
        response.writeln('<input type="submit" class="bigbutton" name="playerlistsubmit" id="playerlistsubmit" value="Save Player List" />')
        response.writeln("</div>")
        response.writeln("<div class=\"playerlistsummarydiv\" id=\"playerlistsummary\"></div>")
        response.writeln("</div>")
        response.writeln("</div>")

        response.writeln("<div class=\"playerlisthelp\">")
        response.writeln("<h3>Example</h3>")
        response.writeln("<pre id=\"playerlistexamplepre\">")
        if auto_rating_behaviour == countdowntourney.RATINGS_UNIFORM:
            response.writeln(player_list_example_uniform)
        elif auto_rating_behaviour == countdowntourney.RATINGS_GRADUATED:
            response.writeln(player_list_example_graduated)
        else:
            response.writeln(player_list_example_manual)
        response.writeln("</pre>")
        response.writeln("<p id=\"playerlistratinghelp\">")
        if auto_rating_behaviour == countdowntourney.RATINGS_MANUAL:
            response.writeln(player_list_rating_help);
        response.writeln("</p>")

        if tourney.has_auto_prune():
            response.writeln("<p id=\"prunewarning\">")
            response.writeln("The number of players does not need to be a multiple of the desired group size. It is no longer necessary for you to add Prune players. Fixture generators will introduce them automatically if required.")
            response.writeln("</p>")

        response.writeln("<p>")
        response.writeln("To split the players into divisions, put a line containing only a dash (<span class=\"fixedwidth\">-</span>) between the desired divisions.")
        response.writeln("</p>")

        response.writeln("<div id=\"playerlistextrahelp\">")
        response.writeln("<h3>Help</h3>")
        response.writeln("<p>")
        response.writeln("You can add extra fields after the player's name, separated by commas, to specify more information about the player, as follows:")
        response.writeln("</p>")
        response.writeln("<table>")
        response.writeln("<tr><td><em>(number)</em></td><td>The player's rating.</td></tr>")
        response.writeln("<tr><td><span class=\"fixedwidth\">A</span></td><td>Player requires an accessible table.</td></tr>")
        response.writeln("<tr><td><span class=\"fixedwidth\">N</span></td><td>Player is a newbie.</td></tr>")
        response.writeln("<tr><td><span class=\"fixedwidth\">NP</span></td><td>Player will avoid playing Prune.</td></tr>")
        response.writeln("<tr><td><span class=\"fixedwidth\">P</span><span style=\"font-style: italic;\">n</span></td><td>Player would prefer to be on table number <span style=\"font-style: italic;\">n</span>.</td></tr>")
        response.writeln("<tr><td><span class=\"fixedwidth\">W</span></td><td>Player is withdrawn.</td></tr>")
        response.writeln("</table>")
        response.writeln("<p>")
        response.writeln("For example, the line:")
        response.writeln("</p>")
        response.writeln("<pre>")
        response.writeln("Spangly Fizzbox,A,NP")
        response.writeln("</pre>")
        response.writeln("<p>")
        response.writeln("means that Spangly Fizzbox requires an accessible table and is to avoid playing Prune.")
        response.writeln("</p>")
        response.writeln("<p>A player's newbie status can be used by fixture generators to put at least one non-newbie on each table.</p>")
        response.writeln("<p>")
        response.writeln("You can always change these settings later on the <a href=\"/cgi-bin/player.py?tourney=%s\">Player Setup</a> page." % (urllib.parse.quote_plus(tourney.get_name())));
        response.writeln("</p>")
        response.writeln("</div>") #playerlistextrahelp

        response.writeln("<a id=\"playerlistextrahelpshow\" onclick=\"playerListExtraHelpShow();\" class=\"fakelink\">Show less</a>");

        response.writeln("</div>")
        response.writeln("</div>")
        response.writeln("</form>")
        response.writeln("<div class=\"playerlistclear\"></div>")

    response.writeln("</div>");

    response.writeln("</body>");
    response.writeln("</html>");
