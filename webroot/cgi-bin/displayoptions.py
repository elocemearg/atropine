#!/usr/bin/python3

import sys;
import cgi;
import cgitb;
import os;
import cgicommon;
import urllib.request, urllib.parse, urllib.error;
import re;

def show_view_preview(tourney, form, selected_view):
    info = tourney.get_teleost_mode_info(selected_view)
    if (info):
        alt_text = info["name"]
    else:
        alt_text = ""
    cgicommon.writeln("<iframe src=\"/cgi-bin/display.py?tourney=%s&mode=%d\" height=\"300\" width=\"400\"></iframe>" % (urllib.parse.quote_plus(tourney.get_name()), selected_view))

def show_view_option_controls(tourney, form, selected_view):
    options = tourney.get_teleost_options(mode=selected_view)
    if options:
        cgicommon.writeln("<div class=\"teleostoptionheading\">Options for this screen mode</div>")
    for o in options:
        cgicommon.writeln("<div class=\"teleostoption\">")
        name_escaped = "teleost_option_" + cgicommon.escape(o.name, True)
        if o.value is None:
            value_escaped = ""
        else:
            value_escaped = cgicommon.escape(str(o.value), True)

        m = re.search("\\$CONTROL\\b", o.desc)
        if m:
            before_control = o.desc[0:m.start()]
            after_control = o.desc[m.end():]
        else:
            before_control = o.desc
            after_control = ""

        cgicommon.writeln(cgicommon.escape(before_control))
        
        if o.control_type == countdowntourney.CONTROL_NUMBER:
            cgicommon.writeln("<input type=\"text\" size=\"6\" name=\"%s\" value=\"%s\" />" % (name_escaped, value_escaped))
        elif o.control_type == countdowntourney.CONTROL_CHECKBOX:
            if o.value is not None and int(o.value):
                checked_str = "checked"
            else:
                checked_str = ""
            cgicommon.writeln("<input type=\"checkbox\" name=\"%s\" value=\"1\" %s />" % (name_escaped, checked_str))
            cgicommon.writeln("<input type=\"hidden\" name=\"%s\" value=\"1\" />" % ("exists_checkbox_" + name_escaped))

        cgicommon.writeln(cgicommon.escape(after_control))

        cgicommon.writeln("</div>")


cgitb.enable();

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/displayoptions.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Display setup: " + str(tourney_name), "style.css");

cgicommon.writeln("<body>");

cgicommon.writeln("<script>")
cgicommon.writeln("""
function clearBannerEditBox() {
    document.getElementById("bannereditbox").value = "";
}
""")
cgicommon.writeln("</script>")

cgicommon.assert_client_from_localhost()

if tourney_name is None:
    cgicommon.writeln("<h1>No tourney specified</h1>");
    cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>");
    cgicommon.writeln("</body>")
    cgicommon.writeln("</html>")
    sys.exit(0)

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

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

    if request_method == "POST":
        if "setoptions" in form:
            for name in list(form.keys()):
                if name.startswith("teleost_option_"):
                    option_name = name[15:]
                    option_value = form.getfirst(name)
                    tourney.set_teleost_option_value(option_name, option_value)
                elif name.startswith("exists_checkbox_teleost_option_"):
                    cgi_option_name = name[16:]
                    if cgi_option_name not in form:
                        tourney.set_teleost_option_value(cgi_option_name[15:], 0)
            text = form.getfirst("bannertext")
            if not text:
                tourney.clear_banner_text()
            else:
                tourney.set_banner_text(text)
        if "switchview" in form:
            tourney.set_teleost_mode(selected_view)
            teleost_modes = tourney.get_teleost_modes();
            mode_info = teleost_modes[selected_view]

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

    cgicommon.writeln("<div class=\"viewselection\">")
    cgicommon.writeln("<div class=\"viewdetails\">")
    cgicommon.writeln("<div class=\"viewdetailstext\">")
    cgicommon.writeln("<h2>")
    cgicommon.writeln(cgicommon.escape(mode_info["name"]))
    cgicommon.writeln("</h2>")
    cgicommon.writeln("<p>")
    cgicommon.writeln(cgicommon.escape(mode_info["desc"]))
    cgicommon.writeln("</p>")
    cgicommon.writeln("</div>") # viewdetailstext

    cgicommon.writeln("</div>") # viewdetails

    cgicommon.writeln("<div style=\"clear: both;\"></div>")

    cgicommon.writeln("<div class=\"viewpreviewandoptions\">")
    cgicommon.writeln("<div class=\"viewpreview\" id=\"viewpreview\">")
    show_view_preview(tourney, form, selected_view)
    if teleost_modes[selected_view].get("selected", False):
        cgicommon.writeln("<div class=\"viewpreviewcurrent\">")
        cgicommon.writeln("Currently showing")
        cgicommon.writeln("</div>")
    else:
        cgicommon.writeln("<div class=\"viewpreviewswitch\">")
        cgicommon.writeln("<form action=\"" + baseurl + "?tourney=%s&selectedview=%d\" method=\"POST\">" % (urllib.parse.quote_plus(tourney_name), selected_view))
        cgicommon.writeln("<input class=\"switchviewbutton\" type=\"submit\" name=\"switchview\" value=\"Switch to this screen mode\" />")
        cgicommon.writeln("</form>")
        cgicommon.writeln("</div>")
    cgicommon.writeln("</div>")

    cgicommon.writeln("<div class=\"viewcontrols\">")
    cgicommon.writeln("<form action=\"" + baseurl + "?tourney=%s&selectedview=%d\" method=\"POST\">" % (urllib.parse.quote_plus(tourney_name), selected_view))

    cgicommon.writeln("<div class=\"viewoptions\" id=\"viewoptions\">")
    cgicommon.writeln("<div class=\"teleostoptionheading\">Banner text</div>")
    cgicommon.writeln("<div class=\"teleostoptionblock\">")
    cgicommon.writeln("<input type=\"text\" name=\"bannertext\" id=\"bannereditbox\" value=\"%s\" size=\"40\" onclick=\"this.select();\" />" % (cgicommon.escape(banner_text, True)))
    cgicommon.writeln("<button type=\"button\" onclick=\"clearBannerEditBox();\">Clear</button>");
    cgicommon.writeln("</div>")
    show_view_option_controls(tourney, form, selected_view)
    cgicommon.writeln("</div>")

    cgicommon.writeln("<div class=\"viewsubmitbuttons\">")
    cgicommon.writeln("<div class=\"viewoptionssave\">")
    cgicommon.writeln("<input type=\"submit\" class=\"setdisplayoptionsbutton\" name=\"setoptions\" value=\"Save options\" />")
    cgicommon.writeln("</div>")
    cgicommon.writeln("</div>") # viewsubmitbuttons

    cgicommon.writeln("</form>")
    cgicommon.writeln("</div>") # viewcontrols
    cgicommon.writeln("</div>") # viewpreviewandoptions

    cgicommon.writeln("<div style=\"clear: both;\"></div>")

    cgicommon.writeln("</div>") # viewselection

    cgicommon.writeln("<div class=\"viewmenu\">")

    cgicommon.writeln("<div class=\"viewmenuheading\">Available screen modes</div>")

    menu_row_size = 5
    teleost_modes_sorted = sorted(teleost_modes, key=lambda x : (x.get("menuorder", 100000), x["num"], x["name"]))

    for idx in range(len(teleost_modes_sorted)):
        mode = teleost_modes_sorted[idx]
        if idx % menu_row_size == 0:
            if idx > 0:
                cgicommon.writeln("</div>")
            cgicommon.writeln("<div class=\"viewmenurow\">")
        classes = ["viewmenucell"]
        if mode.get("selected", False):
            # This is the view currently showing on the public display
            classes.append("viewmenucellshowing")
        elif mode["num"] == selected_view:
            # This is the view the user has clicked in the display options page
            classes.append("viewmenucellselected")
        else:
            # This is neither showing nor selected
            classes.append("viewmenucellbystander")
        cgicommon.writeln("<div class=\"%s\">" % (" ".join(classes)))
        cgicommon.writeln("<a href=\"%s?tourney=%s&selectedview=%d\">" % (baseurl, urllib.parse.quote_plus(tourney_name), mode["num"]))
        img_src = mode.get("image", None)
        if img_src:
            cgicommon.writeln("<img src=\"%s\" alt=\"%s\" title=\"%s\" />" % (
                    cgicommon.escape(img_src, True), cgicommon.escape(mode["name"], True),
                    cgicommon.escape(mode["name"], True)))
        else:
            cgicommon.writeln(cgicommon.escape(mode["name"]))
        cgicommon.writeln("</a>")
        cgicommon.writeln("</div>")

    if len(teleost_modes) > 0:
        cgicommon.writeln("</div>")

    cgicommon.writeln("</div>") #viewmenu

    cgicommon.writeln("</div>") # mainpane

except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

cgicommon.writeln("</body></html>");

sys.exit(0);

