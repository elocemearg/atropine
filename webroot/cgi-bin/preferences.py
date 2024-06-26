#!/usr/bin/python3

import sys
import cgicommon
import htmltraceback
import os

htmltraceback.enable();

cgicommon.writeln("Content-Type: text/html; charset=utf-8");
cgicommon.writeln("");

baseurl = "/cgi-bin/preferences.py";
form = cgicommon.FieldStorage();
tourney_name = form.getfirst("tourney");

tourney = None;
request_method = os.environ.get("REQUEST_METHOD", "");

cgicommon.set_module_path();

import countdowntourney

cgicommon.print_html_head("Preferences");

saved_prefs = False

cgicommon.writeln("<body>")

cgicommon.assert_client_from_localhost()

cgicommon.writeln("""
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
""")

cgicommon.writeln("<h1>Global preferences</h1>")
cgicommon.writeln("<p>These preferences will apply to all tournaments administered with this installation of Atropine.</p>")

prefs = countdowntourney.get_global_preferences();

if request_method == "POST" and "saveprefs" in form:
    value = form.getfirst("resultstab")
    if value in ("nnss", "nsns", "nssn"):
        prefs.set_result_entry_tab_order(value)
    countdowntourney.set_global_preferences(prefs)
    saved_prefs = True

tab_order = prefs.get_result_entry_tab_order();

cgicommon.writeln("<div class=\"prefsdiv\">")
cgicommon.writeln("<form method=\"POST\" action=\"%s\">" % (baseurl));

cgicommon.writeln("<div class=\"prefsheading\">")
cgicommon.writeln("Tabbing order for results entry interface")
cgicommon.writeln("</div>")
cgicommon.writeln("<div class=\"prefstaborder\">")

tab_orders = [ "nnss", "nsns", "nssn" ]
for idx in range(len(tab_orders)):
    option_tab_order = tab_orders[idx]
    field_name_list = [ "Name" if x == "n" else "Score" for x in option_tab_order ]
    cgicommon.writeln("<div class=\"prefstaborderrow\">")
    cgicommon.writeln("<div class=\"prefstabordercontrol\">")
    cgicommon.writeln("<input type=\"radio\" name=\"resultstab\" id=\"resultstab_%s\" value=\"%s\" %s />" % (option_tab_order, option_tab_order, "checked" if tab_order == option_tab_order else ""))
    cgicommon.writeln("<label for=\"resultstab_%s\">" % (option_tab_order))
    cgicommon.writeln(" &rarr; ".join(field_name_list))
    cgicommon.writeln("</label>")
    cgicommon.writeln("</div>")

    cgicommon.writeln("<div class=\"prefstaborderimage\">")
    cgicommon.writeln("<label for=\"resultstab_%s\">" % (option_tab_order))
    cgicommon.writeln("<img src=\"/images/taborder%d.png\" alt=\"%s\" />" % (
            idx + 1,
            cgicommon.escape("-".join(field_name_list), True)
    ))
    cgicommon.writeln("</label>")
    cgicommon.writeln("</div>")

    cgicommon.writeln("</div>")
    cgicommon.writeln("<div class=\"prefsclear\"></div>")

cgicommon.writeln("<div class=\"prefstaborderfooter\">")
cgicommon.writeln("Saved changes will take effect after you refresh the results entry page.")
cgicommon.writeln("</div>")

cgicommon.writeln("</div>") # preferencestaborder

cgicommon.writeln("<div class=\"prefsfeedback\">")
cgicommon.writeln("<span class=\"prefssaved\" id=\"prefssavedspan\">")
if saved_prefs:
    cgicommon.writeln("Preferences saved.");
cgicommon.writeln("</span>")
cgicommon.writeln("</div>")

cgicommon.writeln("<div class=\"prefssubmitrow\">")
cgicommon.writeln("<input type=\"submit\" name=\"saveprefs\" onclick=\"change_saved_indicator(false); return true;\" value=\"Save Preferences\" />")
cgicommon.writeln("<button onclick=\"window.close();\">Close Window</button>")
cgicommon.writeln("</div>")

cgicommon.writeln("</form>")
cgicommon.writeln("</div>") # preferencesdiv


cgicommon.writeln("</body>")
cgicommon.writeln("</html>")

sys.exit(0)
