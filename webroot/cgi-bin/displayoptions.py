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
    print("<iframe src=\"/cgi-bin/display.py?tourney=%s&mode=%d\" height=\"300\" width=\"400\"></iframe>" % (urllib.parse.quote_plus(tourney.get_name()), selected_view))

def show_view_option_controls(tourney, form, selected_view):
    options = tourney.get_teleost_options(mode=selected_view)
    if options:
        print("<div class=\"teleostoptionheading\">Options for this screen mode</div>")
    for o in options:
        print("<div class=\"teleostoption\">")
        name_escaped = "teleost_option_" + cgi.escape(o.name, True)
        if o.value is None:
            value_escaped = ""
        else:
            value_escaped = cgi.escape(str(o.value), True)

        m = re.search("\\$CONTROL\\b", o.desc)
        if m:
            before_control = o.desc[0:m.start()]
            after_control = o.desc[m.end():]
        else:
            before_control = o.desc
            after_control = ""

        print(cgi.escape(before_control))
        
        if o.control_type == countdowntourney.CONTROL_NUMBER:
            print("<input type=\"text\" size=\"6\" name=\"%s\" value=\"%s\" />" % (name_escaped, value_escaped))
        elif o.control_type == countdowntourney.CONTROL_CHECKBOX:
            if o.value is not None and int(o.value):
                checked_str = "checked"
            else:
                checked_str = ""
            print("<input type=\"checkbox\" name=\"%s\" value=\"1\" %s />" % (name_escaped, checked_str))
            print("<input type=\"hidden\" name=\"%s\" value=\"1\" />" % ("exists_checkbox_" + name_escaped))

        print(cgi.escape(after_control))

        print("</div>")


cgitb.enable();

print("Content-Type: text/html; charset=utf-8");
print("");

baseurl = "/cgi-bin/displayoptions.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;

cgicommon.print_html_head("Display setup: " + str(tourney_name), "style.css");

print("<script type=\"text/javascript\">")
print("""
function clearBannerEditBox() {
    document.getElementById("bannereditbox").value = "";
}
""")
print("</script>")

print("<body>");

cgicommon.assert_client_from_localhost()

if tourney_name is None:
    print("<h1>No tourney specified</h1>");
    print("<p><a href=\"/cgi-bin/home.py\">Home</a></p>");
    print("</body>")
    print("</html>")
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

    print("<div class=\"mainpane\">")

    print("<h1>Display Setup</h1>");

    print("<div class=\"opendisplaylink\">")
    print("""
    <a href="/cgi-bin/display.py?tourney=%s"
       target=\"_blank\">
       Open Display Window
       <img src=\"/images/opensinnewwindow.png\"
            alt=\"Opens in new window\"
            title=\"Opens in new window\" />
        </a>""" % (urllib.parse.quote_plus(tourney.name)));
    print("</div>")

    print("<div class=\"viewselection\">")
    print("<div class=\"viewdetails\">")
    print("<div class=\"viewdetailstext\">")
    print("<h2>")
    print(cgi.escape(mode_info["name"]))
    print("</h2>")
    print("<p>")
    print(cgi.escape(mode_info["desc"]))
    print("</p>")
    print("</div>") # viewdetailstext

    print("</div>") # viewdetails

    print("<div style=\"clear: both;\"></div>")

    print("<div class=\"viewpreviewandoptions\">")
    print("<div class=\"viewpreview\" id=\"viewpreview\">")
    show_view_preview(tourney, form, selected_view)
    if teleost_modes[selected_view].get("selected", False):
        print("<div class=\"viewpreviewcurrent\">")
        print("Currently showing")
        print("</div>")
    else:
        print("<div class=\"viewpreviewswitch\">")
        print("<form action=\"" + baseurl + "?tourney=%s&selectedview=%d\" method=\"POST\">" % (urllib.parse.quote_plus(tourney_name), selected_view))
        print("<input class=\"switchviewbutton\" type=\"submit\" name=\"switchview\" value=\"Switch to this screen mode\" />")
        print("</form>")
        print("</div>")
    print("</div>")

    print("<div class=\"viewcontrols\">")
    print("<form action=\"" + baseurl + "?tourney=%s&selectedview=%d\" method=\"POST\">" % (urllib.parse.quote_plus(tourney_name), selected_view))

    print("<div class=\"viewoptions\" id=\"viewoptions\">")
    print("<div class=\"teleostoptionheading\">Banner text</div>")
    print("<div class=\"teleostoptionblock\">")
    print("<input type=\"text\" name=\"bannertext\" id=\"bannereditbox\" value=\"%s\" size=\"40\" onclick=\"this.select();\" />" % (cgi.escape(banner_text, True)))
    print("<button type=\"button\" onclick=\"clearBannerEditBox();\">Clear</button>");
    print("</div>")
    show_view_option_controls(tourney, form, selected_view)
    print("</div>")

    print("<div class=\"viewsubmitbuttons\">")
    print("<div class=\"viewoptionssave\">")
    print("<input type=\"submit\" class=\"setdisplayoptionsbutton\" name=\"setoptions\" value=\"Save options\" />")
    print("</div>")
    print("</div>") # viewsubmitbuttons

    print("</form>")
    print("</div>") # viewcontrols
    print("</div>") # viewpreviewandoptions

    print("<div style=\"clear: both;\"></div>")

    print("</div>") # viewselection

    print("<div class=\"viewmenu\">")

    print("<div class=\"viewmenuheading\">Available screen modes</div>")

    menu_row_size = 5
    teleost_modes_sorted = sorted(teleost_modes, key=lambda x : (x.get("menuorder", 100000), x["num"], x["name"]))

    for idx in range(len(teleost_modes_sorted)):
        mode = teleost_modes_sorted[idx]
        if idx % menu_row_size == 0:
            if idx > 0:
                print("</div>")
            print("<div class=\"viewmenurow\">")
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
        print("<div class=\"%s\">" % (" ".join(classes)))
        print("<a href=\"%s?tourney=%s&selectedview=%d\">" % (baseurl, urllib.parse.quote_plus(tourney_name), mode["num"]))
        img_src = mode.get("image", None)
        if img_src:
            print("<img src=\"%s\" alt=\"%s\" title=\"%s\" />" % (
                    cgi.escape(img_src, True), cgi.escape(mode["name"], True),
                    cgi.escape(mode["name"], True)))
        else:
            print(cgi.escape(mode["name"]))
        print("</a>")
        print("</div>")

    if len(teleost_modes) > 0:
        print("</div>")

    print("</div>") #viewmenu

    print("</div>") # mainpane

except countdowntourney.TourneyException as e:
    cgicommon.show_tourney_exception(e);

print("</body></html>");

sys.exit(0);

