#!/usr/bin/python3

import sys;
import os;
import htmltraceback;
import urllib.request, urllib.parse, urllib.error;
import time;

import cgicommon;

htmltraceback.enable();
cgicommon.set_module_path();

import countdowntourney;

def int_or_none(s):
    try:
        return int(s);
    except ValueError:
        return None;

def get_tourney_modified_time(name):
    path_name = os.path.join(cgicommon.dbdir, name)
    st = os.stat(path_name)
    return st.st_mtime

def print_tourney_table(tourney_list, destination_page, show_last_modified, show_export_html_link=False, show_display_link=False):
    cgicommon.writeln("<table class=\"tourneylist\">");
    cgicommon.writeln("<tr>")
    cgicommon.writeln("<th><a href=\"/cgi-bin/home.py?orderby=%s\">Name</a></th>" % ("name_d" if order_by == "name_a" else "name_a"))

    if show_last_modified:
        cgicommon.writeln("<th><a href=\"/cgi-bin/home.py?orderby=%s\">Last modified</a></th>" % ("mtime_a" if order_by == "mtime_d" else "mtime_d"))

    if show_display_link or show_export_html_link:
        cgicommon.writeln("<th colspan=\"%d\">Useful links</th>" % ( 2 if show_display_link and show_export_html_link else 1 ))

    cgicommon.writeln("</tr>")
    for tourney_basename in tourney_list:
        name = tourney_basename[:-3];
        filename = os.path.join(cgicommon.dbdir, tourney_basename)
        st = os.stat(filename)
        modified_time = time.localtime(st.st_mtime)
        cgicommon.writeln("<tr>")
        cgicommon.writeln('<td class=\"tourneylistname\">')
        if destination_page:
            cgicommon.writeln('<a href="%s?tourney=%s">%s</a>' % (cgicommon.escape(destination_page, True), urllib.parse.quote_plus(name), cgicommon.escape(name)));
        else:
            cgicommon.writeln(cgicommon.escape(name))
        cgicommon.writeln('</td>')

        if show_last_modified:
            cgicommon.writeln("<td class=\"tourneylistmtime\">%s</td>" % (time.strftime("%d %b %Y %H:%M", modified_time)))

        if show_export_html_link:
            cgicommon.writeln("<td class=\"tourneylistlink\">")
            cgicommon.writeln("<a href=\"/cgi-bin/export.py?tourney=%s&format=html\">Tourney report</a>" % (urllib.parse.quote_plus(name)))
            cgicommon.writeln("</td>")
        if show_display_link:
            cgicommon.writeln("<td class=\"tourneylistlink\">")
            cgicommon.writeln("<a href=\"/cgi-bin/display.py?tourney=%s\">Full screen display</a>" % (urllib.parse.quote_plus(name)))
            cgicommon.writeln("</td>")

        cgicommon.writeln("</tr>")
    cgicommon.writeln("</table>");

baseurl = "/cgi-bin/home.py";

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

cgicommon.print_html_head("Create Tourney" if cgicommon.is_client_from_localhost() else "Atropine");

form = cgicommon.FieldStorage();

tourneyname = form.getfirst("name", "");
longtourneyname = form.getfirst("longtourneyname", "")
displayshape = int_or_none(form.getfirst("displayshape", "0"))
if displayshape is None:
    displayshape = 0
display_profile_name = form.getfirst("displayprofile", "")
order_by = form.getfirst("orderby", "mtime_d")
request_method = os.environ.get("REQUEST_METHOD", "GET");

tourney_create_exception = None
tourney_created = False

if cgicommon.is_client_from_localhost():
    if request_method == "POST" and tourneyname:
        # We've been asked to create a new tourney.
        try:
            tourney = countdowntourney.tourney_create(tourneyname, cgicommon.dbdir, load_display_profile_name=display_profile_name)
            if longtourneyname:
                tourney.set_full_name(longtourneyname)
            if not display_profile_name:
                tourney.set_screen_shape_profile_id(displayshape)
            tourney.close()
            tourney_created = True
        except countdowntourney.TourneyException as e:
            tourney_create_exception = e

cgicommon.writeln("<body onload=\"initPage();\">");
cgicommon.writeln("""
<script>
function initPage() {
    let tourneyNameBox = document.getElementById("tourneyname");
    if (tourneyNameBox) {
        tourneyNameBox.focus();
        tourneyNameBox.select();
    }
""")
if tourney_created:
    cgicommon.writeln("""
    /* Redirect the user to the new tourney they just created */
    setTimeout(function() {
        window.location.replace("/cgi-bin/tourneysetup.py?tourney=%s");
    }, 0);
    """ % (urllib.parse.quote_plus(tourneyname)))
cgicommon.writeln("""
}
</script>
""")

if tourney_created:
    cgicommon.writeln("<p>");
    cgicommon.writeln('You should be redirected to your new tourney semi-immediately. If not, <a href="/cgi-bin/tourneysetup.py?tourney=%s">click here to continue</a>.' % urllib.parse.quote_plus(tourneyname));
    cgicommon.writeln("</p>");
    cgicommon.writeln("</body></html>")
    sys.exit(0)

cgicommon.writeln("<h1>Welcome to Atropine</h1>");

if tourney_create_exception:
    cgicommon.show_tourney_exception(tourney_create_exception)

if cgicommon.is_client_from_localhost():
    if not tourney_created:
        # Show the form to create a new tourney
        display_shape_option_html = ""
        for (i, d) in enumerate(countdowntourney.SCREEN_SHAPE_PROFILES):
            display_shape_option_html += "<option value=\"%d\"%s>%s</option>" % (i, " selected" if i == displayshape else "", d["name"])
        cgicommon.writeln("<h2>Create new tourney</h2>");

        cgicommon.writeln('<form action="%s" method="POST">' % cgicommon.escape(baseurl, True));

        # If at least one display profile is defined, also show a drop-down
        # box so the user can choose from which display profile to take the
        # initial settings.
        display_profiles = countdowntourney.get_display_profiles()
        most_recently_used_display_profile_name = countdowntourney.get_display_profile_for_last_created_tourney()
        if display_profiles:
            display_profile_options = []
            display_profile_options.append("<option value=\"\"%s>Default settings</option>" % (" selected" if not most_recently_used_display_profile_name else ""))
            for name in sorted(display_profiles):
                display_profile_options.append("<option value=\"%s\"%s>%s</option>" % (cgicommon.escape(name), " selected" if name == most_recently_used_display_profile_name else "", cgicommon.escape(name)))
            display_profile_controls_html = "<tr><td>Display profile</td><td><select name=\"displayprofile\">" + "\n".join(display_profile_options) + "</select></td></tr>"
            display_profile_controls_html += "<tr><td class=\"optionnote\" colspan=\"2\">Automatically apply the display settings from a previously-defined display profile.<br />Note that if you select a profile here, the screen shape defined in that profile will override what you selected above.</td></tr>"
        else:
            display_profile_controls_html = ""

        cgicommon.writeln("""
<table class="optionstable">
<col style="width: 12.5em;" />
<tr>
<td>
    <span style="font-weight: bold;">Tourney file name</span> <span class="optionrequired">(required)</span>
</td>
<td>
    <input type="text" id="tourneyname" name="name" value="%(tourneyname)s" />
</td>
</tr>
<tr>
<td class="optionnote" colspan="2">
    This name may consist only of letters, numbers, underscores (_) and hyphens (-), with no spaces.
</td>
<tr>
<td>Event name</td>
<td>
    <input type="text" name="longtourneyname" value="%(longtourneyname)s" />
</td>
</tr>
<tr>
<td class="optionnote" colspan="2">
    An optional full name for your event, such as "Co:Mordor %(currentyear)d". This may contain any text.
    <br />
    You can edit it in the Tourney Setup page after you've supplied a player list.
    <br />
    If supplied, this will be used on the Welcome screen and on any exported tournament reports.
</td>
</tr>
<tr>
<td>Display screen shape</td>
<td>
    <select name="displayshape">
        %(displayshapeoptionhtml)s
    </select>
</td>
</tr>
<tr>
<td class="optionnote" colspan="2">
    If you're using a public-facing display, and it's the old square-ish 4:3
    shape, you might want to change this accordingly.<br />
    This affects a few defaults relating to display settings. You can change it at any time in Display Setup.
</td>
</tr>
%(displayprofilecontrols)s
</table>
""" % {
    "tourneyname" : cgicommon.escape(tourneyname, True),
    "longtourneyname" : cgicommon.escape(longtourneyname, True),
    "displayshapeoptionhtml" : display_shape_option_html,
    "currentyear" : time.localtime().tm_year,
    "displayprofilecontrols" : display_profile_controls_html
})
        cgicommon.writeln("<div class=\"createtourneybuttonbox\">");
        cgicommon.writeln('<input type="submit" name="submit" value="Create Tourney" class=\"bigbutton\" />');
        cgicommon.writeln("</div>");
        cgicommon.writeln("</form>");
    cgicommon.writeln("<hr />")

tourney_list = os.listdir(cgicommon.dbdir);
tourney_list = [x for x in tourney_list if (len(x) > 3 and x[-3:] == ".db")];
if order_by in ("mtime_a", "mtime_d"):
    tourney_list = sorted(tourney_list, key=get_tourney_modified_time, reverse=(order_by == "mtime_d"));
else:
    tourney_list = sorted(tourney_list, key=lambda x : x.lower(), reverse=(order_by == "name_d"));

if cgicommon.is_client_from_localhost():
    if tourney_list:
        cgicommon.writeln("<h2>Open existing tourney</h2>");
        print_tourney_table(tourney_list, "/cgi-bin/tourneysetup.py", True, False, False)
    else:
        cgicommon.writeln("<p>")
        cgicommon.writeln("No tourneys exist yet.");
        cgicommon.writeln("</p>")

    cgicommon.writeln("<hr>")

    try:
        cgicommon.writeln("<p>")
        cgicommon.writeln("Tournament database directory: <span class=\"fixedwidth\">%s</span>" % (cgicommon.escape(os.path.realpath(cgicommon.dbdir))))
        cgicommon.writeln("</p>")
    except:
        cgicommon.writeln("<p>Failed to expand tournament database directory name</p>")
else:
    # Client is not from localhost, so display a menu of tournaments. Each
    # link goes to the Teleost display for that tournament, which is the only
    # thing non-localhost clients are allowed to access.
    cgicommon.writeln("<h2>Select tourney</h2>")
    print_tourney_table(tourney_list, None, False, True, True)

cgicommon.writeln("<p>Atropine version %s</p>" % (countdowntourney.SW_VERSION))
cgicommon.writeln("<p>Python version %d.%d.%d</p>" % tuple(sys.version_info[0:3]))

cgicommon.writeln("</body>");
cgicommon.writeln("</html>");

sys.exit(0);
