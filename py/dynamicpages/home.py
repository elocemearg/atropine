#!/usr/bin/python3

import sys
import os
import time
import urllib.parse

import htmlcommon
import htmldialog
import countdowntourney

class UploadFailedException(Exception):
    pass

class InvalidFilenameException(UploadFailedException):
    description = "Import rejected: tourney filename must end with .db"

class TourneyExistsException(UploadFailedException):
    def __init__(self, tourney_name):
        self.description = "Import rejected: tourney name \"%s\" already exists. Delete or rename the existing tourney, or rename the file, or supply a different tourney name for the imported tourney." % (tourney_name)

class NoTourneyFileException(UploadFailedException):
    description = "Import failed: no .db file provided."

def int_or_none(s):
    try:
        return int(s);
    except ValueError:
        return None;

def print_tourney_table(response, tourney_list, destination_page,
        show_last_modified, show_export_html_link=False,
        show_display_link=False, show_advanced_link=False, order_by="mtime_d"):
    response.writeln("<table class=\"tourneylist\">");
    response.writeln("<tr>")
    response.writeln("<th><a href=\"?orderby=%s\">Name</a></th>" % ("name_d" if order_by == "name_a" else "name_a"))

    if show_last_modified:
        response.writeln("<th><a href=\"?orderby=%s\">Last modified</a></th>" % ("mtime_a" if order_by == "mtime_d" else "mtime_d"))

    if show_display_link or show_export_html_link:
        response.writeln("<th colspan=\"%d\">Useful links</th>" % ( 2 if show_display_link and show_export_html_link else 1 ))

    if show_advanced_link:
        response.writeln("<th></th>")

    response.writeln("</tr>")
    for name in tourney_list:
        filename = countdowntourney.get_tourney_filename(name)
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

        if show_advanced_link:
            response.writeln("""
<td class="tourneylistadvanced">
<div class="contextmenubuttoncontainer">
<button class="contextmenubutton moretourneyactions" data-tourney="%s">...</button>
</div>
</td>""" % (htmlcommon.escape(name)))
        response.writeln("</tr>")
    response.writeln("</table>");


def import_tourney(form):
    upload_filename = form.getfirst("dbfile", "")
    if not upload_filename:
        raise NoTourneyFileException()
    upload_tourney_name = form.getfirst("uploadtourneyname", "")
    if not upload_tourney_name:
        # User didn't specify a tourney name, so infer it from the filename
        if not upload_filename.lower().endswith(".db"):
            raise InvalidFilenameException()
        upload_tourney_name = os.path.basename(upload_filename[:-3])

    if upload_tourney_name.endswith(".db"):
        # User has specified the .db suffix on the tourney name.
        # Not required, but we can see what they mean.
        upload_tourney_name = upload_tourney_name[:-3]

    # Check the proposed tourney name is valid and doesn't already exist
    countdowntourney.check_tourney_name_valid(upload_tourney_name)
    dest_path = countdowntourney.get_tourney_filename(upload_tourney_name)
    if os.path.exists(dest_path):
        raise TourneyExistsException(upload_tourney_name)

    # Get the data for this uploaded file
    upload_data = form.get_file_data("dbfile")
    if not upload_data:
        raise NoTourneyFileException()

    # Write this file to the tourneys directory
    with open(dest_path, "wb") as f:
        f.write(upload_data)

    return upload_tourney_name


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

    tourney_created = False
    error_texts = []
    exceptions = []
    successes = []

    if httpreq.is_client_from_localhost():
        if request_method == "POST":
            try:
                if "createtourney" in form and tourneyname:
                    # We've been asked to create a new tourney.
                    tourney = countdowntourney.tourney_create(tourneyname, load_display_profile_name=display_profile_name)
                    if longtourneyname:
                        tourney.set_full_name(longtourneyname)
                    if not display_profile_name:
                        tourney.set_screen_shape_profile_id(displayshape)
                    tourney.close()
                    tourney_created = True
                elif "renametourney" in form:
                    # We've been asked to rename an existing tourney.
                    old_name = form.getfirst("oldname")
                    new_name = form.getfirst("newname")
                    if old_name and new_name and old_name != new_name:
                        countdowntourney.check_tourney_name_valid(old_name)
                        countdowntourney.check_tourney_name_valid(new_name)
                        old_filename = countdowntourney.get_tourney_filename(old_name)
                        new_filename = countdowntourney.get_tourney_filename(new_name)
                        if not os.path.exists(old_filename):
                            error_texts.append("Can't rename tourney \"%s\" because it doesn't exist." % (old_name))
                        elif os.path.exists(new_filename):
                            error_texts.append("Can't rename tourney \"%s\" to \"%s\": tourney \"%s\" already exists. Delete or rename that one first." % (old_name, new_name, new_name))
                        else:
                            os.rename(old_filename, new_filename)
                            successes.append("Successfully renamed tourney \"%s\" to \"%s\"." % (old_name, new_name))
                elif "deletetourney" in form:
                    # We've been asked to delete an existing tourney.
                    tourney_name = form.getfirst("tourneyname")
                    countdowntourney.tourney_delete(tourney_name)
                    successes.append("Successfully deleted tourney \"%s\"" % (htmlcommon.escape(tourney_name)))
                elif "importtourney" in form:
                    # We've been given what we expect to be an SQLite3 .db file
                    # to import into the tourney directory.
                    try:
                        upload_tourney_name = import_tourney(form)
                        successes.append("Successfully imported tourney \"%s\"" % (upload_tourney_name))
                    except UploadFailedException as e:
                        exceptions.append(e)
            except countdowntourney.TourneyException as e:
                exceptions.append(e)

    response.writeln("<body onload=\"initPage();\">");
    response.writeln("<script>")

    # Include the supporting scripts for dialog boxes
    response.writeln(htmldialog.DIALOG_JAVASCRIPT)

    response.writeln("""

let moreActionsMenu = null;

function showMoreTourneyActionsMenu(button, container, tourneyName) {
    container.appendChild(moreActionsMenu);
    moreActionsMenu.style.display = "block";

    /* Elements of class contextmenuitempagelink are links which need their
       href attribute rewritten to point to the page indicated by the
       element's data-page attribute, of the relevant tourney. */
    let menuItems = moreActionsMenu.getElementsByClassName("contextmenuitempagelink");
    for (let i = 0; i < menuItems.length; i++) {
        menuItems[i].href = "/atropine/" + tourneyName + "/" + menuItems[i].getAttribute("data-page");
    }
    moreActionsMenu.setAttribute("data-tourney", tourneyName);

    let openTourneyItems = moreActionsMenu.getElementsByClassName("contextmenuitemopentourney");
    for (let i = 0; i < openTourneyItems.length; i++) {
        openTourneyItems[i].innerText = 'Open tourney "' + tourneyName + '"';
    }
}

function hideMoreTourneyActionsMenu(parentElement) {
    if (moreActionsMenu.parentElement) {
        parentElement.removeChild(moreActionsMenu);
    }
    moreActionsMenu.style.display = "none";
}

function contextMenuShowRenameDialog() {
    let tourneyName = moreActionsMenu.getAttribute("data-tourney");

    let p1 = document.createElement("P");
    let p2 = document.createElement("P");
    p1.innerHTML = 'Enter the new name for the <span style="font-weight: bold;">' + tourneyName + "</span> tourney.";
    p2.innerHTML = "The new name may only contain letters, numbers, underscores and hyphens, must not be blank, and must not be the name of an already-existing tourney.";

    let controlRow = document.createElement("DIV");
    let label = document.createElement("LABEL");
    let textBox = document.createElement("INPUT");
    label.innerText = "New name ";
    textBox.type = "text";
    textBox.name = "newname";
    textBox.value = tourneyName;
    controlRow.classList.add("formcontrolrow");
    controlRow.appendChild(label);
    controlRow.appendChild(textBox);

    dialogBoxShow("renametourneydialog", "Rename tourney", "Rename", "Cancel",
        "POST", null, "renametourney", [p1, p2, controlRow],
        { "oldname" : tourneyName });
}

function contextMenuShowDeleteDialog() {
    let tourneyName = moreActionsMenu.getAttribute("data-tourney");

    let p1 = document.createElement("P");
    let p2 = document.createElement("P");
    let p3 = document.createElement("P");
    p1.innerHTML = 'You are about to delete the database file for: <span style="font-weight: bold;">' + tourneyName + "</span>";
    p2.innerHTML = "This will permanently delete the tourney along with all its players, games and scores. This cannot be undone.";
    p3.innerHTML = 'Are you sure you want to delete <span style="font-weight: bold;">' + tourneyName + "</span>?";

    dialogBoxShow("deletetourneydialog", "Delete tourney?", "Delete", "Cancel",
        "POST", null, "deletetourney", [ p1, p2, p3 ], { "tourneyname" : tourneyName });
}

function showImportTourneyDialog() {
    let p1 = document.createElement("P");
    p1.innerHTML = "If you have a tourney .db file from another Atropine installation which you want to use, you can import it here.";

    let fileRow = document.createElement("DIV");
    let nameRow = document.createElement("DIV");
    let nameNoteRow = document.createElement("DIV");

    let fileLabel = document.createElement("LABEL");
    let nameLabel = document.createElement("LABEL");
    let fileInput = document.createElement("INPUT");
    let nameInput = document.createElement("INPUT");

    fileLabel.innerHTML = "Select .db file to import: ";
    nameLabel.innerHTML = "Tourney name: ";
    nameNoteRow.innerHTML = "Leave the tourney name blank to infer it from the imported file name.";
    nameNoteRow.classList.add("optionnote");
    fileInput.type = "file";
    fileInput.accept = ".db";
    fileInput.name = "dbfile";
    nameInput.type = "text";
    nameInput.value = "";
    nameInput.name = "uploadtourneyname";

    fileRow.classList.add("formcontrolrow");
    nameRow.classList.add("formcontrolrow");
    nameNoteRow.classList.add("formcontrolrow");

    fileRow.appendChild(fileLabel);
    fileRow.appendChild(fileInput);
    nameRow.appendChild(nameLabel);
    nameRow.appendChild(nameInput);

    dialogBoxShow("importtourneydialog", "Import tourney from .db file",
        "Import", "Cancel", "POST", null, "importtourney",
        [ p1, fileRow, nameRow, nameNoteRow ], {}, "multipart/form-data");
}

function initPage() {
    let tourneyNameBox = document.getElementById("tourneyname");
    if (tourneyNameBox) {
        tourneyNameBox.focus();
        tourneyNameBox.select();
    }

    if (moreActionsMenu == null) {
        moreActionsMenu = document.getElementById("moreactionsmenu");
    }
    let tourneyMoreButtons = document.getElementsByClassName("moretourneyactions");
    for (let i = 0; i < tourneyMoreButtons.length; i++) {
        let button = tourneyMoreButtons[i];
        let tourneyName = button.getAttribute("data-tourney");
        button.addEventListener("click", function(e) {
            showMoreTourneyActionsMenu(button, button.parentElement, tourneyName);
        });
    }

    /* If the user clicks anything that isn't a moretourneyactions button or
       a menu option from that button, hide the context menu. */
    document.body.addEventListener("click", function (e) {
        let target = e.target;
        while (target != null) {
            if (target == moreActionsMenu ||
                    target.classList.contains("contextmenu") ||
                    target.classList.contains("contextmenuitem") ||
                    target.classList.contains("contextmenubutton") ||
                    target.classList.contains("contextmenubuttoncontainer")) {
                break;
            }
            target = target.parentElement;
        }
        if (target == null) {
            hideMoreTourneyActionsMenu(moreActionsMenu.parentElement);
        }
    });
""")
    if tourney_created:
        response.writeln("""
        /* Redirect the user to the new tourney they just created */
        setTimeout(function() {
            window.location.replace("/atropine/%s/tourneysetup");
        }, 0);
        """ % (htmlcommon.escape(tourneyname)))
    response.writeln("""
}
</script>
""")

    # If we just created a tourney, we're redirecting to its setup page.
    if tourney_created:
        response.writeln("<p>");
        response.writeln('You should be redirected to your new tourney semi-immediately. If not, <a href="/atropine/%s/tourneysetup">click here to continue</a>.' % htmlcommon.escape(tourneyname));
        response.writeln("</p>");
        response.writeln("</body></html>")
        return

    # Write the special barely-there sidebar for when we don't have a tourney
    htmlcommon.show_sidebar(response, None)

    response.writeln("<div class=\"mainpane\">")
    response.writeln("<h1>Welcome to Atropine</h1>");

    # If we were asked to do something, tell the user how it went
    for e in exceptions:
        htmlcommon.show_tourney_exception(response, e)
    for txt in error_texts:
        htmlcommon.show_error_text(response, txt)
    for txt in successes:
        htmlcommon.show_success_box(response, txt)

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
            response.writeln('<input type="submit" name="createtourney" value="Create Tourney" class=\"bigbutton\" />');
            response.writeln("</div>");
            response.writeln("</form>");
        response.writeln("<hr />")

    tourney_list = countdowntourney.get_tourney_list(order_by=order_by)

    if httpreq.is_client_from_localhost():
        manage_qs = ""
        if order_by != "mtime_d":
            manage_qs = "?orderby=" + urllib.parse.quote_plus(order_by)

        if tourney_list:
            response.writeln("<h2>Open existing tourney</h2>");
            print_tourney_table(response, tourney_list, "tourneysetup", True, False, False, True, order_by)
        else:
            response.writeln("""
<p>
No tourneys exist yet.
</p>""")

        response.writeln("""
<p>
<button onclick="showImportTourneyDialog();">Import tourney from .db file...</button>
</p>""")

        response.writeln("<hr>")

        try:
            response.writeln("<p>")
            response.writeln("Location for tourney database files: <span class=\"fixedwidth\">%s</span>" % (htmlcommon.escape(os.path.realpath(countdowntourney.get_tourneys_path()))))
            response.writeln("</p>")
        except:
            response.writeln("<p>Failed to expand tournament database directory name</p>")
    else:
        # Client is not from localhost, so display a menu of tournaments. Each
        # link goes to the Teleost display for that tournament, which is the
        # only thing non-localhost clients are allowed to access.
        response.writeln("<h2>Select tourney</h2>")
        print_tourney_table(response, tourney_list, None, False, True, True, False, order_by)

    response.writeln("</div>") #mainpane

    # Per-tourney popup menu for the "more actions" button
    response.writeln("""
    <div id="moreactionsmenu" class="contextmenu" style="display: none;">
        <a class="contextmenuitem contextmenuitempagelink contextmenuitemopentourney" data-page="tourneysetup" href="/atropine/TOURNEYNAME/exportdbfile">Open tourney</a>
        <a class="contextmenuitem contextmenuitempagelink" data-page="exportdbfile" href="/atropine/TOURNEYNAME/exportdbfile">Export .db file</a>
        <a class="contextmenuitem contextmenuitempagelink" data-page="sql" href="/atropine/TOURNEYNAME/sql" target="_blank">SQL prompt</a>
        <button class="contextmenuitem" onclick="contextMenuShowRenameDialog();">Rename...</button>
        <button class="contextmenuitem" onclick="contextMenuShowDeleteDialog();">Delete...</button>
    </div>
""")

    # HTML for Rename and Delete dialog boxes, initially hidden
    response.writeln(htmldialog.get_html("renametourneydialog"))
    response.writeln(htmldialog.get_html("deletetourneydialog"))

    # HTML for db import dialog box, initially hidden
    response.writeln(htmldialog.get_html("importtourneydialog"))

    response.writeln("</body>");
    response.writeln("</html>");
