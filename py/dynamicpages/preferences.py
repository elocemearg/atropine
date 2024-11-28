#!/usr/bin/python3

import htmlcommon
import countdowntourney

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    # tourney is None for this handler

    htmlcommon.print_html_head(response, "Preferences", othercssfiles=["preferences.css"])

    saved_prefs = False

    response.writeln("<body>")

    response.writeln("""
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

    response.writeln("<h1>Global preferences</h1>")
    response.writeln("<p>These preferences will apply to all tournaments administered with this installation of Atropine.</p>")

    prefs = countdowntourney.get_global_preferences();

    if request_method == "POST" and "saveprefs" in form:
        value = form.getfirst("resultstab")
        if value in ("nnss", "nsns", "nssn"):
            prefs.set_result_entry_tab_order(value)
        countdowntourney.set_global_preferences(prefs)
        saved_prefs = True

    tab_order = prefs.get_result_entry_tab_order();

    response.writeln("<div class=\"prefsdiv\">")
    response.writeln("<form method=\"POST\">");

    response.writeln("<div class=\"prefsheading\">")
    response.writeln("Tabbing order for results entry interface")
    response.writeln("</div>")
    response.writeln("<div class=\"prefstaborder\">")

    tab_orders = [ "nnss", "nsns", "nssn" ]
    for idx in range(len(tab_orders)):
        option_tab_order = tab_orders[idx]
        field_name_list = [ "Name" if x == "n" else "Score" for x in option_tab_order ]
        response.writeln("<div class=\"prefstaborderrow\">")
        response.writeln("<div class=\"prefstabordercontrol\">")
        response.writeln("<input type=\"radio\" name=\"resultstab\" id=\"resultstab_%s\" value=\"%s\" %s />" % (option_tab_order, option_tab_order, "checked" if tab_order == option_tab_order else ""))
        response.writeln("<label for=\"resultstab_%s\">" % (option_tab_order))
        response.writeln(" &rarr; ".join(field_name_list))
        response.writeln("</label>")
        response.writeln("</div>")

        response.writeln("<div class=\"prefstaborderimage\">")
        response.writeln("<label for=\"resultstab_%s\">" % (option_tab_order))
        response.writeln("<img src=\"/images/taborder%d.png\" alt=\"%s\" />" % (
                idx + 1,
                htmlcommon.escape("-".join(field_name_list), True)
        ))
        response.writeln("</label>")
        response.writeln("</div>")

        response.writeln("</div>")
        response.writeln("<div class=\"prefsclear\"></div>")

    response.writeln("<div class=\"prefstaborderfooter\">")
    response.writeln("Saved changes will take effect after you refresh the results entry page.")
    response.writeln("</div>")

    response.writeln("</div>") # preferencestaborder

    response.writeln("<div class=\"prefsfeedback\">")
    response.writeln("<span class=\"prefssaved\" id=\"prefssavedspan\">")
    if saved_prefs:
        response.writeln("Preferences saved.");
    response.writeln("</span>")
    response.writeln("</div>")

    response.writeln("<div class=\"prefssubmitrow\">")
    response.writeln("<input type=\"submit\" name=\"saveprefs\" onclick=\"change_saved_indicator(false); return true;\" value=\"Save Preferences\" />")
    response.writeln("<button onclick=\"window.close();\">Close Window</button>")
    response.writeln("</div>")

    response.writeln("</form>")
    response.writeln("</div>") # preferencesdiv

    response.writeln("</body>")
    response.writeln("</html>")
