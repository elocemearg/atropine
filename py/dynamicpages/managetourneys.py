#!/usr/bin/python3

import os
import time

import htmlcommon
import htmldialog
import countdowntourney

def print_tourney_table(response, tourney_list, order_by):
    response.writeln("<table class=\"tourneylist\">");
    response.writeln("<tr>")
    response.writeln("<th><a href=\"?orderby=%s\">Name</a></th>" % ("name_d" if order_by == "name_a" else "name_a"))
    response.writeln("<th>Operations</th>")
    response.writeln("<th><a href=\"?orderby=%s\">Last modified</a></th>" % ("mtime_a" if order_by == "mtime_d" else "mtime_d"))
    response.writeln("</tr>")
    for name in tourney_list:
        tourney_basename = name + ".db"
        filename = os.path.join(htmlcommon.dbdir, tourney_basename)
        st = os.stat(filename)
        modified_time = time.localtime(st.st_mtime)
        response.writeln("<tr>")
        response.writeln('<td class=\"tourneylistname\">')
        response.writeln('<a href="/atropine/%(name)s/tourneysetup">%(name)s</a>' % { "name" : htmlcommon.escape(name) })
        response.writeln('</td>')
        response.writeln("<td class=\"tourneylistadvanced\">")
        response.writeln("<form method=\"GET\" action=\"/atropine/%(name)s/exportdbfile\"><input type=\"submit\" value=\"Download .db\"></form>" % { "name" : htmlcommon.escape(name) })
        response.writeln("<form method=\"GET\" action=\"/atropine/%(name)s/sql\"><input type=\"submit\" value=\"&#x1F527; SQL prompt\"></form>" % { "name" : htmlcommon.escape(name) })
        response.writeln("<button onclick=\"showDeleteDialog('%(name)s');\">&#x1F5D1; Delete</button>" % { "name" : name } )
        response.writeln("</td>")
        response.writeln("<td class=\"tourneylistmtime\">%s</td>" % (time.strftime("%d %b %Y %H:%M", modified_time)))
        response.writeln("</td>")
        response.writeln("</tr>")
    response.writeln("</table>")

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    # tourney is None for this handler
    htmlcommon.print_html_head(response, "Manage Tourneys")

    response.writeln("<script>")
    response.writeln(htmldialog.DIALOG_JAVASCRIPT)
    response.writeln("""
function showDeleteDialog(tourneyName) {
    let p1 = document.createElement("P");
    let p2 = document.createElement("P");
    let p3 = document.createElement("P");
    p1.innerHTML = 'You are about to delete the database file for tourney: <span style="font-weight: bold;">' + tourneyName + '</span>';
    p2.innerHTML = 'This will permanently delete the tourney along with all its players, games and scores. This cannot be undone.';
    p3.innerHTML = 'Are you sure you want to delete the <span style="font-weight: bold;">' + tourneyName + '</span> tourney?';
    dialogBoxShow("deletedialog", "Delete tourney?", "Delete", "Cancel",
        "POST", "/atropine/global/managetourneys%(qs)s", "delete", [p1, p2, p3], { "tourney" : tourneyName });
}
""" % {
        "qs" : "?" + query_string
    })
    response.writeln("</script>")

    response.writeln("<h1>Manage Tourneys</h1>")
    response.writeln("<p><a href=\"/\">Back to the home page</a></p>")

    if request_method == "POST":
        if "delete" in form:
            try:
                tourney_name = form.getfirst("tourney")
                countdowntourney.tourney_delete(tourney_name, htmlcommon.dbdir)
                htmlcommon.show_success_box(response, "Successfully deleted tourney \"%s\"" % (htmlcommon.escape(tourney_name)))
            except countdowntourney.TourneyException as e:
                htmlcommon.show_tourney_exception(response, e)

    order_by = form.getfirst("orderby", "mtime_d")

    response.writeln("<p>Tourneys location: <span class=\"fixedwidth\">%s</span></p>" % (htmlcommon.escape(htmlcommon.dbdir)))

    tourney_list = countdowntourney.get_tourney_list(htmlcommon.dbdir, order_by)
    if tourney_list:
        print_tourney_table(response, tourney_list, order_by)

    response.writeln(htmldialog.get_html("deletedialog"))

    response.writeln("</body>")
    response.writeln("</html>")

