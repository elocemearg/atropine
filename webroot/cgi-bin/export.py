#!/usr/bin/python3

import sys
import cgicommon
import urllib.request, urllib.parse, urllib.error
import cgi
import cgitb
import datetime
import calendar
import csv

def int_or_none(s):
    try:
        i = int(s)
        return i
    except:
        return None

def valid_date(d, m, y):
    try:
        datetime.datetime.strptime("%04d-%02d-%02d" % (y, m, d), "%Y-%m-%d")
        return True
    except ValueError:
        return False

def show_error(err_str):
    cgicommon.writeln("Content-Type: text/html; charset=utf-8");
    cgicommon.writeln("");
    cgicommon.print_html_head("Tourney: %s" % tourney_name);

    cgicommon.writeln("<body>");

    cgicommon.show_sidebar(tourney);

    cgicommon.writeln("<div class=\"mainpane\">")
    cgicommon.writeln("<p><strong>%s</strong></p>" % err_str)
    cgicommon.writeln("</div>")
    cgicommon.writeln("</body>")
    cgicommon.writeln("</html>")

form_letter_to_word = {
        "W" : "won",
        "D" : "drew",
        "L" : "lost"
}

cgitb.enable();

baseurl = "/cgi-bin/export.py"
started_html = False;
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");
export_format = form.getfirst("format");
wikitext_date_d = form.getfirst("wikitextday");
wikitext_date_m = form.getfirst("wikitextmonth");
wikitext_date_y = form.getfirst("wikitextyear");
wikitext_game_prefix = form.getfirst("wikitextgameprefix")
wikitext_submit = form.getfirst("wikitextsubmit")

csv_submit_download = form.getfirst("csvsubmitdownload")
csv_submit_view = form.getfirst("csvsubmitview")
csv_event_code = form.getfirst("csveventcode")
csv_game_format = form.getfirst("csvgameformat")
csv_type = form.getfirst("csvtype")

tourney = None;

cgicommon.set_module_path();

if csv_event_code is None:
    csv_event_code = ""
if csv_game_format is None:
    csv_game_format = ""

import countdowntourney;

if tourney_name is None:
    show_error("No tourney specified");
    sys.exit(0);

if export_format is None:
    # No format specified: display a list of possible formats to choose from
    cgicommon.writeln("Content-Type: text/html; charset=utf-8")
    cgicommon.writeln("")
    started_html = True;
    cgicommon.print_html_head("Tournament report: " + str(tourney_name))

    cgicommon.writeln("<body>")

    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)

    cgicommon.show_sidebar(tourney)

    cgicommon.writeln("<div class=\"mainpane\">")

    html = """<h1>Choose export format</h1>
<p>
How do you want to export results?
</p>
<p>
<a href="$BASEURL?tourney=$TOURNEY&format=html" target="_blank">HTML $NEWWINDOW</a> - a single HTML page containing standings and results.
</p>
<p>
<a href="$BASEURL?tourney=$TOURNEY&format=text" target="_blank">Text $NEWWINDOW</a> - a plain text document containing standings and results.
</p>
<p>
<a href="$BASEURL?tourney=$TOURNEY&format=csv" target="_blank">CSV $NEWWINDOW</a> - a CSV file containing either the results of games or the standings.
</p>
<p>
<a href="$BASEURL?tourney=$TOURNEY&format=wikitext" target="_blank">Wikitext $NEWWINDOW</a> - Standings and results as Wikitext, suitable for copy-pasting to the wiki.
</p>"""
    html = html.replace("$BASEURL", baseurl).replace("$TOURNEY", urllib.parse.quote_plus(tourney_name))
    html = html.replace("$NEWWINDOW", "<img src=\"/images/opensinnewwindow.png\" alt=\"Opens in new window\" title=\"Opens in new window\" />")

    cgicommon.writeln(html)

    cgicommon.writeln("</div>") #mainpane

    cgicommon.writeln("</body>")
    cgicommon.writeln("</html>")

    # And exit here
    sys.exit(0)

# If the user has asked for wikitext, prompt the user for the date of the
# tournament and the prefix for any individual game articles.
if export_format == "wikitext":
    errors = []
    if wikitext_submit:
        # Check that what the user has put in the form makes sense, and if it
        # doesn't, ask them to try again
        wikitext_date_d = int_or_none(wikitext_date_d)
        wikitext_date_m = int_or_none(wikitext_date_m)
        wikitext_date_y = int_or_none(wikitext_date_y)
        if wikitext_date_d is None or wikitext_date_m is None or wikitext_date_y is None or not valid_date(wikitext_date_d, wikitext_date_m, wikitext_date_y):
            errors.append("That date is not valid.")

    if errors or wikitext_submit is None:
        cgicommon.writeln("Content-Type: text/html; charset=utf-8")
        cgicommon.writeln("")
        started_html = True

        cgicommon.print_html_head("Tournament report - Wikitext")

        tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
        cgicommon.writeln("<body>")
        cgicommon.show_sidebar(tourney)

        # Default value for date is the tourney's event date. If that's not
        # set then the default is today. Default value for game prefix is the
        # tourney name, upcased, with all non-letter and non-digit characters
        # removed, and with a dot on the end if it ends with a digit.
        if wikitext_submit is None:
            (year, month, day) = tourney.get_event_date()
            if year and month and day:
                wikitext_date_d = day
                wikitext_date_m = month
                wikitext_date_y = year
            else:
                today = datetime.date.today()
                wikitext_date_d = today.day
                wikitext_date_m = today.month
                wikitext_date_y = today.year

            wikitext_game_prefix = ""
            for c in tourney_name.upper():
                if c.isupper() or c.isdigit():
                    wikitext_game_prefix += c
            if wikitext_game_prefix[-1].isdigit():
                wikitext_game_prefix += "."

        cgicommon.writeln("<div class=\"mainpane\">")
        cgicommon.writeln("<h1>Tournament report - Wikitext</h1>")
        if errors:
            cgicommon.writeln("<h2>Failed to generate wikitext...</h2>")
            cgicommon.writeln("<blockquote>")
            for txt in errors:
                cgicommon.writeln("<li>%s</li>" % (cgicommon.escape(txt)))
            cgicommon.writeln("</blockquote>")

        cgicommon.writeln("<p>")
        cgicommon.writeln("Select the date the tournament was played, and a string to prefix each game ID. Then generate the wikitext for copy-pasting into a new wiki page.")
        cgicommon.writeln("</p>")
        cgicommon.writeln("<form method=\"GET\" action=\"/cgi-bin/export.py\">")
        cgicommon.writeln("<table>")
        cgicommon.writeln("<tr><td>Day</td><td>Month</td><td>Year</td></tr>")
        cgicommon.writeln("<tr>")
        cgicommon.writeln("<td><input type=\"number\" name=\"wikitextday\" value=\"%d\" min=\"1\" max=\"31\" size=\"2\" /></td>" % (wikitext_date_d))
        cgicommon.writeln("<td>")
        cgicommon.writeln("<select name=\"wikitextmonth\">")
        for m in range(1, 13):
            cgicommon.writeln("<option value=\"%d\" %s>%s</option>" % (m, "selected " if m == wikitext_date_m else "", cgicommon.escape(calendar.month_name[m])))
        cgicommon.writeln("</select>")
        cgicommon.writeln("</td>")
        cgicommon.writeln("<td><input type=\"number\" name=\"wikitextyear\" value=\"%d\" min=\"0\" max=\"9999\" size=\"4\" /></td>" % (wikitext_date_y))
        cgicommon.writeln("</tr></table>")
        cgicommon.writeln("<p>")
        cgicommon.writeln("Game ID prefix: <input type=\"text\" name=\"wikitextgameprefix\" value=\"%s\" />" % (cgicommon.escape(wikitext_game_prefix, True)))
        cgicommon.writeln("</p>")
        cgicommon.writeln("<p>")
        cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney_name, True)))
        cgicommon.writeln("<input type=\"hidden\" name=\"format\" value=\"wikitext\" />")
        cgicommon.writeln("<input type=\"submit\" name=\"wikitextsubmit\" value=\"Generate Wikitext\" />")
        cgicommon.writeln("</p>")
        cgicommon.writeln("</form>")
        cgicommon.writeln("</div>")
        cgicommon.writeln("</body>")
        cgicommon.writeln("</html>")
        sys.exit(0)
elif export_format == "csv":
    if not csv_submit_download and not csv_submit_view:
        # Ask the user what event code and format code they want to use.
        # Everything else is stuff we already have in the tourney db.
        cgicommon.writeln("Content-Type: text/html; charset=utf-8")
        cgicommon.writeln("")
        started_html = True

        cgicommon.print_html_head("Tournament report - CSV")

        tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
        cgicommon.writeln("<body>")
        cgicommon.show_sidebar(tourney)

        cgicommon.writeln("<div class=\"mainpane\">")

        cgicommon.writeln("<h1>Tournament report - CSV</h1>")

        cgicommon.writeln("<form method=\"GET\" action=\"/cgi-bin/export.py\">")

        cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney_name, True)))
        cgicommon.writeln("<input type=\"hidden\" name=\"format\" value=\"csv\" />")
        cgicommon.writeln("<p>Event code: <input type=\"text\" name=\"csveventcode\" value=\"%s\" /> (e.g. COLIN2019)</p>" % (cgicommon.escape(csv_event_code or tourney_name, True)))
        cgicommon.writeln("<p>Game format: <input type=\"text\" name=\"csvgameformat\" value=\"%s\" />" % (cgicommon.escape(csv_game_format, True)))
        cgicommon.writeln("(e.g. 9R, 15R, ...)</p>");
        cgicommon.writeln("<p>")
        cgicommon.writeln("Containing what information?<br />")
        cgicommon.writeln("<input type=\"radio\" name=\"csvtype\" value=\"results\" id=\"csvtyperesults\" checked /> <label for=\"csvtyperesults\">Game results</label><br />")
        cgicommon.writeln("<input type=\"radio\" name=\"csvtype\" value=\"standings\" id=\"csvtypestandings\" /> <label for=\"csvtypestandings\">Standings</label>")
        cgicommon.writeln("</p>")

        num_divisions = tourney.get_num_divisions()
        if num_divisions > 1:
            cgicommon.writeln("<p>")
            cgicommon.writeln("Which division(s)?<br />")
            for div in range(num_divisions):
                cgicommon.writeln("<input type=\"checkbox\" name=\"csvdiv%d\" id=\"csvdiv%d\" value=\"1\" checked /> <label for=\"csvdiv%d\">%s</label><br />" % (
                    div, div, div, cgicommon.escape(tourney.get_division_name(div))
                ))
            cgicommon.writeln("</p>")

        cgicommon.writeln("<p>")
        cgicommon.writeln("<input type=\"submit\" name=\"csvsubmitview\" value=\"View CSV in browser\" />")
        cgicommon.writeln("<input type=\"submit\" name=\"csvsubmitdownload\" value=\"Download CSV\" />")
        cgicommon.writeln("</p>")

        cgicommon.writeln("</form>")

        cgicommon.writeln("</div>")

        cgicommon.writeln("</body>")
        cgicommon.writeln("</html>")

        sys.exit(0)


try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

    full_name = tourney.get_full_name()
    venue = tourney.get_venue()
    (date_year, date_month, date_day) = tourney.get_event_date()
    if date_year and date_month and date_day:
        date_string = "%d %s %04d" % (date_day, "Octember" if date_month < 1 or date_month > 12 else calendar.month_name[date_month], date_year)
    else:
        date_string = None
    games = tourney.get_games();

    show_draws_column = tourney.get_show_draws_column()

    rank_method = tourney.get_rank_method()
    show_points_column = tourney.is_ranked_by_points()
    show_spread_column = tourney.is_ranked_by_spread()
    show_tournament_rating_column = tourney.get_show_tournament_rating_column()

    if export_format == "html":
        cgicommon.writeln("Content-Type: text/html; charset=utf-8");
        cgicommon.writeln("");
        started_html = True;

        cgicommon.print_html_head_local("Tourney: %s" % full_name);

        cgicommon.writeln("<body>");

        cgicommon.writeln("<div class=\"exportedstandings\">")
        cgicommon.writeln("<h1>%s</h1>" % (cgicommon.escape(full_name)))
        if venue:
            cgicommon.writeln("<p>%s</p>" % (cgicommon.escape(venue)))
        if date_string:
            cgicommon.writeln("<p>%s</p>" % (cgicommon.escape(date_string)))
        cgicommon.writeln("<h2>Standings</h2>")

        num_divisions = tourney.get_num_divisions()

        cgicommon.writeln("<p>")
        cgicommon.writeln(cgicommon.escape(rank_method.get_short_description()))
        if show_draws_column:
            cgicommon.writeln("Draws count as half a win.")
        cgicommon.writeln("</p>")

        cgicommon.show_standings_table(tourney, tourney.get_show_draws_column(), show_points_column, show_spread_column, False, False, show_tournament_rating_column, True)
        cgicommon.writeln("</div>")

        cgicommon.writeln("<div class=\"exportedresults\">")
        cgicommon.writeln("<h2>Results</h2>")
        prev_round_no = None
        prev_table_no = None
        prev_division = None
        show_table_numbers = None
        game_seq = 0
        for g in games:
            if prev_round_no is None or prev_round_no != g.round_no:
                if prev_round_no is not None:
                    cgicommon.writeln("</table>")
                    cgicommon.writeln("<br />")
                cgicommon.writeln("<table class=\"resultstable\">")
                cgicommon.writeln("<tr><th colspan=\"3\" class=\"exportroundnumber\">%s</th></tr>" % (cgicommon.escape(tourney.get_round_name(g.round_no))))
                prev_table_no = None
                prev_division = None
            if prev_division is None or prev_division != g.division:
                if num_divisions > 1:
                    cgicommon.writeln("<tr class=\"exportdivisionnumber\"><th class=\"exportdivisionnumber\" colspan=\"3\">%s</th></tr>" % (cgicommon.escape(tourney.get_division_name(g.division))))

                # If this division has a table with more than one game on it
                # then show the table numbers, otherwise don't bother.
                prev_table_no = g.table_no
                show_table_numbers = False
                i = 1
                while game_seq + i < len(games) and games[game_seq + i].round_no == g.round_no and games[game_seq + i].division == g.division:
                    if games[game_seq + i].table_no == prev_table_no:
                        show_table_numbers = True
                        break
                    prev_table_no = games[game_seq + i].table_no
                    i += 1
                prev_table_no = None
            if prev_table_no is None or prev_table_no != g.table_no:
                if show_table_numbers:
                    cgicommon.writeln("<tr class=\"exporttablenumber\"><th class=\"exporttablenumber\" colspan=\"3\">Table %d</th></tr>" % g.table_no)
            cgicommon.writeln("<tr class=\"exportgamerow\">")
            names = g.get_player_names();
            cgicommon.writeln("<td class=\"exportleftplayer\">%s</td>" % names[0]);
            if g.s1 is None or g.s2 is None:
                cgicommon.writeln("<td class=\"exportscore\"> v </td>")
            else:
                cgicommon.writeln("<td class=\"exportscore\">%s</td>" % cgicommon.escape(g.format_score()));
            cgicommon.writeln("<td class=\"exportrightplayer\">%s</td>" % names[1]);
            cgicommon.writeln("</tr>")
            prev_table_no = g.table_no
            prev_round_no = g.round_no
            prev_division = g.division
            game_seq += 1
        if prev_round_no is not None:
            cgicommon.writeln("</table>")

        cgicommon.writeln("</div>")

        cgicommon.writeln("</body></html>");
    elif export_format == "text":
        cgicommon.writeln("Content-Type: text/plain; charset=utf-8")
        cgicommon.writeln("")
        cgicommon.writeln(full_name)
        if venue:
            cgicommon.writeln(venue)
        if date_string:
            cgicommon.writeln(date_string)
        cgicommon.writeln("")
        cgicommon.writeln("STANDINGS")
        cgicommon.writeln("")
        cgicommon.writeln(rank_method.get_short_description())
        if show_draws_column:
            cgicommon.writeln("Draws count as half a win.")
        cgicommon.writeln("")
        cgicommon.writeln("")

        num_divisions = tourney.get_num_divisions()

        # First, work out how much room we need for the longest name
        max_name_len = 0
        for div_index in range(num_divisions):
            standings = tourney.get_standings(div_index, True)
            if len(standings) > 0:
                m = max([len(x[1]) for x in standings]);
                if m > max_name_len:
                    max_name_len = m

        for div_index in range(num_divisions):
            standings = tourney.get_standings(div_index, True)
            if num_divisions > 1:
                cgicommon.writeln(tourney.get_division_name(div_index))

            # Show the position, then the name, then games played, then the
            # number of wins, then the number of draws if applicable, then any
            # secondary ranking columns, then points if they weren't in the
            # secondary ranking columns, then tournament rating if applicable.
            header_line = ("%%%ds" % (max_name_len + 6)) % ("")
            header_line += "    P   W"
            row_format = "%(pos)5d %(name)-" + str(max_name_len) + "s  %(played)3d %(wins)3d"
            if show_draws_column:
                header_line += "   D"
                row_format += " %(draws)3d"
            shown_points = False
            sec_index = 0
            sec_rank_headings = rank_method.get_secondary_rank_headings(short=True)
            for sec_index in range(len(sec_rank_headings)):
                heading = sec_rank_headings[sec_index]
                width = max(4, len(heading))
                header_line += (" %" + str(width) + "s") % (heading)
                row_format += " %(secondary" + str(sec_index) + ")" + str(width) + "s"
                if heading == "Pts":
                    shown_points = True
            if show_points_column and not shown_points:
                header_line += "  Pts"
                row_format += " %(points)4d"
            if show_tournament_rating_column:
                header_line += "      TR"
                row_format += " %(tr)7s"

            cgicommon.writeln(header_line)
            for s in standings:
                fields = {
                        "pos" : s.position,
                        "name" : s.name,
                        "played" : s.played,
                        "wins" : s.wins,
                        "draws" : s.draws,
                        "points" : s.points,
                        "tr" : ("" if s.tournament_rating is None else "%7.2f" % (s.tournament_rating))
                }
                secondary_rank_value_strings = s.get_secondary_rank_value_strings()
                for i in range(len(secondary_rank_value_strings)):
                    fields["secondary" + str(i)] = secondary_rank_value_strings[i]
                cgicommon.write(row_format % fields)

                # If this player has played in any QF, SF, final or third place
                # playoff, insert a parenthetical explanatory note as to why
                # their position in the table might not match their wins/points
                # total.
                finals_form = s.finals_form
                # Remove any leading dashes from finals form
                while finals_form and finals_form[0] == '-':
                    finals_form = finals_form[1:]
                if finals_form:
                    if len(finals_form) == 1 and s[0] <= 4:
                        match_type = ("final" if s[0] <= 2 else "third place")
                        cgicommon.write(" (%s %s)" % (form_letter_to_word.get(finals_form), match_type))
                    else:
                        # Not just a single finals match, so display
                        # something like "(finals: WWL)".
                        cgicommon.write(" (finals: " + finals_form + ")")
                cgicommon.writeln("")
            cgicommon.writeln("")
            cgicommon.writeln("")

        cgicommon.writeln("RESULTS")

        prev_round_no = None
        prev_table_no = None
        prev_division = None
        show_table_numbers = False
        game_seq = 0
        for g in games:
            if prev_round_no is None or prev_round_no != g.round_no:
                cgicommon.writeln("")
                cgicommon.writeln(tourney.get_round_name(g.round_no))
                prev_table_no = None
                prev_division = None
            if prev_division is None or prev_division != g.division:
                if num_divisions > 1:
                    cgicommon.writeln("")
                    cgicommon.writeln(tourney.get_division_name(g.division))
                i = 1
                prev_table_no = g.table_no
                show_table_numbers = False
                # If this division in this round has a table with more than
                # one game on it, show the table numbers, else don't.
                while game_seq + i < len(games) and games[game_seq + i].round_no == g.round_no and games[game_seq + i].division == g.division:
                    if games[game_seq + i].table_no == prev_table_no:
                        show_table_numbers = True
                        break
                    prev_table_no = games[game_seq + i].table_no
                    i += 1
                prev_table_no = None
            if prev_table_no is None or prev_table_no != g.table_no:
                if show_table_numbers:
                    cgicommon.writeln("")
                    cgicommon.writeln("Table %d" % g.table_no)
            if g.s1 is None or g.s2 is None:
                score_str = "    -    "
            elif g.is_double_loss():
                score_str = "  X - X  "
            else:
                score_str = "%3d%s-%s%d" % (g.s1, "*" if g.tb and g.s1 > g.s2 else " ", "*" if g.tb and g.s2 >= g.s1 else " ", g.s2)
            names = g.get_player_names()
            cgicommon.writeln("%*s %-9s %s" % (max_name_len, names[0], score_str, names[1]))
            prev_round_no = g.round_no
            prev_table_no = g.table_no
            prev_division = g.division
            game_seq += 1
    elif export_format == "wikitext":
        num_divisions = tourney.get_num_divisions()
        cgicommon.writeln("Content-Type: text/plain; charset=utf-8")
        cgicommon.writeln("")
        cgicommon.writeln("==Standings==")
        cgicommon.writeln()
        sec_rank_headings = rank_method.get_secondary_rank_headings()
        for div_index in range(num_divisions):
            if num_divisions > 1:
                cgicommon.writeln("===%s===" % (tourney.get_division_name(div_index)))
            standings = tourney.get_standings(div_index, True)
            cgicommon.writeln("{|")
            cgicommon.write("! Rank !! Name !! Games !! Wins")
            if show_draws_column:
                cgicommon.write(" !! Draws")
            for head in sec_rank_headings:
                cgicommon.write(" !! " + head)
            if show_points_column and "Points" not in sec_rank_headings:
                cgicommon.write(" !! Points")
            if show_spread_column and "Spread" not in sec_rank_headings:
                cgicommon.write(" !! Spread")
            if show_tournament_rating_column:
                cgicommon.write(" !! Tournament rating")
            cgicommon.writeln("")
            for s in standings:
                cgicommon.writeln("|-")
                cgicommon.write("| %3d || %s || %d || %d" % (s.position, s.name, s.played, s.wins))
                if show_draws_column:
                    cgicommon.write(" || %d" % (s.draws))
                for val in s.get_secondary_rank_value_strings():
                    cgicommon.write(" || %s" % (val))
                if show_points_column and "Points" not in sec_rank_headings:
                    cgicommon.write(" || %d" % (s.points))
                if show_spread_column and "Spread" not in sec_rank_headings:
                    cgicommon.write(" || %+d" % (s.spread))
                if show_tournament_rating_column:
                    cgicommon.write(" || %d" % (s.tournament_rating))
                cgicommon.writeln("")
            cgicommon.writeln("|-")
            cgicommon.writeln("|}")
            cgicommon.writeln()

        cgicommon.writeln("==Results==")
        num_tiebreaks = 0
        game_serial_no = 1
        wikitext_date = "%02d/%02d/%04d" % (wikitext_date_d, wikitext_date_m, wikitext_date_y)
        for div_index in range(num_divisions):
            if num_divisions > 1:
                cgicommon.writeln("===%s===" % (tourney.get_division_name(div_index)))
            cgicommon.writeln("{{game table}}")
            div_games = [x for x in games if x.get_division() == div_index]
            prev_round_no = None
            for g in div_games:
                if g.round_no != prev_round_no:
                    cgicommon.writeln("{{game table block|%s}}" % (tourney.get_round_name(g.round_no)))
                cgicommon.writeln("{{game | %s%03d | %s | Table %d | %s | %s | %s | }}" % (
                        wikitext_game_prefix, game_serial_no, wikitext_date,
                        g.table_no, g.get_player_names()[0], g.format_score(),
                        g.get_player_names()[1]))
                if g.tb:
                    num_tiebreaks += 1
                prev_round_no = g.round_no
                game_serial_no += 1
            cgicommon.writeln("{{game table end}}")
            cgicommon.writeln("")

        if num_tiebreaks > 0:
            cgicommon.writeln("<center>* includes 10 points from a tie-break conundrum</center>")
    elif export_format == "csv":
        selected_divisions = set()
        num_divisions = tourney.get_num_divisions()

        for div_index in range(num_divisions):
            if ("csvdiv%d" % (div_index)) in form:
                selected_divisions.add(div_index)

        if csv_submit_download:
            filename = csv_event_code
            if not filename:
                filename = tourney_name
            else:
                filename = "".join([ x for x in filename if x not in "\\\"\':/"])
            if csv_type:
                filename += "_" + csv_type
            cgicommon.writeln("Content-Type: text/csv; charset=utf-8")
            cgicommon.writeln("Content-Disposition: attachment; filename=\"%s.csv\"" % (filename))
        else:
            cgicommon.writeln("Content-Type: text/plain; charset=utf-8")

        cgicommon.writeln("")

        if csv_type == "standings":
            sec_rank_headings = rank_method.get_secondary_rank_headings()
            writer = csv.writer(sys.stdout, delimiter=",", quotechar="\"", quoting=csv.QUOTE_MINIMAL)
            if num_divisions == 1:
                selected_divisions = [0]

            # Write header row
            header_row = [ "Position", "Name", "Finals", "Played", "Wins", "Draws" ]
            for heading in sec_rank_headings:
                header_row.append(heading)
            if show_points_column and "Points" not in sec_rank_headings:
                header_row.append("Points")
            if show_spread_column and "Spread" not in sec_rank_headings:
                header_row.append("Spread")
            writer.writerow(tuple(header_row))
            last_div_position = 0
            for div in selected_divisions:
                standings = tourney.get_standings(division=div, calculate_qualification=False)
                for s in standings:
                    finals_form = s.finals_form
                    while finals_form and finals_form[0] == '-':
                        finals_form = finals_form[1:]
                    row = [ last_div_position + s.position, s.name, finals_form,
                            s.played, s.wins, s.draws ]
                    for val in s.get_secondary_rank_value_strings():
                        row.append(val)
                    if show_points_column and "Points" not in sec_rank_headings:
                        row.append(s.points)
                    if show_spread_column and "Spread" not in sec_rank_headings:
                        row.append(s.spread)
                    writer.writerow(tuple(row))

                if standings:
                    last_div_position = standings[-1].position
        else:
            games = tourney.get_games()
            games = sorted(games, key=lambda x : (x.get_round_no(), x.get_division(), x.get_table_no(), x.get_round_seq()))

            writer = csv.writer(sys.stdout, delimiter=',', quotechar='\"', quoting=csv.QUOTE_MINIMAL)

            # Write header row
            writer.writerow(("Event code", "Player 1", "Player 1's score", "Player 2's score", "Player 2", "Round", "Format", "Tiebreak?"))
            for g in games:
                # If there's more than one division, then don't output a game
                # from a division that wasn't ticked when we submitted the form
                div = g.get_division()
                if num_divisions > 1 and div not in selected_divisions:
                    continue

                player_names = g.get_player_names()
                game_type = g.get_game_type()
                if game_type in ('P', 'N'):
                    round_text = str(g.get_round_no())
                else:
                    # If it's QF, SF etc, use that rather than the round number
                    round_text = game_type

                if len(selected_divisions) > 1:
                    if div > 26:
                        round_text = tourney.get_short_division_name(div) + "." + round_text
                    else:
                        round_text = tourney.get_short_division_name(div) + round_text

                # Write one row for each game
                score = g.get_score()
                writer.writerow((csv_event_code,
                    player_names[0], score[0], score[1], player_names[1],
                    round_text, csv_game_format, 1 if g.is_tiebreak() else None))
    else:
        show_error("Unknown export format: %s" % export_format);
except countdowntourney.TourneyException as e:
    if started_html:
        cgicommon.show_tourney_exception(e);
    else:
        show_error(e.get_description());

sys.exit(0)
