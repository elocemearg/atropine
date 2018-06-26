#!/usr/bin/python

import sys;
import cgi;
import cgitb;
import os;
import cgicommon;
import urllib;
import re;

cgitb.enable();

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/teleost.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney;
import teleostcolours;

cgicommon.print_html_head("Display control: " + str(tourney_name));

print "<body>";

print """
<script type="text/javascript">
//<![CDATA[
function fingerpoken(show) {
    var elements = document.getElementsByClassName("fingerpokenzeug");
    for (var i = 0; i < elements.length; ++i) {
        if (show) {
            elements[i].style.display = "block";
        }
        else {
            elements[i].style.display = "none";
        }
    }
    var button = document.getElementById("fingerpokenbutton");
    if (show) {
        button.setAttribute("value", "Hide advanced settings");
        button.setAttribute("onclick", "fingerpoken(false);");
    }
    else {
        button.setAttribute("value", "Show advanced settings");
        button.setAttribute("onclick", "fingerpoken(true);");
    }

    var hidden_control = document.getElementById("showadvanced");
    hidden_control.setAttribute("value", show ? "1" : "0");
}
//]]>
</script>
"""

if tourney_name is None:
    print "<h1>No tourney specified</h1>";
    print "<p><a href=\"/cgi-bin/home.py\">Home</a></p>";
else:
    try:
        tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir);

        show_advanced = False

        if request_method == "POST":
            mode = form.getfirst("mode");
            auto_use_vertical = form.getfirst("autousevertical")
            auto_use_table_index = form.getfirst("autousetableindex")
            animate_scroll = form.getfirst("animatescroll")
            palette_name = form.getfirst("palette")
            banner_text = form.getfirst("bannertext")
            show_advanced = form.getfirst("showadvanced")

            if mode is not None:
                try:
                    mode = int(mode);
                    tourney.set_teleost_mode(mode);
                except ValueError:
                    pass;
            if auto_use_vertical is not None:
                try:
                    auto_use_vertical = int(auto_use_vertical)
                    tourney.set_auto_use_vertical(auto_use_vertical != 0)
                except ValueError:
                    pass
            else:
                tourney.set_auto_use_vertical(False)

            if auto_use_table_index is not None:
                try:
                    auto_use_table_index = int(auto_use_table_index)
                    tourney.set_auto_use_table_index(auto_use_table_index != 0)
                except ValueError:
                    pass
            else:
                tourney.set_auto_use_table_index(False)

            if animate_scroll is not None:
                try:
                    animate_scroll = int(animate_scroll)
                    tourney.set_teleost_animate_scroll(animate_scroll != 0)
                except ValueError:
                    pass
            else:
                tourney.set_teleost_animate_scroll(False)

            if palette_name is not None:
                tourney.set_teleost_colour_palette(palette_name)

            if banner_text is not None:
                banner_text = banner_text.strip()
            if not banner_text:
                tourney.clear_banner_text()
            else:
                tourney.set_banner_text(banner_text)

            if show_advanced is not None:
                try:
                    show_advanced = int(show_advanced)
                except ValueError:
                    pass
            else:
                show_advanced = False

            for name in form.keys():
                if name.startswith("teleost_option_"):
                    option_name = name[15:]
                    option_value = form.getfirst(name)
                    tourney.set_teleost_option_value(option_name, option_value)


        banner_text = tourney.get_banner_text()
        if banner_text is None:
            banner_text = ""

        cgicommon.show_sidebar(tourney);

        print("<div class=\"mainpane\">")


        views = tourney.get_teleost_modes();
        current_palette_name = tourney.get_teleost_colour_palette()
        if not current_palette_name:
            current_palette_name = "Standard"

        print "<h1>Display control</h1>";

        print "<p>"
        print "This page controls what Teleost shows and how it is shown, if you have Teleost running."
        print "</p>"

        print "<p>"
        print "<a href=\"/cgi-bin/display.py?tourney=%s\" target=\"_blank\">New Teleost Screen (experimental)</a>" % (urllib.quote_plus(tourney_name))
        print "</p>"

        print "<form action=\"/cgi-bin/teleost.py?tourney=%s\" method=\"POST\">" % urllib.quote_plus(tourney_name);
        print("<h2>Banner</h2>")
        print("<p>If you want to display a message at the top of the screen, enter it here. To remove the banner, make it blank. The current banner text is also shown in the sidebar to remind you it's active.</p>")
        print("<p>")
        print("<input type=\"text\" name=\"bannertext\" value=\"%s\" size=\"40\" />" % (cgi.escape(banner_text, True)))
        print("</p>")

        print "<h2>Select current view</h2>"
        print "<p>"
        print "<input type=\"button\" name=\"advanced\" id=\"fingerpokenbutton\" value=\"%s advanced settings\" onclick=\"fingerpoken(%s);\" />" % ("Hide" if show_advanced else "Show", "false" if show_advanced else "true");
        print "<input type=\"hidden\" name=\"showadvanced\" id=\"showadvanced\" value=\"%d\" />" % (1 if show_advanced else 0)
        print "</p>"
        for v in views:
            view_num = v.get("num", -1);
            view_name = v.get("name", "View %d" % view_num);
            view_desc = v.get("desc", "");
            view_selected = v.get("selected", False);
            print "<div>"
            print "<input type=\"radio\" name=\"mode\" value=\"%d\" %s />" % (view_num, "checked" if view_selected else "");
            print "<strong>%s</strong>: %s" % (cgi.escape(view_name), cgi.escape(view_desc));
            print "</div>"
            if view_num == 0:
                use_vertical = tourney.get_auto_use_vertical()
                use_table_index = tourney.get_auto_use_table_index()
                print "<div class=\"teleostoptionblock\">"
                print "<div class=\"teleostoption\">"
                print "<input type=\"checkbox\" name=\"autousevertical\" value=\"1\" %s /> Use vertical standings/results format between rounds regardless of table size" % ("checked" if use_vertical else "")
                print "</div>"
                print "<div class=\"teleostoption\">"
                print "<input type=\"checkbox\" name=\"autousetableindex\" value=\"1\" %s /> Use name-to-table index at start of round rather than fixtures view" % ("checked" if use_table_index else "")
                print "</div>"
                print "</div>"
            else:
                options = tourney.get_teleost_options(view_num)
                print "<div class=\"teleostoptionblock fingerpokenzeug\" style=\"display: %s\">" % ("block" if show_advanced else "None")
                for o in options:
                    print "<div class=\"teleostoption\">"
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

                    print cgi.escape(before_control)
                    
                    if o.control_type == countdowntourney.CONTROL_NUMBER:
                        print "<input type=\"text\" size=\"6\" name=\"%s\" value=\"%s\" />" % (name_escaped, value_escaped)
                    elif o.control_type == countdowntourney.CONTROL_CHECKBOX:
                        if o.value is not None and int(o.value):
                            checked_str = "checked"
                        else:
                            checked_str = ""
                        print "<input type=\"checkbox\" name=\"%s\" value=\"1\" %s />" % (name_escaped, checked_str)

                    print cgi.escape(after_control)

                    print "</div>"
                print "</div>"

        print "<h2>Select colour scheme</h2>"
        print "<p>"
        for palette_name in teleostcolours.list_palettes():
            print "<input type=\"radio\" name=\"palette\" value=\"%s\" %s /> %s<br />" % (cgi.escape(palette_name, True), "checked" if current_palette_name == palette_name else "", cgi.escape(palette_name))
        print "</p>"

        print "<h2>Other</h2>"
        print "<p>"
        print "<input type=\"checkbox\" name=\"animatescroll\" value=\"1\" %s /> Animate page scrolling<br />" % ("checked" if tourney.get_teleost_animate_scroll() else "")
        print "</p>"

        print "<p>"
        print "<input type=\"submit\" name=\"submit\" value=\"Apply Settings\" />";
        print "</p>"
        print "</form>";

        print "</div>";

    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);

print "</body></html>";

sys.exit(0);

