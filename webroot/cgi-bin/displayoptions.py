#!/usr/bin/python3

import sys
import os
import urllib.request, urllib.parse, urllib.error
import re

import htmltraceback
import cgicommon
import dialog

def show_now_showing_frame(tourney, is_widescreen):
    cgicommon.writeln("<iframe class=\"displaypreviewframe\" src=\"/cgi-bin/display.py?tourney=%s\" height=\"270\" width=\"%d\"></iframe>" % (
        urllib.parse.quote_plus(tourney.get_name()),
        480 if is_widescreen else 360
    ))

def show_view_preview(tourney, form, selected_view, is_widescreen):
    cgicommon.writeln("<iframe class=\"displaypreviewframe\" src=\"/cgi-bin/display.py?tourney=%s&mode=%d\" height=\"270\" width=\"%d\"></iframe>" % (
        urllib.parse.quote_plus(tourney.get_name()),
        selected_view, 480 if is_widescreen else 360
    ))

def show_live_and_preview(tourney, form, teleost_modes, showing_view, selected_view):
    tourney_name = tourney.get_name()
    is_widescreen = tourney.is_screen_shape_profile_widescreen()

    # Tell the user what mode is being shown, what mode is selected for preview
    # (if different) and if not auto, offer the user a button to return to auto.
    # We assume the "auto" display mode is number 0.
    cgicommon.writeln("<form action=\"" + baseurl + "?%s\" method=\"POST\">" % (cgicommon.escape(os.getenv("QUERY_STRING", ""))))
    cgicommon.writeln("<p>")
    cgicommon.write("You are currently <span style=\"color: green;\">showing</span> the <span style=\"font-weight: bold;\">%s</span> display mode" % (
            "?" if showing_view is None else teleost_modes[showing_view]["name"]
        )
    )
    if showing_view != selected_view:
        cgicommon.write(", and <span style=\"color: darkorange;\">previewing</span> the <span style=\"font-weight: bold;\">%s</span> display mode" % (teleost_modes[selected_view]["name"]))
    cgicommon.writeln(".")
    if showing_view != 0:
        cgicommon.writeln(" <input type=\"submit\" name=\"switchview\" value=\"Return to automatic control\" />")
    cgicommon.writeln("</p>")
    cgicommon.writeln("</form>")

    cgicommon.writeln("<div class=\"viewselection\">")
    cgicommon.writeln("<div class=\"viewpreviewandoptions\">")
    cgicommon.writeln("<div class=\"displaysetupview viewnowshowing\">")
    show_now_showing_frame(tourney, is_widescreen)
    cgicommon.writeln("<div class=\"viewpreviewcurrent\">")
    cgicommon.writeln("Now showing")
    cgicommon.writeln("</div>")
    cgicommon.writeln("</div>")
    if not teleost_modes[selected_view].get("selected", False):
        cgicommon.writeln("<div class=\"displaysetupview viewpreview\" id=\"viewpreview\">")
        show_view_preview(tourney, form, selected_view, is_widescreen)

        cgicommon.writeln("<div class=\"viewpreviewswitch\">")
        cgicommon.writeln("<form action=\"" + baseurl + "?%s\" method=\"POST\">" % (cgicommon.escape(os.getenv("QUERY_STRING", ""))))
        cgicommon.writeln("<input class=\"switchviewbutton\" type=\"submit\" name=\"switchview\" value=\"Switch to %s\" />" % ("this screen mode" if selected_view != 0 else "automatic control"))
        cgicommon.writeln("</form>")
        cgicommon.writeln("</div>") # viewpreviewswitch
        cgicommon.writeln("</div>") # viewpreview
    cgicommon.writeln("</div>") # viewpreviewandoptions
    cgicommon.writeln("</div>") # viewselection

checkbox_to_assoc_field = {
        "standings_videprinter_spell_big_scores" : "standings_videprinter_big_score_min"
}

assoc_field_to_checkbox = {
        "standings_videprinter_big_score_min" : "standings_videprinter_spell_big_scores"
}

def show_view_option_controls(options):
    if not options:
        return
    for o in options:
        disabled = False
        if o.name in assoc_field_to_checkbox:
            for oo in options:
                if oo.name == assoc_field_to_checkbox[o.name]:
                    try:
                        value = int(oo.value)
                    except ValueError:
                        value = 0
                    if not value:
                        disabled = True
                    break
        if o.name in checkbox_to_assoc_field:
            onclick_value = "var numberField = document.getElementById('%s'); var checkboxField = document.getElementById('%s'); numberField.disabled = !checkboxField.checked;" % ("teleost_option_" + checkbox_to_assoc_field[o.name], "teleost_option_" + cgicommon.escape(o.name))
        else:
            onclick_value = None
        html = o.get_html(disabled, onclick_value)
        cgicommon.writeln(html)

def show_view_thumbnail(mode, selected_view, auto_current_view, large=False):
    classes = ["viewmenucell"]
    if large:
        classes.append("viewmenucelllarge")
    if mode.get("selected", False):
        # This is the view currently showing on the public display
        classes.append("viewmenucellshowing")
    elif mode["num"] == selected_view:
        # This is the view the user has clicked in the display options page
        classes.append("viewmenucellselected")
    elif auto_current_view is not None and mode["num"] == auto_current_view:
        classes.append("viewmenucellautoshowing")
    else:
        # This is neither showing nor selected
        classes.append("viewmenucellbystander")
    cgicommon.writeln("<div class=\"%s\">" % (" ".join(classes)))
    cgicommon.writeln("<a href=\"%s?tourney=%s&selectedview=%d\">" % (baseurl, urllib.parse.quote_plus(tourney_name), mode["num"]))
    img_src = mode.get("image", None)
    if img_src:
        cgicommon.writeln("<img src=\"%s\" alt=\"%s\" title=\"%s\" />" % (
                cgicommon.escape(img_src, True), cgicommon.escape(mode["name"], True),
                cgicommon.escape(mode["desc"], True)))
    cgicommon.writeln("</a>")
    cgicommon.writeln("<br>")
    cgicommon.writeln(cgicommon.escape(mode["name"]))
    cgicommon.writeln("</div>")

# selected_view: the view the user has clicked on and is previewing, not
# necessarily the one currently showing.
# auto_current_view: None if not in Auto mode. Otherwise, the number of the
# actual view being displayed by Auto mode.
def show_view_menu(tourney, form, teleost_modes, selected_view, auto_current_view):
    menu_row_size = 6
    teleost_modes_sorted = sorted(teleost_modes, key=lambda x : (x.get("menuorder", 100000), x["num"], x["name"]))

    cgicommon.writeln("<div>")
    cgicommon.writeln("<div style=\"display: table-cell;\">")
    show_view_thumbnail(teleost_modes_sorted[0], selected_view, auto_current_view, large=True)
    cgicommon.writeln("</div>")
    cgicommon.writeln("<div style=\"display: table-cell;\">")
    cgicommon.writeln("<div>")
    for mode in teleost_modes_sorted[1:]:
        show_view_thumbnail(mode, selected_view, auto_current_view)
    cgicommon.writeln("</div>")
    cgicommon.writeln("</div>")
    cgicommon.writeln("</div>")

def emit_scripts(baseurl, profile_names, selected_profile_name):
    cgicommon.writeln("<script>")

    # Write the JavaScript we need for the dialogBoxShow() function to work...
    cgicommon.writeln(dialog.DIALOG_JAVASCRIPT)

    # Write a JavaScript list containing the names of all the display profiles
    # we have, and a string constant for the currently-selected profile. The
    # code that shows the dialog boxes will need this.
    cgicommon.writeln("const profileNames = [")
    for name in profile_names:
        cgicommon.writeln("    " + cgicommon.js_string(name) + ",")
    cgicommon.writeln("];")
    if not selected_profile_name:
        cgicommon.writeln("const selectedProfileName = null;")
    else:
        cgicommon.writeln("const selectedProfileName = %s;" % (cgicommon.js_string(selected_profile_name)))

    cgicommon.writeln("""
function clearBannerEditBox() {
    document.getElementById("bannereditbox").value = "";
}

/* Return a list of HTML elements to put in a form. The HTML elements comprise
   a drop-down box with one option for each existing display profile, plus
   optionally a "[new profile]" or "[factory defaults]" option, whose
   associated values are the empty string.
   This is a helper function used to construct the three types of dialog box
   this page can show when a display profile function button is pressed. */
function makeProfileSelectElements(helpText, dropDownText, showNewProfile, showFactoryDefaults) {
    let formElements = [];
    let dropDownLabel = document.createElement("LABEL");
    let select = document.createElement("SELECT");

    dropDownLabel.innerText = dropDownText + " ";
    for (let i = 0; i < profileNames.length; i++) {
        let name = profileNames[i];
        let opt = document.createElement("OPTION");
        opt.value = name;
        opt.innerText = name;
        if (selectedProfileName != null && name == selectedProfileName) {
            opt.selected = true;
        }
        select.appendChild(opt);
    }
    if (showNewProfile || showFactoryDefaults) {
        let opt = document.createElement("OPTION");
        opt.value = "";
        opt.innerText = showNewProfile ? "[new profile]" : "[factory defaults]";
        if (selectedProfileName == null) {
            opt.selected = true;
        }
        select.appendChild(opt);
    }
    select.name = "profilename";
    select.addEventListener("change", function (e) {
        let s = e.target;
        let profileNameDiv = document.getElementById("newprofilenamediv");
        if (profileNameDiv) {
            profileNameDiv.style.visibility = (s.value == "" ? "visible" : "hidden");
        }
    });

    let helpTextElement = document.createElement("P");
    helpTextElement.innerText = helpText;

    formElements.push(helpTextElement);

    let div = document.createElement("DIV");
    div.classList.add("formcontrolrow");
    div.appendChild(dropDownLabel);
    div.appendChild(select);
    formElements.push(div);

    if (showNewProfile) {
        let div = document.createElement("DIV");
        let label = document.createElement("LABEL");
        let editBox = document.createElement("INPUT");
        label.innerText = "New profile name: ";
        editBox.type = "text";
        editBox.name = "newprofilename";
        div.id = "newprofilenamediv";
        editBox.classList.add("focusifvisible");
        editBox.value = "";
        div.style.visibility = (selectedProfileName == null ? "visible" : "hidden");
        div.classList.add("formcontrolrow");
        div.appendChild(label);
        div.appendChild(editBox);
        formElements.push(div);
    }

    return formElements;
}

function showSaveToProfileDialog() {
    dialogBoxShow("displayoptionsdialog", "Save to profile", "Save", "Cancel",
            "POST", "%(form_action)s", "savetoprofile",
            makeProfileSelectElements(
                "The currently-saved display option settings will be saved to the profile selected below, overwriting any previous settings in that profile.",
                "Save to which profile?", true, false
            )
    );
}

function showLoadFromProfileDialog() {
    dialogBoxShow("displayoptionsdialog", "Switch to profile",
            "Switch to profile", "Cancel", "POST", "%(form_action)s", "loadfromprofile",
            makeProfileSelectElements(
                "The currently-saved display option settings will be discarded and replaced with those previously saved in the profile you select below.",
                "Switch to which profile?", false, true
            )
    );
}

function showDeleteProfileDialog() {
    dialogBoxShow("displayoptionsdialog", "Delete a profile", "Delete",
            "Cancel", "POST", "%(form_action)s", "deleteprofile",
            makeProfileSelectElements(
                "Delete profiles you no longer need. Once you delete a profile it can no longer be used.",
                "Select profile to delete:", false, false
            )
    );
}

""" % {
        "form_action" : baseurl + "?" + os.getenv("QUERY_STRING", "")
    })
    cgicommon.writeln("</script>")

###############################################################################

htmltraceback.enable();

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/displayoptions.py";
form = cgicommon.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Display setup: " + str(tourney_name), "style.css");

cgicommon.writeln("<body>");

cgicommon.assert_client_from_localhost()

if tourney_name is None:
    cgicommon.writeln("<h1>No tourney specified</h1>");
    cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>");
    cgicommon.writeln("</body>")
    cgicommon.writeln("</html>")
    sys.exit(0)

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
    teleost_modes = tourney.get_teleost_modes();

    selected_view = form.getfirst("selectedview")
    if selected_view is not None:
        try:
            selected_view = int(selected_view)
        except ValueError:
            selected_view = None

    if selected_view is not None and (selected_view < 0 or selected_view >= len(teleost_modes)):
        selected_view = None

    if selected_view is None or selected_view == "":
        selected_view = tourney.get_current_teleost_mode()

    mode_info = teleost_modes[selected_view]

    # Any exceptions that get thrown, or confirmation messages for things we
    # achieved, before we've displayed the page, will be added here for display
    # at the top of the page.
    exceptions = []
    ok_messages = []

    if request_method == "POST":
        if "setoptions" in form or "setoptionsandswitch" in form:
            # Set per-view options
            for name in list(form.keys()):
                if name.startswith("teleost_option_"):
                    option_name = name[15:]
                    option_value = form.getfirst(name)
                    tourney.set_attribute(option_name, option_value)
                elif name.startswith("exists_checkbox_teleost_option_"):
                    cgi_option_name = name[16:]
                    if cgi_option_name not in form:
                        tourney.set_attribute(cgi_option_name[15:], 0)
        if "setbanner" in form:
            text = form.getfirst("bannertext")
            if not text:
                tourney.clear_banner_text()
            else:
                tourney.set_banner_text(text)
        elif "clearbanner" in form:
            tourney.clear_banner_text()

        # Set various attributes if the user clicked the relevant button
        if "setfontprofile" in form:
            font_profile_id = form.getfirst("fontprofileselect")
            if font_profile_id is not None:
                try:
                    font_profile_id = int(font_profile_id)
                    tourney.set_display_font_profile_id(font_profile_id)
                except ValueError:
                    pass
        if "setscreenshape" in form:
            screen_shape_profile = form.getfirst("screenshapeselect")
            if screen_shape_profile is not None:
                try:
                    screen_shape_profile = int(screen_shape_profile)
                    tourney.set_screen_shape_profile_id(screen_shape_profile)
                except ValueError:
                    pass
        if "switchview" in form or "setoptionsandswitch" in form:
            tourney.set_teleost_mode(selected_view)
            teleost_modes = tourney.get_teleost_modes();
            mode_info = teleost_modes[selected_view]

        # Deal with the save, load and delete commands
        display_profile_name = form.getfirst("profilename")
        new_profile_name = form.getfirst("newprofilename")
        if not display_profile_name and new_profile_name:
            display_profile_name = new_profile_name
        if not display_profile_name:
            display_profile_name = ""

        try:
            if "savetoprofile" in form:
                tourney.save_display_profile(display_profile_name)
                ok_messages.append("Display settings saved to profile \"%s\"." % (display_profile_name))
            elif "loadfromprofile" in form:
                if not display_profile_name:
                    # Restore factory defaults
                    tourney.load_default_display_options()
                    ok_messages.append("Display settings restored from factory defaults.")
                else:
                    tourney.load_display_profile(display_profile_name)
                    ok_messages.append("Display settings imported from profile \"%s\"." % (display_profile_name))
            elif "deleteprofile" in form:
                countdowntourney.delete_display_profile(display_profile_name)
                ok_messages.append("Deleted display settings profile \"%s\"." % (display_profile_name))
        except countdowntourney.TourneyException as e:
            exceptions.append(e)

    # Get the current list of display profiles, and the currently-selected
    # profile name, and emit all the Javascript we need...
    profile_names = countdowntourney.get_display_profile_names()
    selected_profile_name = tourney.get_last_loaded_display_profile_name()
    emit_scripts(baseurl, profile_names, selected_profile_name)

    banner_text = tourney.get_banner_text()
    if banner_text is None:
        banner_text = ""

    cgicommon.show_sidebar(tourney);

    cgicommon.writeln("<div class=\"mainpane\">")
    cgicommon.writeln("<h1>Display Setup</h1>");
    cgicommon.writeln("<div class=\"opendisplaylink\">")
    cgicommon.writeln("""
    <a href="/cgi-bin/display.py?tourney=%s"
       target=\"_blank\">
       Open Display Window
       <img src=\"/images/opensinnewwindow.png\"
            alt=\"Opens in new window\"
            title=\"Opens in new window\" />
        </a>""" % (urllib.parse.quote_plus(tourney.name)));
    cgicommon.writeln("</div>")

    for exc in exceptions:
        cgicommon.show_tourney_exception(exc)
    for text in ok_messages:
        cgicommon.show_success_box(cgicommon.escape(text))


    # Banner text controls
    cgicommon.writeln("<h2>Configuration</h2>")
    cgicommon.writeln("<div class=\"displayoptsform bannercontrol\">")
    cgicommon.writeln("<form action=\"" + baseurl + "?%s\" method=\"POST\">" % (cgicommon.escape(os.getenv("QUERY_STRING", ""))))
    cgicommon.writeln("Banner text: <input type=\"text\" name=\"bannertext\" id=\"bannereditbox\" value=\"%s\" size=\"50\" onclick=\"this.select();\" />" % (cgicommon.escape(banner_text, True)))
    cgicommon.writeln("<input type=\"submit\" style=\"min-width: 60px;\" name=\"setbanner\" value=\"Set\" />")
    cgicommon.writeln("<input type=\"submit\" style=\"min-width: 60px;\" name=\"clearbanner\" value=\"Clear\" />")
    cgicommon.writeln("</form>")
    cgicommon.writeln("</div>")

    # Font set selector
    display_font_profile = tourney.get_display_font_profile_id()
    font_profile_descs = countdowntourney.DISPLAY_FONT_PROFILES
    cgicommon.writeln("""<div class=\"displayoptsform\">
<form action=\"%s?%s\" method=\"POST\">
<label for="fontprofileselect">Font width:</label>
<select name="fontprofileselect" id="fontprofileselect">""" % (baseurl, cgicommon.escape(os.getenv("QUERY_STRING", ""))))
    for i in range(len(font_profile_descs)):
        cgicommon.writeln("<option value=\"%d\" %s>%s</option>" % (i, "selected" if i == display_font_profile else "", cgicommon.escape(font_profile_descs[i]["name"])))
    cgicommon.writeln("</select>")
    cgicommon.writeln("<input type=\"submit\" name=\"setfontprofile\" value=\"Set font width\" />")
    cgicommon.writeln("</form>")
    cgicommon.writeln("</div>")

    # Screen shape selector
    screen_shape_profile = tourney.get_screen_shape_profile_id()
    screen_shape_descs = countdowntourney.SCREEN_SHAPE_PROFILES
    cgicommon.writeln("""<div class=\"displayoptsform\">
<form action=\"%s?%s\" method=\"POST\">
<label for="screenshapeselect">Optimise for screen shape:</label>
<select name="screenshapeselect" id="screenshapeselect">""" % (baseurl, cgicommon.escape(os.getenv("QUERY_STRING", ""))))
    for i in range(len(screen_shape_descs)):
        cgicommon.writeln("<option value=\"%d\" %s>%s</option>" % (i, "selected" if i == screen_shape_profile else "", cgicommon.escape(screen_shape_descs[i]["name"])))
    cgicommon.writeln("</select>")
    cgicommon.writeln("<input type=\"submit\" name=\"setscreenshape\" value=\"Set screen shape\" />")
    cgicommon.writeln("</form>")
    cgicommon.writeln("</div>")

    showing_view = None
    for mode in teleost_modes:
        if mode.get("selected", False):
            showing_view = mode["num"]
    showing_view = tourney.get_current_teleost_mode()
    if showing_view == 0:
        auto_current_view = tourney.get_effective_teleost_mode()
    else:
        auto_current_view = None

    cgicommon.writeln("<h2>Display window</h2>")
    show_live_and_preview(tourney, form, teleost_modes, showing_view, selected_view)
    cgicommon.writeln("<div style=\"margin-top: 20px; clear: both;\"></div>")

    show_view_menu(tourney, form, teleost_modes, selected_view, auto_current_view)
    cgicommon.writeln("<div style=\"clear: both;\"></div>")

    cgicommon.writeln("<div class=\"viewmenu\">")
    cgicommon.writeln("<div class=\"viewdetails\">")
    #cgicommon.writeln("<div class=\"viewmenuheading\">Select screen mode</div>")
    cgicommon.writeln("<div class=\"viewdetailstext\">")
    cgicommon.writeln("<span style=\"font-weight: bold;\">")
    cgicommon.write(cgicommon.escape(mode_info["name"]))
    cgicommon.writeln(": </span>");
    cgicommon.writeln(cgicommon.escape(mode_info["desc"]))
    cgicommon.writeln("</div>") # viewdetailstext
    cgicommon.writeln("</div>") # viewdetails

    options = tourney.get_teleost_options(mode=selected_view)
    if options:
        cgicommon.writeln("<h3>Options for the <span style=\"font-weight: bold;\">%s</span> display mode</h3>" % ("?" if selected_view is None or selected_view < 0 or selected_view >= len(teleost_modes) else cgicommon.escape(teleost_modes[selected_view]["name"])))
        cgicommon.writeln("<div class=\"viewcontrols\">")
        cgicommon.writeln("<form action=\"" + baseurl + "?%s\" method=\"POST\">" % (cgicommon.escape(os.getenv("QUERY_STRING", ""))))
        cgicommon.writeln("<div class=\"viewoptions\" id=\"viewoptions\">")
        show_view_option_controls(options)
        cgicommon.writeln("</div>")

        cgicommon.writeln("<div class=\"viewsubmitbuttons\">")
        cgicommon.writeln("<div class=\"viewoptionssave\">")
        cgicommon.writeln("<input type=\"submit\" class=\"displayoptionsbutton\" name=\"setoptions\" value=\"Apply options\" />")
        if not teleost_modes[selected_view].get("selected", False):
            cgicommon.writeln("<input type=\"submit\" class=\"displayoptionsbutton\" name=\"setoptionsandswitch\" value=\"Apply options and switch to %s\" />" % (cgicommon.escape(teleost_modes[selected_view]["name"])))
        cgicommon.writeln("</div>")
        cgicommon.writeln("</div>") # viewsubmitbuttons

        cgicommon.writeln("</form>")
        cgicommon.writeln("</div>") # viewcontrols
    cgicommon.writeln("</div>")

    # Display profile save/load controls
    profile_names = countdowntourney.get_display_profile_names()
    selected_profile_name = tourney.get_last_loaded_display_profile_name()

    cgicommon.writeln("<h2>Display profiles</h2>")
    cgicommon.writeln("<p>Atropine can remember your favourite display option settings and apply them to all tourneys you create with this Atropine installation.</p>")
    cgicommon.writeln("<p>To do this, save the settings to a profile below. If you want to save the current settings to a profile, make sure you've applied them above first.</p>")
    cgicommon.writeln("<div class=\"displayoptsform\">")
    cgicommon.writeln("<button id=\"savetoprofile\" class=\"displayoptionsbutton\" onclick=\"showSaveToProfileDialog();\">&#x1F4BE; Save to profile...</button>")
    cgicommon.writeln("<button id=\"loadfromprofile\" class=\"displayoptionsbutton\" onclick=\"showLoadFromProfileDialog();\">&#x1F4C2; Switch to profile...</button>")

    if profile_names:
        cgicommon.writeln("<button id=\"deleteprofile\" class=\"displayoptionsbutton\" onclick=\"showDeleteProfileDialog();\">&#x1F5D1; Delete a profile...</button>")
    cgicommon.writeln("</div>")

    cgicommon.writeln("<div style=\"margin-bottom: 50px;\"></div>")

    cgicommon.writeln("</div>") # mainpane

    # Emit the currently non-displayed dialog box, which will pop up if the
    # user presses any of the save, restore or delete profile options.
    cgicommon.writeln(dialog.get_html("displayoptionsdialog"))

except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

cgicommon.writeln("</body></html>");

sys.exit(0);

