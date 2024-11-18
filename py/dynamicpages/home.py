#!/usr/bin/python3

import sys
import os
import time

import htmlcommon
import countdowntourney

def int_or_none(s):
    try:
        return int(s);
    except ValueError:
        return None;

def get_tourney_modified_time(name):
    path_name = os.path.join(htmlcommon.dbdir, name)
    st = os.stat(path_name)
    return st.st_mtime

def print_tourney_table(response, tourney_list, destination_page, show_last_modified, show_export_html_link=False, show_display_link=False, order_by="mtime_d"):
    response.writeln("<table class=\"tourneylist\">");
    response.writeln("<tr>")
    response.writeln("<th><a href=\"?orderby=%s\">Name</a></th>" % ("name_d" if order_by == "name_a" else "name_a"))

    if show_last_modified:
        response.writeln("<th><a href=\"?orderby=%s\">Last modified</a></th>" % ("mtime_a" if order_by == "mtime_d" else "mtime_d"))

    if show_display_link or show_export_html_link:
        response.writeln("<th colspan=\"%d\">Useful links</th>" % ( 2 if show_display_link and show_export_html_link else 1 ))

    response.writeln("</tr>")
    for tourney_basename in tourney_list:
        name = tourney_basename[:-3];
        filename = os.path.join(htmlcommon.dbdir, tourney_basename)
        st = os.stat(filename)
        modified_time = time.localtime(st.st_mtime)
        response.writeln("<tr>")
        response.writeln('<td class=\"tourneylistname\">')
        if destination_page:
            response.writeln('<a href="/atropine/%s/%s">%s</a>' % (htmlcommon.escape(name), htmlcommon.escape(destination_page), htmlcommon.escape(name)));
        else:
            response.writeln(htmlcommon.escape(name))
        response.writeln('</td>')

        if show_last_modified:
            response.writeln("<td class=\"tourneylistmtime\">%s</td>" % (time.strftime("%d %b %Y %H:%M", modified_time)))

        if show_export_html_link:
            response.writeln("<td class=\"tourneylistlink\">")
            response.writeln("<a href=\"/atropine/%s/export?format=html\">Tourney report</a>" % (htmlcommon.escape(name)))
            response.writeln("</td>")
        if show_display_link:
            response.writeln("<td class=\"tourneylistlink\">")
            response.writeln("<a href=\"/atropine/%s/display\">Full screen display</a>" % (htmlcommon.escape(name)))
            response.writeln("</td>")

        response.writeln("</tr>")
    response.writeln("</table>");

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    # For this handler, tourney is None.
    htmlcommon.print_html_head(response, "Create Tourney" if httpreq.is_client_from_localhost() else "Atropine");

    tourneyname = form.getfirst("name", "");
    longtourneyname = form.getfirst("longtourneyname", "")
    displayshape = int_or_none(form.getfirst("displayshape", "0"))
    if displayshape is None:
        displayshape = 0
    display_profile_name = form.getfirst("displayprofile", "")
    order_by = form.getfirst("orderby", "mtime_d")

    tourney_create_exception = None
    tourney_created = False

    if httpreq.is_client_from_localhost():
        if request_method == "POST" and tourneyname:
            # We've been asked to create a new tourney.
            try:
                tourney = countdowntourney.tourney_create(tourneyname, htmlcommon.dbdir, load_display_profile_name=display_profile_name)
                if longtourneyname:
                    tourney.set_full_name(longtourneyname)
                if not display_profile_name:
                    tourney.set_screen_shape_profile_id(displayshape)
                tourney.close()
                tourney_created = True
            except countdowntourney.TourneyException as e:
                tourney_create_exception = e

    response.writeln("<body onload=\"initPage();\">");
    response.writeln("""
    <script>
function initPage() {
    let tourneyNameBox = document.getElementById("tourneyname");
    if (tourneyNameBox) {
        tourneyNameBox.focus();
        tourneyNameBox.select();
    }
""")
    if tourney_created:
        response.writeln("""
        /* Redirect the user to the new tourney they just created */
        setTimeout(function() {
            window.location.replace("/atropine/%s/tourneysetup");
        }, 0);
        """ % (htmlcommon.escape(tourneyname)))
    response.writeln("}\n</script>")

    if tourney_created:
        response.writeln("<p>");
        response.writeln('You should be redirected to your new tourney semi-immediately. If not, <a href="/atropine/%s/tourneysetup">click here to continue</a>.' % htmlcommon.escape(tourneyname));
        response.writeln("</p>");
        response.writeln("</body></html>")
        return

    response.writeln("<h1>Welcome to Atropine</h1>");

    if tourney_create_exception:
        htmlcommon.show_tourney_exception(response, tourney_create_exception)

    if httpreq.is_client_from_localhost():
        if not tourney_created:
            # Show the form to create a new tourney
            display_shape_option_html = ""
            for (i, d) in enumerate(countdowntourney.SCREEN_SHAPE_PROFILES):
                display_shape_option_html += "<option value=\"%d\"%s>%s</option>" % (i, " selected" if i == displayshape else "", d["name"])
            response.writeln("<h2>Create new tourney</h2>");

            response.writeln('<form method="POST">');

            # If at least one display profile is defined, also show a drop-down
            # box so the user can choose from which display profile to take the
            # initial settings.
            display_profiles = countdowntourney.get_display_profiles()
            most_recently_used_display_profile_name = countdowntourney.get_display_profile_for_last_created_tourney()
            if display_profiles:
                display_profile_options = []
                display_profile_options.append("<option value=\"\"%s>Default settings</option>" % (" selected" if not most_recently_used_display_profile_name else ""))
                for name in sorted(display_profiles):
                    display_profile_options.append("<option value=\"%s\"%s>%s</option>" % (htmlcommon.escape(name), " selected" if name == most_recently_used_display_profile_name else "", htmlcommon.escape(name)))
                display_profile_controls_html = "<tr><td>Display profile</td><td><select name=\"displayprofile\">" + "\n".join(display_profile_options) + "</select></td></tr>"
                display_profile_controls_html += "<tr><td class=\"optionnote\" colspan=\"2\">Automatically apply the display settings from a previously-defined display profile.<br />Note that if you select a profile here, the screen shape defined in that profile will override what you selected above.</td></tr>"
            else:
                display_profile_controls_html = ""

            response.writeln("""
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
        "tourneyname" : htmlcommon.escape(tourneyname, True),
        "longtourneyname" : htmlcommon.escape(longtourneyname, True),
        "displayshapeoptionhtml" : display_shape_option_html,
        "currentyear" : time.localtime().tm_year,
        "displayprofilecontrols" : display_profile_controls_html
    })
            response.writeln("<div class=\"createtourneybuttonbox\">");
            response.writeln('<input type="submit" name="submit" value="Create Tourney" class=\"bigbutton\" />');
            response.writeln("</div>");
            response.writeln("</form>");
        response.writeln("<hr />")

    tourney_list = os.listdir(htmlcommon.dbdir);
    tourney_list = [x for x in tourney_list if (len(x) > 3 and x[-3:] == ".db")];
    if order_by in ("mtime_a", "mtime_d"):
        tourney_list = sorted(tourney_list, key=get_tourney_modified_time, reverse=(order_by == "mtime_d"));
    else:
        tourney_list = sorted(tourney_list, key=lambda x : x.lower(), reverse=(order_by == "name_d"));

    if httpreq.is_client_from_localhost():
        if tourney_list:
            response.writeln("<h2>Open existing tourney</h2>");
            print_tourney_table(response, tourney_list, "tourneysetup", True, False, False, order_by)
        else:
            response.writeln("<p>")
            response.writeln("No tourneys exist yet.");
            response.writeln("</p>")

        response.writeln("<hr>")

        try:
            response.writeln("<p>")
            response.writeln("Tournament database directory: <span class=\"fixedwidth\">%s</span>" % (htmlcommon.escape(os.path.realpath(htmlcommon.dbdir))))
            response.writeln("</p>")
        except:
            response.writeln("<p>Failed to expand tournament database directory name</p>")
    else:
        # Client is not from localhost, so display a menu of tournaments. Each
        # link goes to the Teleost display for that tournament, which is the
        # only thing non-localhost clients are allowed to access.
        response.writeln("<h2>Select tourney</h2>")
        print_tourney_table(response, tourney_list, None, False, True, True, order_by)

    response.writeln("<p>Atropine version %s</p>" % (countdowntourney.SW_VERSION))
    response.writeln("<p>Python version %d.%d.%d</p>" % tuple(sys.version_info[0:3]))

    response.writeln("</body>");
    response.writeln("</html>");
