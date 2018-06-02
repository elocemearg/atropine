#!/usr/bin/python

import sys
import cgicommon
import cgi
import cgitb
import os

cgitb.enable();

print "Content-Type: text/html; charset=utf-8";
print "";

baseurl = "/cgi-bin/preferences.py";
form = cgi.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

cgicommon.print_html_head("Preferences");

saved_prefs = False

print "<body>"

print """
<script>
function change_saved_indicator(on) {
    var control = document.getElementById("prefssavedspan");
    if (on) {
        control.innerHTML = "Preferences saved.";
    }
    else {
        control.innerHTML = "";
    }
}
</script>
"""

print "<h1>Global preferences</h1>"
print "<p>These preferences will apply to all tournaments administered with this installation of Atropine.</p>"

prefs = cgicommon.get_global_preferences();

if request_method == "POST" and "saveprefs" in form:
    value = form.getfirst("resultstab")
    if value in ("nnss", "nsns", "nssn"):
        prefs.set_result_entry_tab_order(value)
    cgicommon.set_global_preferences(prefs)
    saved_prefs = True

tab_order = prefs.get_result_entry_tab_order();

print "<div class=\"prefsdiv\">"
print "<form method=\"POST\" action=\"%s\">" % (baseurl);

print "<div class=\"prefsheading\">"
print "Tabbing order for results entry interface"
print "</div>"
print "<div class=\"prefstaborder\">"

tab_orders = [ "nnss", "nsns", "nssn" ]
for idx in range(len(tab_orders)):
    option_tab_order = tab_orders[idx]
    field_name_list = [ "Name" if x == "n" else "Score" for x in option_tab_order ]
    print "<div class=\"prefstaborderrow\">"
    print "<div class=\"prefstabordercontrol\">"
    print "<input type=\"radio\" name=\"resultstab\" id=\"resultstab_%s\" value=\"%s\" %s />" % (option_tab_order, option_tab_order, "checked" if tab_order == option_tab_order else "")
    print "<label for=\"resultstab_%s\">" % (option_tab_order)
    print " &rarr; ".join(field_name_list)
    print "</label>"
    print "</div>"

    print "<div class=\"prefstaborderimage\">"
    print "<label for=\"resultstab_%s\">" % (option_tab_order)
    print "<img src=\"/images/taborder%d.png\" alt=\"%s\" />" % (
            idx + 1,
            cgi.escape("-".join(field_name_list), True)
    )
    print "</label>"
    print "</div>"

    print "</div>"
    print "<div class=\"prefsclear\"></div>"

print "<div class=\"prefstaborderfooter\">"
print "Saved changes will take effect after you refresh the results entry page."
print "</div>"

print "</div>" # preferencestaborder

print "<div class=\"prefsfeedback\">"
print "<span class=\"prefssaved\" id=\"prefssavedspan\">"
if saved_prefs:
    print "Preferences saved.";
print "</span>"
print "</div>"

print "<div class=\"prefssubmitrow\">"
print "<input type=\"submit\" name=\"saveprefs\" onclick=\"change_saved_indicator(false); return true;\" value=\"Save Preferences\" />"
print "<button onclick=\"window.close();\">Close Window</button>"
print "</div>"

print "</form>"
print "</div>" # preferencesdiv


print "</body>"
print "</html>"

sys.exit(0)
