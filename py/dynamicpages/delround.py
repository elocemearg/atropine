#!/usr/bin/python3

import cgicommon
import urllib.request, urllib.parse, urllib.error
import countdowntourney

baseurl = "/cgi-bin/delround.py"

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

def handle(httpreq, response, tourney, request_method, form, query_string):
    round_no = int_or_none(form.getfirst("round"))
    confirm = int_or_none(form.getfirst("confirm"))
    tourneyname = tourney.name

    cgicommon.print_html_head(response, "Delete round: " + str(tourneyname))

    response.writeln("<body>");

    if confirm:
        try:
            tourney.delete_round(round_no)
            cgicommon.show_sidebar(response, tourney);
            response.writeln("<div class=\"mainpane\">");
            response.writeln("<h1>Delete round</h1>");
            cgicommon.show_success_box(response, "Round %d deleted successfully." % (round_no))
            response.writeln('<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to tourney setup</a></p>' % urllib.parse.quote_plus(tourneyname))
        except countdowntourney.TourneyException as e:
            cgicommon.show_sidebar(response, tourney);
            response.writeln("<div class=\"mainpane\">");
            response.writeln("<h1>Delete round</h1>");
            cgicommon.show_tourney_exception(response, e)
    else:
        cgicommon.show_sidebar(response, tourney);
        response.writeln("<div class=\"mainpane\">");
        response.writeln("<h1>Delete round</h1>");
        latest_round_no = tourney.get_latest_round_no()
        if latest_round_no is None:
            response.writeln('<p>There are no rounds to delete!</p>')
            response.writeln('<p><a href="/cgi-bin/tourneysetup.py?tourney=%s">Back to tourney setup</a></p>' % urllib.parse.quote_plus(tourneyname))
        else:
            round_name = tourney.get_round_name(latest_round_no)
            response.writeln('<p>The most recent round is shown below.</p>')
            cgicommon.show_warning_box(response, "You are about to delete this round and all the fixtures in it. <strong>This cannot be undone.</strong> Are you sure you want to delete it?")
            response.writeln('<form action="%s" method="post">' % (baseurl))
            response.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname))
            response.writeln('<input type="hidden" name="round" value="%d" />' % latest_round_no)
            response.writeln('<input type="hidden" name="confirm" value="1" />')
            response.writeln('<p>')
            response.writeln('<input type="submit" class="bigbutton destroybutton" name="delroundsubmit" value="Yes, I\'m sure. Delete the round and all its games." />')
            response.writeln('</p>')
            response.writeln('</form>')
            response.writeln('<form action="/cgi-bin/tourneysetup.py" method="post">')
            response.writeln('<input type="hidden" name="tourney" value="%s" />' % cgicommon.escape(tourneyname))
            response.writeln('<input type="submit" class="bigbutton chickenoutbutton" name="arrghgetmeoutofhere" value="No. Cancel this and take me back to the tourney setup page." />')
            response.writeln('</form>')

            num_divisions = tourney.get_num_divisions()
            response.writeln("<h2>%s</h2>" % (round_name))
            for div_index in range(num_divisions):
                response.writeln("<h3>%s</h3>" % cgicommon.escape(tourney.get_division_name(div_index)))
                games = tourney.get_games(round_no=latest_round_no, division=div_index)
                cgicommon.show_games_as_html_table(response, games, False, None, False, None, lambda x : cgicommon.player_to_link(x, tourneyname))

    response.writeln("</div>")

    response.writeln("</body>")
    response.writeln("</html>")
