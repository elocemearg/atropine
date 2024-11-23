#!/usr/bin/python3

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
    pass

class TourneyExistsException(UploadFailedException):
    def __init__(self, tourney_name):
        self.description = "Import rejected: tourney name \"%s\" already exists. Delete or rename the existing tourney, or rename the file, or supply a different tourney name for the imported tourney." % (tourney_name)

def print_tourney_table(response, tourney_list, order_by):
    response.writeln("<table class=\"tourneylist\">");
    response.writeln("<tr>")
    response.writeln("<th>Select</th>")
    response.writeln("<th><a href=\"?orderby=%s\">Name</a></th>" % ("name_d" if order_by == "name_a" else "name_a"))
    #response.writeln("<th>Operations</th>")
    response.writeln("<th><a href=\"?orderby=%s\">Last modified</a></th>" % ("mtime_a" if order_by == "mtime_d" else "mtime_d"))
    response.writeln("</tr>")
    for name in tourney_list:
        filename = countdowntourney.get_tourney_filename(name)
        st = os.stat(filename)
        modified_time = time.localtime(st.st_mtime)
        response.writeln("""
<tr id="tourneyrow_%(name)s" class="tourneyrow">
    <td class="tourneylistselect" style="padding: 0">
        <label for="tourneyselect_%(name)s" class="fillcontainer" style="padding-top: 5px; padding-bottom: 5px;">
            <input type="radio" id="tourneyselect_%(name)s" name="tourneyselect" class="tourneyselect" value="%(name)s">
        </label>
    </td>
    <td class="tourneylistname">
    <a href="/atropine/%(name)s/tourneysetup">%(name)s</a>
    </td>
    <td class="tourneylistmtime">%(mtime)s</td>
</tr>
""" % {
            "name" : htmlcommon.escape(name),
            "mtime" : time.strftime("%d %b %Y %H:%M", modified_time)
        })
    response.writeln("</table>")

def print_tourney_upload_form(response, form, import_tourney_failed):
    response.writeln("""
<form method="POST" enctype="multipart/form-data">
    <table class="optionstable">
    <col style="width: 8em;" />
    <tr>
    <td><label for="dbfile">Import .db file</label></td>
    <td><input type="file" onchange="checkUploadFile();" id="dbfile" name="dbfile" accept=".db"></td>
    </tr>
    <tr>
    <td><label for="uploadtourneyname">Tourney name</label></td>
    <td><input type="text" id="uploadtourneyname" name="uploadtourneyname" value="%(tourney)s"></td>
    </tr>
    <tr>
    <td></td>
    <td class="optionnote">(leave blank to use imported file name)</td>
    </tr>
    <tr>
    </table>
    <input type="submit" id="importtourneydbsubmit" name="importtourneydb" value="Import" class="bigbutton">
</form>
""" % {
        "tourney" : htmlcommon.escape(form.getfirst("uploadtourneyname", "")) if import_tourney_failed else ""
    })

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    # tourney is None for this handler
    htmlcommon.print_html_head(response, "Manage Tourneys")

    response.writeln("<body onload=\"initPage();\">")

    response.writeln("<script>")
    response.writeln(htmldialog.DIALOG_JAVASCRIPT)
    response.writeln("""
let selectedTourneyName = null;

function showDeleteDialog() {
    if (!selectedTourneyName) {
        return;
    }
    let p1 = document.createElement("P");
    let p2 = document.createElement("P");
    let p3 = document.createElement("P");
    p1.innerHTML = 'You are about to delete the database file for tourney: <span style="font-weight: bold;">' + selectedTourneyName + '</span>';
    p2.innerHTML = 'This will permanently delete the tourney along with all its players, games and scores. This cannot be undone.';
    p3.innerHTML = 'Are you sure you want to delete the <span style="font-weight: bold;">' + selectedTourneyName + '</span> tourney?';
    dialogBoxShow("deletedialog", "Delete tourney?", "Delete", "Cancel",
        "POST", "/atropine/global/managetourneys%(qs)s", "delete", [p1, p2, p3], { "tourney" : selectedTourneyName });
}

function showRenameForm() {
    let renameForm = document.getElementById("renameform");
    let mainForms = document.getElementById("mainmanageform");
    renameForm.style.display = "block";
    mainForms.style.display = "none";
}

function hideRenameForm() {
    let renameForm = document.getElementById("renameform");
    let mainForms = document.getElementById("mainmanageform");
    renameForm.style.display = "none";
    mainForms.style.display = "block";
}

function checkUploadFile() {
    let fileElement = document.getElementById("dbfile");
    let submitButton = document.getElementById("importtourneydbsubmit");
    if (fileElement.value != "" && fileElement.value.endsWith(".db")) {
        submitButton.disabled = false;
        submitButton.value = "⬆ Import";
    }
    else {
        submitButton.disabled = true;
        submitButton.value = ".db file required";
    }
}

""" % {
        "qs" : "?" + query_string
    })
    response.writeln("""
function selectTourney(tourneyName) {
    selectedTourneyName = tourneyName;

    /* Enable some controls */
    let elements = document.getElementsByClassName("enableontourneyselect");
    for (let i = 0; i < elements.length; i++) {
        elements[i].disabled = false;
    }

    /* Fill in the value attribute of some other controls */
    elements = document.getElementsByClassName("setvalueonselect");
    for (let i = 0; i < elements.length; i++) {
        elements[i].value = tourneyName;
    }

    /* Tell the user what tourney is selected */
    let selectedIndicator = document.getElementById("selectedindicator");
    selectedIndicator.innerHTML = 'Manage tourney: <span style="font-weight: bold;">' + tourneyName + '</span>';
    selectedIndicator.style.color = "black";

    /* Rewrite the action attributes of the various forms */
    let idToAction = {
        "exportdbfileform" : "/atropine/" + escape(tourneyName) + "/exportdbfile",
        "sqlpromptform" : "/atropine/" + escape(tourneyName) + "/sql"
    };
    for (let elementId in idToAction) {
        let e = document.getElementById(elementId);
        if (e) {
            e.action = idToAction[elementId];
        }
    }

    /* Highlight the correct row and lowlight the others */
    elements = document.getElementsByClassName("tourneyrow");
    for (let i = 0; i < elements.length; i++) {
        let tr = elements[i];
        if (tr.tagName.toUpperCase() == "TR") {
            if (tr.id == "tourneyrow_" + tourneyName) {
                tr.classList.add("tourneyselected");
            }
            else {
                tr.classList.remove("tourneyselected");
            }
        }
    }
}

function initPage() {
    /* Attach oninput listeners to all tourneyselect radio buttons */
    let radioButtons = document.getElementsByClassName("tourneyselect");
    for (let i = 0; i < radioButtons.length; i++) {
        let tourneyName = radioButtons[i].value;
        radioButtons[i].addEventListener("input", function(e) {
            selectTourney(tourneyName);
        })
    }

    /* If any radio button is already selected, call selectTourney() */
    for (let i = 0; i < radioButtons.length; i++) {
        if (radioButtons[i].checked) {
            selectTourney(radioButtons[i].value);
            break;
        }
    }

    checkUploadFile();
}
""")
    response.writeln("</script>")

    # Write a sidebar, but not the normal one
    htmlcommon.show_sidebar(response, None)

    response.writeln("<div class=\"mainpane\">")
    response.writeln("<h1>Manage Tourneys</h1>")

    import_tourney_failed = False

    if request_method == "POST":
        if "delete" in form:
            try:
                tourney_name = form.getfirst("tourney")
                countdowntourney.tourney_delete(tourney_name)
                htmlcommon.show_success_box(response, "Successfully deleted tourney \"%s\"" % (htmlcommon.escape(tourney_name)))
            except countdowntourney.TourneyException as e:
                htmlcommon.show_tourney_exception(response, e)
        elif "rename" in form:
            try:
                old_name = form.getfirst("oldname")
                new_name = form.getfirst("newname")
                if old_name and new_name and old_name != new_name:
                    countdowntourney.check_tourney_name_valid(old_name)
                    countdowntourney.check_tourney_name_valid(new_name)
                    old_filename = countdowntourney.get_tourney_filename(old_name)
                    new_filename = countdowntourney.get_tourney_filename(new_name)
                    if not os.path.exists(old_filename):
                        htmlcommon.show_error_text(response, "Can't rename tourney \"%s\" because it doesn't exist." % (old_name))
                    elif os.path.exists(new_filename):
                        htmlcommon.show_error_text(response, "Can't rename tourney \"%s\" to \"%s\": tourney \"%s\" already exists. Delete or rename that one first." % (old_name, new_name, new_name))
                    else:
                        os.rename(old_filename, new_filename)
                        htmlcommon.show_success_box(response, "Successfully renamed tourney \"%s\" to \"%s\"." % (old_name, new_name))
            except countdowntourney.TourneyException as e:
                htmlcommon.show_tourney_exception(response, e)
        elif "importtourneydb" in form:
            try:
                # User has given us a .db file to put in the tourneys directory.
                upload_filename = form.getfirst("dbfile", "")
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

                # Write this file to the tourneys directory
                with open(dest_path, "wb") as f:
                    f.write(upload_data)

                htmlcommon.show_success_box(response, "Successfully imported tourney \"%s\"" % (upload_tourney_name))
            except UploadFailedException as e:
                htmlcommon.show_tourney_exception(response, e)
                import_tourney_failed = True
            except countdowntourney.TourneyException as e:
                htmlcommon.show_tourney_exception(response, e)
                import_tourney_failed = True

    response.writeln("<h2>Import tourney from file</h2>")
    response.writeln("<p>If you have a .db file from some other Atropine installation which you want to use, you can import it here.</p>")
    response.writeln("<p>If you want to create a new tourney, you can do that on the <a href=\"/\">home page</a>.</p>")
    print_tourney_upload_form(response, form, import_tourney_failed)

    response.writeln("<h2>Manage existing tourneys</h2>")
    order_by = form.getfirst("orderby", "mtime_d")
    tourney_list = countdowntourney.get_tourney_list(order_by=order_by)

    if not tourney_list:
        response.writeln("<p>There are no existing tourneys.</p>")
    else:
        response.writeln("""
<div>
<div class="managetourneycontrols" style="border: 1px solid black;">
    <div class="managetourneysubform" id="selectedindicator" style="color: gray;">Select a tourney below.</div>
    <div class="managetourneysubform" id="mainmanageform">
        <form method="GET" id="exportdbfileform" action="">
            <input type="submit" class="enableontourneyselect" disabled
                value="&#x2B07; Download .db"
                title="Export the .db file for this tourney, to import into another Atropine installation or for safe keeping.">
        </form>
        <form method="GET" id="sqlpromptform" action="">
            <input type="submit" class="enableontourneyselect" disabled
            value="&#x1F527; SQL prompt"
            title="Raw SQL access to this tourney's database file. Only for emergency surgery or debugging.">
        </form>
        <button onclick="showRenameForm();" class="enableontourneyselect"
            disabled title="Give this tourney a different name.">&#x270E; Rename</button>
        <button onclick="showDeleteDialog();" class="enableontourneyselect"
            disabled title="Delete this tourney. A dialog box will ask you to confirm.">&#x1F5D1; Delete</button>
    </div>
    <div id="renameform" style="display: none;" class="managetourneysubform">
        <form method="POST" action="/atropine/global/managetourneys%(qs)s">
            <input type="hidden" name="oldname" class="setvalueonselect" value="">
            Rename to: <input type="text" class="enableontourneyselect setvalueonselect" disabled name="newname" value="">
            <input type="submit" class="enableontourneyselect" disabled name="rename" value="OK">
            <button type="button" class="enableontourneyselect" onclick="hideRenameForm();">Cancel</button>
        </form>
    </div>
</div>
</div>
""" % {
            "qs" : ("?" + urllib.parse.quote_plus(query_string)) if query_string else ""
        })

    if tourney_list:
        print_tourney_table(response, tourney_list, order_by)

    response.writeln("<p>Location for tourney database files: <span class=\"fixedwidth\">%s</span></p>" % (htmlcommon.escape(os.path.realpath(countdowntourney.get_tourneys_path()))))

    response.writeln(htmldialog.get_html("deletedialog"))

    response.writeln("</div>") #mainpane
    response.writeln("</body>")
    response.writeln("</html>")

