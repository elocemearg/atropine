#!/usr/bin/python

import sys
import cgicommon
import urllib
import cgi
import cgitb
import re

cgitb.enable()

print "Content-Type: text/html; charset=utf-8"
print ""

form = cgi.FieldStorage()
tourney_name = form.getfirst("tourney")

tourney = None

cgicommon.set_module_path()

import countdowntourney

cgicommon.print_html_head("Display: " + str(tourney_name), cssfile="teleoststyle.css")

print "<script>var tourney_name = \"%s\";</script>" % (tourney_name);

script_text = """
<script type="text/javascript" src="/teleost.js"></script>
<script type="text/javascript">

var viewUpdateInterval = null;
var refreshGameStateInterval = null;
var currentView = null;
var currentViewDrawn = false;
var viewRefreshFrameInterval = null;
var frame_ms = 40;
var updatesSkipped = 0;
var updatesMaxSkip = 5;

function refreshFrame_current_view() {
    var cont = currentView.refreshFrame(new Date().getTime());
    if (!cont) {
        /* animation complete - refreshFrame() calls no longer needed */
        clearInterval(viewRefreshFrameInterval);
        viewRefreshFrameInterval = null;
    }
}

function update_current_view() {
    /* If an animation is still going on, awkwardly walk back out of the room,
       unless we've skipped updatesMaxSkip updates consecutively in this way,
       in which case kill the animation and do the next refresh without
       animating. */
    var enableAnimation = true;
    if (viewRefreshFrameInterval != null) {
        if (updatesSkipped < updatesMaxSkip) {
            updatesSkipped++;
            return;
        }
        else {
            clearInterval(viewRefreshFrameInterval);
            viewRefreshFrameInterval = null;
            enableAnimation = false;
        }
    }

    updatesSkipped = 0;
    var animate = currentView.refresh(new Date().getTime(), enableAnimation);
    currentViewDrawn = true;
    if (animate && enableAnimation) {
        viewRefreshFrameInterval = setInterval(refreshFrame_current_view, frame_ms);
    }
}

function display_setup() {
    currentView = create_standings_and_videprinter(tourney_name);
    var mainpane = document.getElementById("displaymainpane");
    var viewdiv = document.createElement("div")
    mainpane.appendChild(viewdiv);
    currentView.setup(viewdiv);

    fetch_game_state();
    viewUpdateInterval = setInterval(update_current_view, 1000);
    refreshGameStateInterval = setInterval(fetch_game_state, 5000);
}
</script>
"""
script_text = re.sub("\\$TOURNEY_NAME", tourney_name, script_text)
print script_text


print "<body class=\"display\" onload=\"display_setup();\">"

if tourney_name is None:
    cgicommon.show_tourney_exception(countdowntourney.TourneyException("No tourney name specified."))
    print "</body>"
    print "</html>"
    sys.exit(0)

print "<div id=\"displaymainpane\">"
print "</div>"

print "</body>"
print "</html>"
