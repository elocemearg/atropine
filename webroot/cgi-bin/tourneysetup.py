#!/usr/bin/python3

import cgi;
import cgitb;
import cgicommon;
import sys;
import csv;
import os;
import json
import io
import time
import urllib.request, urllib.parse, urllib.error;

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

def show_player_drop_down_box(players, control_name):
    cgicommon.writeln("<select name=\"%s\">" % (control_name))
    cgicommon.writeln("<option value=\"\">-- select player --</option>")
    for p in players:
        cgicommon.writeln("<option value=\"%s\">%s (%g)</option>" % (cgicommon.escape(p.name, True), cgicommon.escape(p.name), p.rating));
    cgicommon.writeln("</select>")

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

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/tourneysetup.py";
form = cgi.FieldStorage();
tourneyname = form.getfirst("tourney");
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

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.print_html_head("Tourney Setup: " + str(tourneyname));

cgicommon.writeln("<body onload=\"textAreaChange(); playerListExtraHelpShow();\">");

cgicommon.writeln("<script>")
cgicommon.writeln("""
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
    cgicommon.writeln("""
        case %d:
            element.innerText = %s;
            break;
    """ % (num, json.dumps(text)))

cgicommon.writeln("""
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

cgicommon.assert_client_from_localhost()

if tourneyname is not None:
    try:
        tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir);
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);
        cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>")
        cgicommon.writeln("</body></html>")
        sys.exit(1)

if tourneyname is None:
    cgicommon.writeln("<h1>Sloblock</h1>");
    cgicommon.writeln("<p>No tourney name specified. <a href=\"/cgi-bin/home.py\">Home</a></p>");
    cgicommon.writeln("</body></html>")
    sys.exit(1)
elif not tourney:
    cgicommon.writeln("<p>No valid tourney name specified</p>");
    cgicommon.writeln("</body></html>")
    sys.exit(1)

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
                player_requires_accessible_table, player_table_pref))
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
# enough that we can now show the sidebar and open the main div. It's important
# we handle the player list submission before showing the sidebar, because the
# sidebar won't show most things until there are players submitted.

cgicommon.show_sidebar(tourney);

cgicommon.writeln("<div class=\"mainpane\">");
cgicommon.writeln("<h1>Tourney Setup</h1>");

if show_success_box:
    cgicommon.show_success_box(show_success_box)
if show_exception:
    cgicommon.show_tourney_exception(show_exception);

players = tourney.get_players();
players = sorted(players, key=lambda x : x.name);

cgicommon.writeln("<p>")
if tourney.get_num_games() > 0:
    cgicommon.writeln("The tournament has started.")
if len(players) == 0:
    cgicommon.writeln("This isn't much of a tourney yet. It hasn't got any players.")
else:
    cgicommon.writeln("There are <a href=\"player.py?tourney=%s\">%d players</a>," % (urllib.parse.quote_plus(tourney.get_name()), len(players)))
    num_active = len([x for x in players if not x.is_withdrawn()])
    if num_active != len(players):
        cgicommon.writeln("of whom %d %s active and %d %s withdrawn." % (num_active, "is" if num_active == 1 else "are", len(players) - num_active, "has" if len(players) - num_active == 1 else "have"))
    else:
        cgicommon.writeln("none withdrawn.")
cgicommon.writeln("</p>")

if tourney.get_num_games() == 0:
    if players:
        cgicommon.show_info_box("""<p>
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
        cgicommon.show_info_box("""
<p>First, enter or paste a list of player names into the text box below.</p>
<p>Don't worry, this isn't final. For now, just include everyone you're
expecting to play. You can add new players or withdraw existing players
at any time.</p>""")

if num_divisions > 1:
    cgicommon.writeln("<p>The players are distributed into <a href=\"divsetup.py?tourney=%s\">%d divisions</a>.</p>" % (urllib.parse.quote_plus(tourney.get_name()), num_divisions))
    cgicommon.writeln("<blockquote>")
    for div_index in range(num_divisions):
        cgicommon.writeln("<li>%s: %d active players.</li>" % (tourney.get_division_name(div_index), tourney.get_num_active_players(div_index)))
    cgicommon.writeln("</blockquote>")

if tourney.get_players():
    # Tourney properties. We'll only show these controls when the user has
    # entered some player names, but once we have player names, we'll show
    # these before the player list so that the user sees they're there.
    cgicommon.writeln("<hr />")
    cgicommon.writeln("<h2 id=\"tourneyprops\">Tourney properties</h2>");
    cgicommon.writeln(('<form action="%s?tourney=%s" method="post">' % (baseurl, urllib.parse.quote_plus(tourneyname))));
    cgicommon.writeln(('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname, True)));

    cgicommon.writeln("<h3>Event details</h3>")
    cgicommon.writeln("<p>These details will appear at the top of exported tournament reports, on the public-facing welcome screen, and on the event's webpage if you use the broadcast feature.</p>")

    cgicommon.writeln("<div class=\"generalsetupcontrolgroup generalsetuptourneydetails\">")
    cgicommon.writeln("<div class=\"generalsetuptourneydetailslabel\"><label for=\"fullname\">Event name </label></div><div class=\"generalsetuptourneydetailsbox\"><input type=\"text\" name=\"fullname\" value=\"%s\" id=\"fullname\" /></div>" % (cgicommon.escape(tourney.get_full_name(), True)))

    cgicommon.writeln("<span class=\"generalsetupinputexample\">(e.g. \"CoTrod %d\")</span>" % (time.localtime().tm_year))
    cgicommon.writeln("</div>")
    cgicommon.writeln("<div class=\"generalsetupcontrolgroup generalsetuptourneydetails\">")
    cgicommon.writeln("<div class=\"generalsetuptourneydetailslabel\"><label for=\"venue\">Venue</label></div><div class=\"generalsetuptourneydetailsbox\"><input type=\"text\" name=\"venue\" value=\"%s\" id=\"venue\" /></div>" % (cgicommon.escape(tourney.get_venue(), True)))
    cgicommon.writeln("<span class=\"generalsetupinputexample\">(e.g. \"St Quinquangle's Village Hall, Trodmore\")</span>")
    cgicommon.writeln("</div>")
    cgicommon.writeln("<div class=\"generalsetupcontrolgroup generalsetuptourneydetails\">")
    cgicommon.writeln("<div class=\"generalsetuptourneydetailslabel\"><label for=\"dateyear\">Event date</label></div><div class=\"generalsetuptourneydetailsbox\">")

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
    cgicommon.writeln("<input type=\"number\" name=\"dateyear\" value=\"%s\" id=\"dateyear\" placeholder=\"YYYY\" min=\"0\" max=\"9999\" style=\"width: 5em;\" /> -" % (cgicommon.escape(year_str)))
    cgicommon.writeln("<input type=\"number\" name=\"datemonth\" value=\"%s\" id=\"datemonth\" placeholder=\"MM\" min=\"1\" max=\"12\" style=\"width: 3em;\" /> -" % (cgicommon.escape(month_str)))
    cgicommon.writeln("<input type=\"number\" name=\"dateday\" value=\"%s\" id=\"dateday\" placeholder=\"DD\" min=\"1\" max=\"31\" style=\"width: 3em;\" />" % (cgicommon.escape(day_str)))

    cgicommon.writeln("<button type=\"button\" onclick=\"setDateToday();\" style=\"margin-left: 10px;\">Today</button>");
    cgicommon.writeln("</div>") #generalsetuptourneydetailsbox
    cgicommon.writeln("</div>") #generalsetupcontrolgroup

    (table_list, accessible_default) = tourney.get_accessible_tables()
    cgicommon.writeln("<h3>Accessibility</h3>")
    cgicommon.writeln("<p>If a player requires an accessible table, you can set this on the <a href=\"/cgi-bin/player.py?tourney=%s\">configuration page for that player</a>.</p>" % (urllib.parse.quote_plus(tourney.get_name())))
    cgicommon.writeln("<div class=\"generalsetupcontrolgroup\">")
    cgicommon.writeln("<span style=\"padding-right: 10px;\">Table numbers</span> <input type=\"text\" name=\"accessibletables\" value=\"%s\" />" % (", ".join([ str(x) for x in table_list ])))
    cgicommon.writeln(" <span style=\"color: #808080; font-size: 10pt\">(Enter table numbers separated by commas, e.g. <span class=\"fixedwidth\">1,2,5</span>)</span>")
    cgicommon.writeln("</div>")
    cgicommon.writeln("<div class=\"generalsetupcontrolgroup\">")
    cgicommon.writeln("<input type=\"radio\" name=\"accessibletablesdefault\" value=\"0\" id=\"accessibletablesdefault_0\" %s /><label for=\"accessibletablesdefault_0\"> The above table numbers are the accessible tables.</label>" % ("" if accessible_default else "checked"))
    cgicommon.writeln("<br />")
    cgicommon.writeln("<input type=\"radio\" name=\"accessibletablesdefault\" value=\"1\" id=\"accessibletablesdefault_1\" %s /><label for=\"accessibletablesdefault_1\"> All tables are accessible <em>except</em> for the table numbers listed above.</label>" % ("checked" if accessible_default else ""))
    cgicommon.writeln("</div>")

    cgicommon.writeln("<h3>Intended number of rounds, and qualification</h3>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("If you fill in these values, Atropine will automatically work out when a player is guaranteed to finish in the qualification zone, and highlight them in green in the standings table.")
    cgicommon.writeln("If you don't fill these in, or if you set them to zero, Atropine won't do that.")
    cgicommon.writeln("</p>")

    for div_index in range(num_divisions):
        if num_divisions > 1:
            cgicommon.writeln("<h4>%s</h4>" % (cgicommon.escape(tourney.get_division_name(div_index))))
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

        cgicommon.writeln("<div class=\"tourneyqualifyingcontrols\">")
        cgicommon.writeln("The last round is expected to be round number <input class=\"tourneysetupnumber\" type=\"number\" name=\"%slastround\" value=\"%s\" />" % (div_prefix, cgicommon.escape(last_round, True)))
        cgicommon.writeln("</div>")
        cgicommon.writeln("<div class=\"tourneyqualifyingcontrols\">")
        cgicommon.writeln("Each player is expected to play <input class=\"tourneysetupnumber\" type=\"number\" name=\"%snumgamesperplayer\" value=\"%s\" /> games" % (div_prefix, cgicommon.escape(num_games_per_player, True)))
        cgicommon.writeln("</div>")
        cgicommon.writeln("<div class=\"tourneyqualifyingcontrols\">")
        cgicommon.writeln("The qualification zone is the top <input class=\"tourneysetupnumber\" type=\"number\" name=\"%squalplaces\" value=\"%s\" /> places in the standings table" % (div_prefix, cgicommon.escape(qual_places, True)))
        cgicommon.writeln("</div>")
    cgicommon.writeln("<div class=\"generalsetupcontrolgroup\">")
    cgicommon.writeln(("<input type=\"checkbox\" name=\"showdrawscolumn\" id=\"showdrawscolumn\" value=\"1\" %s />" % ("checked" if tourney.get_show_draws_column() else "")))
    cgicommon.writeln("<label for=\"showdrawscolumn\">Draws are possible</label>")
    cgicommon.writeln("</div>")

    cgicommon.writeln('<div class="rulessubmit"><input type="submit" class="bigbutton" name="rulessubmit" value="Save Changes" /></div>')
    cgicommon.writeln("</form>");

    if tourney.get_num_games() > 0:
        cgicommon.writeln("<hr />")
        cgicommon.writeln('<h2>Delete rounds</h2>')
        cgicommon.writeln('<p>Press this button to delete the most recent round. You\'ll be asked to confirm on the next screen.</p>')
        cgicommon.writeln('<form action="/cgi-bin/delround.py" method="get">')
        cgicommon.writeln(('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname)))
        cgicommon.writeln('<input type="submit" class="bigbutton" name="delroundsetupsubmit" value="Delete most recent round" />')
        cgicommon.writeln('</form>')

# Display the player list, and let the user resubmit it, only if there haven't
# been any games generated yet.
if tourney.get_num_games() == 0:
    players = sorted(tourney.get_players(), key=lambda x : (x.get_division(), x.get_id()))
    cgicommon.writeln("<hr />")
    cgicommon.writeln("<h2>Ratings setup</h2>");

    cgicommon.writeln(("<form action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourneyname))))

    cgicommon.writeln("<p>")
    cgicommon.writeln("How do you want to assign ratings to players? Ratings are used by the Overachievers table and some fixture generators. If you don't know what ratings are, or you don't care, select \"This tournament is not seeded\".")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<blockquote>")
    auto_rating_behaviour = tourney.get_auto_rating_behaviour()
    cgicommon.writeln(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" id=\"autoratingbehaviourmanual\" %s />" % (countdowntourney.RATINGS_MANUAL, countdowntourney.RATINGS_MANUAL, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_MANUAL else "")))
    cgicommon.writeln("<label for=\"autoratingbehaviourmanual\"><strong>Ratings are specified manually in the player list.</strong></label> If you select this option, it is an error if you try to submit a player without a rating.")
    cgicommon.writeln("<br />")

    cgicommon.writeln(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" id=\"autoratingbehaviourgraduated\" %s />" % (countdowntourney.RATINGS_GRADUATED, countdowntourney.RATINGS_GRADUATED, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_GRADUATED else "")))
    cgicommon.writeln("<label for=\"autoratingbehaviourgraduated\"><strong>The player list is in rating order with the highest-rated player at the top.</strong></label>")
    cgicommon.writeln("Ratings will be assigned automatically, with the player at the top of the list receiving a rating of 2000, and the player at the bottom 1000. If you select this option, it is an error to specify any ratings manually in the player list.")
    cgicommon.writeln("<br />")

    cgicommon.writeln(("<input type=\"radio\" name=\"autoratingbehaviour\" value=\"%d\" onclick=\"set_player_list_example(%d);\" id=\"autoratingbehaviouruniform\" %s />" % (countdowntourney.RATINGS_UNIFORM, countdowntourney.RATINGS_UNIFORM, "checked" if auto_rating_behaviour == countdowntourney.RATINGS_UNIFORM else "")))
    cgicommon.writeln("<label for=\"autoratingbehaviouruniform\"><strong>This tournament is not seeded.</strong></label>")
    cgicommon.writeln("Assign every player a rating of 1000. If you select this option, it is an error to specify any ratings manually in the player list. If unsure, select this option.")
    cgicommon.writeln("</blockquote>")

    cgicommon.writeln("<p>")
    cgicommon.writeln("A player's rating may still be changed after the tournament has started.")
    cgicommon.writeln("</p>")

    cgicommon.writeln("<h2>Player list</h2>");
    cgicommon.writeln("<p>")
    cgicommon.writeln("Enter player names in this box, one player per line, then click <em>Save Player List</em>.")
    cgicommon.writeln("</p>")

    cgicommon.writeln("<div class=\"playerlist\">")
    cgicommon.writeln("<div class=\"playerlistpane\">")
    cgicommon.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname));
    cgicommon.writeln('<textarea rows="30" cols="40" name="playerlist" id="playerlist" oninput="textAreaChange();">');
    if request_method == "POST" and playerlist:
        # If the user has submitted something, display what the user
        # submitted rather than what's in the database - this gives them
        # a chance to correct any errors without typing in the whole
        # change again.
        cgicommon.write(cgicommon.escape(playerlist).strip())
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
        cgicommon.write(string_stream.getvalue())
    cgicommon.writeln("</textarea>");

    cgicommon.writeln("<div class=\"playerlistclear\"></div>")
    cgicommon.writeln("<div class=\"playerlistsubmitpanel\">")
    cgicommon.writeln("<div class=\"playerlistsubmitdiv\">")
    cgicommon.writeln('<input type="submit" class="bigbutton" name="playerlistsubmit" id="playerlistsubmit" value="Save Player List" />')
    cgicommon.writeln("</div>")
    cgicommon.writeln("<div class=\"playerlistsummarydiv\" id=\"playerlistsummary\"></div>")
    cgicommon.writeln("</div>")
    cgicommon.writeln("</div>")

    cgicommon.writeln("<div class=\"playerlisthelp\">")
    cgicommon.writeln("<h3>Example</h3>")
    cgicommon.writeln("<pre id=\"playerlistexamplepre\">")
    if auto_rating_behaviour == countdowntourney.RATINGS_UNIFORM:
        cgicommon.writeln(player_list_example_uniform)
    elif auto_rating_behaviour == countdowntourney.RATINGS_GRADUATED:
        cgicommon.writeln(player_list_example_graduated)
    else:
        cgicommon.writeln(player_list_example_manual)
    cgicommon.writeln("</pre>")
    cgicommon.writeln("<p id=\"playerlistratinghelp\">")
    if auto_rating_behaviour == countdowntourney.RATINGS_MANUAL:
        cgicommon.writeln(player_list_rating_help);
    cgicommon.writeln("</p>")

    if tourney.has_auto_prune():
        cgicommon.writeln("<p id=\"prunewarning\">")
        cgicommon.writeln("The number of players does not need to be a multiple of the desired group size. It is no longer necessary for you to add Prune players. Fixture generators will introduce them automatically if required.")
        cgicommon.writeln("</p>")

    cgicommon.writeln("<p>")
    cgicommon.writeln("To split the players into divisions, put a line containing only a dash (<span class=\"fixedwidth\">-</span>) between the desired divisions.")
    cgicommon.writeln("</p>")

    cgicommon.writeln("<div id=\"playerlistextrahelp\">")
    cgicommon.writeln("<h3>Help</h3>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("You can add extra fields after the player's name, separated by commas, to specify more information about the player, as follows:")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<table>")
    cgicommon.writeln("<tr><td><em>(number)</em></td><td>The player's rating.</td></tr>")
    cgicommon.writeln("<tr><td><span class=\"fixedwidth\">A</span></td><td>Player requires an accessible table.</td></tr>")
    cgicommon.writeln("<tr><td><span class=\"fixedwidth\">NP</span></td><td>Player will avoid playing Prune.</td></tr>")
    cgicommon.writeln("<tr><td><span class=\"fixedwidth\">P</span><span style=\"font-style: italic;\">n</span></td><td>Player would prefer to be on table number <span style=\"font-style: italic;\">n</span>.</td></tr>")
    cgicommon.writeln("<tr><td><span class=\"fixedwidth\">W</span></td><td>Player is withdrawn.</td></tr>")
    cgicommon.writeln("</table>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("For example, the line:")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<pre>")
    cgicommon.writeln("Spangly Fizzbox,A,NP")
    cgicommon.writeln("</pre>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("means that Spangly Fizzbox requires an accessible table and is to avoid playing Prune.")
    cgicommon.writeln("</p>")
    cgicommon.writeln("<p>")
    cgicommon.writeln("You can always change these settings later on the <a href=\"/cgi-bin/player.py?tourney=%s\">Player Setup</a> page." % (urllib.parse.quote_plus(tourney.get_name())));
    cgicommon.writeln("</p>")
    cgicommon.writeln("</div>") #playerlistextrahelp

    cgicommon.writeln("<a id=\"playerlistextrahelpshow\" onclick=\"playerListExtraHelpShow();\" class=\"fakelink\">Show less</a>");

    cgicommon.writeln("</div>")
    cgicommon.writeln("</div>")
    cgicommon.writeln("</form>")
    cgicommon.writeln("<div class=\"playerlistclear\"></div>")

cgicommon.writeln("</div>");

cgicommon.writeln("</body>");
cgicommon.writeln("</html>");
