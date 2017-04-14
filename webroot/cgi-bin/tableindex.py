#!/usr/bin/python

import cgi
import cgitb
import cgicommon
import sys
import urllib
import os

cgitb.enable();

cgicommon.set_module_path();
import countdowntourney;

def fatal_error(text):
    cgicommon.print_html_head("Table Index")
    print "<body>"
    print "<p>%s</p>" % (cgi.escape(text))
    print "</body></html>"
    sys.exit(1)

def fatal_exception(exc, tourney=None):
    cgicommon.print_html_head("Table Index")
    print "<body>"
    if tourney:
        cgicommon.show_sidebar(tourney)
    print "<div class=\"mainpane\">"
    cgicommon.show_tourney_exception(exc)
    print "</div>"
    print "</body></html>"
    sys.exit(1)

def int_or_none(s):
    if s is None:
        return None
    else:
        try:
            return int(s)
        except:
            return None

print "Content-Type: text/html; charset=utf-8"
print ""

baseurl = "/cgi-bin/tableindex.py"
form = cgi.FieldStorage()
tourneyname = form.getfirst("tourney")

tourney = None
if tourneyname is None:
    fatal_error("No tourney name specified.")

try:
    tourney = countdowntourney.tourney_open(tourneyname, cgicommon.dbdir)
except countdowntourney.TourneyException as e:
    fatal_exception(e, None)

# Read parameters to adjust how the table is formatted
max_columns = int_or_none(form.getfirst("maxcols"))
if max_columns is None or max_columns < 1:
    max_columns = 3
names_per_column = int_or_none(form.getfirst("namespercol"))
if names_per_column is None or names_per_column <= 0:
    names_per_column = 20
min_names_per_column = int_or_none(form.getfirst("minnamespercol"))
if min_names_per_column is None or min_names_per_column < 0:
    min_names_per_column = 5

cgicommon.print_html_head("Table assignment")

cgicommon.show_sidebar(tourney)

print "<div class=\"mainpane\">"

rd = tourney.get_current_round()

if rd is None:
    print "<h1>Table assignment</h1>"
    print "<p>There are no fixtures yet.</p>"
else:
    round_no = rd["num"]
    round_name = rd["name"]

    print "<h1>Table assignment: %s</h1>" % (cgi.escape(round_name))
    games = tourney.get_games(round_no)
    player_name_to_table_list = dict()
    for g in games:
        names = g.get_player_names()
        for name in names:
            current_table_list = player_name_to_table_list.get(name, [])
            if g.table_no not in current_table_list:
                player_name_to_table_list[name] = current_table_list + [g.table_no]

    # Display the index in several columns, so we use more horizontal space
    # and save vertical space.

    num_names = len(player_name_to_table_list)

    if num_names > 0:
        num_columns = (num_names + names_per_column - 1) / names_per_column
        if num_columns <= 2:
            names_per_column = num_names

        # If there would be fewer than five names in the last column, use one
        # fewer column and extend the earlier columns.
        if num_columns > 1 and num_names % names_per_column > 0 and num_names % names_per_column < min_names_per_column:
            num_columns -= 1
            names_per_column = (num_names + num_columns - 1) / num_columns

        # Don't display more than the maximum number of columns. If we have
        # more than this many columns, make the columns longer.
        if num_columns > max_columns:
            num_columns = max_columns
            names_per_column = (num_names + num_columns - 1) / num_columns

        print "<table class=\"tableindex\">"
        columns = [ [] for i in range(num_columns) ]
        sorted_names = sorted(player_name_to_table_list)
        for position_in_column in range(0, names_per_column):
            print "<tr>"
            for column in range(0, num_columns):
                position_in_list = column * names_per_column + position_in_column
                if position_in_list < len(sorted_names):
                    name = sorted_names[position_in_list]
                    print "<td class=\"tableindexname\">%s</td>" % (cgi.escape(name))
                    print "<td class=\"tableindextable\">%s</td>" % (cgi.escape(", ".join(map(str, player_name_to_table_list[name]))))
                    if column < num_columns - 1:
                        print "<td class=\"tableindexspacer\"> </td>"
            print "</tr>"
        print "</table>"

print "</div>"
print "</body>"
print "</html>"

