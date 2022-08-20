#!/usr/bin/python3

import sys;
import os;
import cgi;
import urllib.request, urllib.parse, urllib.error;
import sqlite3;
import html
import re

dbdir = os.getenv("TOURNEYSPATH")
if not dbdir:
    dbdir = os.path.join("..", "tourneys");
globaldbfile = os.path.join("..", "prefs.db");

def int_or_none(s):
    try:
        i = int(s)
        return i
    except:
        return None

def writeln(string=""):
    sys.stdout.buffer.write(string.encode("utf-8"))
    sys.stdout.buffer.write(b'\n')

def write(string):
    sys.stdout.buffer.write(string.encode("utf-8"))

def escape(string, quote=True):
    if string is None:
        return "(None)"
    else:
        return html.escape(string, quote)

def print_html_head(title, cssfile="style.css", othercssfiles=[]):
    writeln("<!DOCTYPE html>")
    writeln("<html lang=\"en\">")
    writeln("<head>");
    writeln("<title>%s</title>" % (escape(title)));
    writeln("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />");
    writeln("<link rel=\"stylesheet\" type=\"text/css\" href=\"/%s\" />" % (escape(cssfile, True)));
    for f in othercssfiles:
        writeln("<link rel=\"stylesheet\" type=\"text/css\" href=\"/%s\" />" % (escape(f, True)));
    writeln("<link rel=\"shortcut icon\" href=\"/favicon.ico\" type=\"image/x-icon\" />")
    writeln("<link rel=\"shortcut icon\" href=\"/favicon.png\" type=\"image/png\" />")
    writeln("</head>");

def print_html_head_local(title):
    writeln("<!DOCTYPE html>")
    writeln("<html lang=\"en\">")
    writeln("<head>")
    writeln("<title>%s</title>" % (escape(title)))
    writeln("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />")
    writeln("<style>")

    # Current directory should already be webroot
    try:
        f = open("style.css")
        for line in f:
            write(line)
        f.close()
    except IOError:
        writeln("<!-- Failed to load style.css -->")
        pass

    writeln("</style>")
    writeln("</head>")

def show_tourney_exception(exc):
    show_error_text(exc.description)

def show_error_text(text):
    writeln("<div class=\"tourneyexception\">")
    writeln("<div class=\"tourneyexceptionimage\">")
    writeln("<img src=\"/images/facepalm.png\" alt=\"Facepalm\" />")
    writeln("</div>")
    writeln("<div class=\"tourneyexceptionmessagecontainer\">")
    writeln("<div class=\"tourneyexceptionmessage\">")
    writeln(escape(text))
    writeln("</div>")
    writeln("</div>")
    writeln("</div>")

def make_warning_box(html, wide=False):
    lines = []
    lines.append("<div class=\"warningbox%s\">" % (" warningboxwidthlimited" if not wide else ""))
    lines.append("<div class=\"warningboximage\">")
    lines.append("<img src=\"/images/warning.png\" alt=\"Warning\" />")
    lines.append("</div>")
    lines.append("<div class=\"warningboxmessagecontainer%s\">" % (" warningboxmessagecontainerwidthlimited" if not wide else ""))
    lines.append("<div class=\"warningboxmessage\">")
    lines.append(html)
    lines.append("</div>")
    lines.append("</div>")
    lines.append("</div>")
    return "\n".join(lines)

def show_warning_box(html, wide=False):
    writeln(make_warning_box(html, wide))

def show_info_box(html):
    writeln("<div class=\"infoboxcontainer\">")
    writeln("<div class=\"infoboximage\">")
    writeln("<img src=\"/images/info.png\" alt=\"Info\" />")
    writeln("</div>")
    writeln("<div class=\"infoboxmessagecontainer\">")
    writeln("<div class=\"infoboxmessage\">")
    writeln(html)
    writeln("</div>")
    writeln("</div>")
    writeln("</div>")

def show_success_box(html):
    writeln("<div class=\"infoboxcontainer successinfoboxcontainer\">")
    writeln("<div class=\"infoboximage\">")
    writeln("<img src=\"/images/success.png\" alt=\"Success\" />")
    writeln("</div>")
    writeln("<div class=\"infoboxmessagecontainer\">")
    writeln("<div class=\"infoboxmessage\">")
    writeln(html)
    writeln("</div>")
    writeln("</div>")
    writeln("</div>")


def set_module_path():
    generator_dir = os.environ.get("GENERATORPATH", ".");
    code_dir = os.environ.get("CODEPATH", os.path.join("..", "..", "py"));
    sys.path.append(generator_dir);
    sys.path.append(code_dir);


# Write out the uploader widget for the sidebar, and write the necessary
# Javascript so that it's updated automatically.
def write_live_upload_widget(tourney_name):
    writeln("<div class=\"uploaderwidget\">")

    writeln("<div class=\"uploaderwidgeticon\" id=\"uploaderwidgeticondiv\">")
    writeln("<img id=\"uploaderwidgeticon\" />")
    writeln("</div>")

    writeln("<div class=\"uploaderwidgetstatus\" id=\"uploaderwidgetstatus\">")
    writeln("</div>")

    writeln("</div>")

    upload_widget_script_text = """<script>
<!--
var uploadStatusRequest = null;

var uploadWidgetExtraCallback = null;
var uploadWidgetSecondsOfFailure = null;
var uploadWidgetBroadcastingEnabled = false;
var uploadWidgetSuccess = false;
var uploadWidgetNumViewers = null;
var uploadWidgetErrorMessage = null;
var uploadWidgetUploaderThreadFailed = false;
var uploadWidgetFailureIsHTTP = false;

function makeDurationString(seconds) {
    if (seconds < 60) {
        return seconds.toString() + "s";
    }
    else if (seconds < 3600) {
        return Math.floor(seconds / 60).toString() + "m";
    }
    else if (seconds < 86400) {
        return Math.floor(seconds / 3600).toString() + "h " + (Math.floor(seconds / 60) % 60).toString() + "m";
    }
    else {
        return "> 24h";
    }
}

/* If lightFlashInterval is set, then every half second we will alternate the
   image between uploadoff.png and lightFlashImgSrc */
var lightFlashInterval = null;
var lightFlashImgSrc = null;
var lightFlashState = false;

function lightFlashUpdate() {
    var img = document.getElementById("uploaderwidgeticon");
    if (img != null) {
        if (lightFlashState) {
            lightFlashState = false;
            img.src = "/images/uploadoff.png";
        }
        else {
            lightFlashState = true;
            img.src = lightFlashImgSrc;
        }
    }
}

function updateUploadWidgetWithStatus(response) {
    var img = document.getElementById("uploaderwidgeticon");
    var statusElement = document.getElementById("uploaderwidgetstatus");
    var imgFile = null;
    var flash = false;
    var titleText = null;

    if (response != null && response.success) {
        var status = response.uploader_state;
        var isUploading = status.publishing;
        var lastSuccessfulUploadTime = status.last_successful_upload_time;
        var lastFailedUpload = status.last_failed_upload;
        var lastFailedUploadTime = null;
        var uploadButtonPressedTime = status.upload_button_pressed_time;
        var now = status.now;
        var secondsOfFailure = null;
        var statusText = null;
        var successful = false;
        var errorMessage = null;
        var lastAttemptFailed = false;
        var numViewers = null;

        if (lastFailedUpload != null) {
            lastFailedUploadTime = lastFailedUpload.ts;
        }

        if (!isUploading) {
            imgFile = "uploadoff.png";
            titleText = "Not broadcasting";
        }
        else if (lastSuccessfulUploadTime == null && lastFailedUploadTime == null) {
            imgFile = "uploadnoidea.png";
            statusText = "Please wait...";
            titleText = "Waiting for upload status...";
            flash = true;
        }
        else if (lastSuccessfulUploadTime == null || (lastFailedUploadTime > lastSuccessfulUploadTime)) {
            var failureStartTime;
            if (lastFailedUpload.failure_type == 1) {
                imgFile = "uploadfailhttp.png";
                titleText = "Server error or internet connection failure";
                uploadWidgetFailureIsHTTP = true;
            }
            else {
                titleText = "Upload rejected by server";
                imgFile = "uploadfailrejected.png";
            }
            if (lastSuccessfulUploadTime == null) {
                failureStartTime = uploadButtonPressedTime;
            }
            else if (uploadButtonPressedTime == null) {
                failureStartTime = lastSuccessfulUploadTime;
            }
            else {
                failureStartTime = Math.max(uploadButtonPressedTime, lastSuccessfulUploadTime);
            }
            secondsOfFailure = now - failureStartTime;
            errorMessage = lastFailedUpload.message;
            lastAttemptFailed = true;
            flash = true;
        }
        else if (lastSuccessfulUploadTime < now - 15) {
            imgFile = "uploadnoidea.png";
            secondsOfFailure = now - lastSuccessfulUploadTime;
            errorMessage = "No upload for " + makeDurationString(secondsOfFailure);
            titleText = errorMessage;
            flash = true;
        }
        else {
            imgFile = "uploadsuccess.png";
            statusText = "Connected";
            numViewers = status.viewers;
            titleText = statusText;
            if (numViewers != null) {
                statusText = " &#128065; " + numViewers.toString();
                titleText += ", " + numViewers.toString() + " viewing";
            }
            successful = true;
        }

        if (!isUploading) {
            statusElement.style.display = "none";
        }
        else {
            statusElement.style.display = null;
            if (successful) {
                statusElement.style.backgroundColor = "#88ff88";
                statusElement.style.color = "black";
                statusElement.innerHTML = statusText;
            }
            else if (!lastAttemptFailed) {
                statusElement.style.backgroundColor = "#ffff88";
                statusElement.style.color = "black";
                if (secondsOfFailure != null)
                    statusElement.innerText = makeDurationString(secondsOfFailure);
                else
                    statusElement.innerHTML = statusText;
            }
            else {
                statusElement.style.backgroundColor = "red";
                statusElement.style.color = "white";
                if (secondsOfFailure != null)
                    statusElement.innerText = makeDurationString(secondsOfFailure);
                else
                    statusElement.innerHTML = statusText;
            }
        }

        uploadWidgetSecondsOfFailure = secondsOfFailure;
        uploadWidgetBroadcastingEnabled = isUploading;
        uploadWidgetUploaderThreadFailed = false;
        uploadWidgetSuccess = successful;
        uploadWidgetNumViewers = numViewers;
        uploadWidgetLastAttemptFailed = lastAttemptFailed;
        if (successful) {
            uploadWidgetErrorMessage = null;
        }
        else {
            uploadWidgetErrorMessage = errorMessage;
        }
    }
    else {
        imgFile = "uploadnoidea.png";
        titleText = "Internal error: uploader thread failed";
        statusElement.innerText = "Internal error";
        statusElement.style.color = "white";
        statusElement.style.backgroundColor = "black";
        uploadWidgetUploaderThreadFailed = true;
        uploadWidgetSuccess = false;
        uploadWidgetNumViewers = null;
        uploadWidgetBroadcastingEnabled = false;
        uploadWidgetSecondsOfFailure = 0;
        uploadWidgetLastAttemptFailed = true;
    }

    if (flash) {
        lightFlashImgSrc = "/images/" + imgFile;
        if (lightFlashInterval == null) {
            lightFlashInterval = setInterval(lightFlashUpdate, 500);
            lightFlashState = true;
        }
    }
    else {
        if (lightFlashInterval != null) {
            clearInterval(lightFlashInterval);
            lightFlashInterval = null;
            lightFlashImgSrc = false;
            lightFlashState = true;
        }
    }
    img.setAttribute("src", "/images/" + imgFile);
    if (titleText != null) {
        img.setAttribute("title", titleText);
        img.setAttribute("alt", titleText);
        statusElement.setAttribute("title", titleText);
    }
}

function refreshUploadWidgetCallback() {
    var req = uploadStatusRequest;
    if (req.status == 200 && req.responseText != null) {
        var uploadStatus = JSON.parse(req.responseText);
        updateUploadWidgetWithStatus(uploadStatus);
        if (uploadWidgetExtraCallback != null) {
            uploadWidgetExtraCallback(uploadWidgetBroadcastingEnabled,
                    uploadWidgetSuccess, uploadWidgetNumViewers,
                    uploadWidgetSecondsOfFailure, uploadWidgetErrorMessage,
                    uploadWidgetFailureIsHTTP, uploadWidgetLastAttemptFailed,
                    uploadWidgetUploaderThreadFailed);
        }
    }
    uploadStatusRequest = null;
}

function refreshUploadWidgetError() {
    var el = document.getElementById("uploaderwidgetstatus");
    el.innerText = "Internal error";
    //el.setAttribute("title", "jsonreq.py failed: " + uploadStatusRequest.statusText);
    updateUploadWidgetWithStatus(null);
    if (uploadWidgetExtraCallback != null) {
        uploadWidgetExtraCallback(uploadWidgetBroadcastingEnabled,
                uploadWidgetSuccess, uploadWidgetNumViewers,
                uploadWidgetSecondsOfFailure, uploadWidgetErrorMessage,
                uploadWidgetFailureIsHTTP, uploadWidgetLastAttemptFailed,
                uploadWidgetUploaderThreadFailed);
    }
    uploadStatusRequest = null;
}

function refreshUploadWidget() {
    /* Ask our uploader thread for its status, and when it returns, display
       it on the uploader widget */
    if (uploadStatusRequest == null) {
        uploadStatusRequest = new XMLHttpRequest();
        uploadStatusRequest.open("GET", "jsonreq.py?tourney=$TOURNEY_NAME&request=uploader", true);
        uploadStatusRequest.onload = refreshUploadWidgetCallback;
        uploadStatusRequest.onerror = refreshUploadWidgetError;
        uploadStatusRequest.send(null);
    }
}

var uploadWidgetInterval = null;
function setupUploadWidget() {
    refreshUploadWidget();

    /* So that we don't have to wait 10 seconds to get the result, call
       refreshUploadWidget 2 and 4 seconds after the page loads */
    setTimeout(refreshUploadWidget, 2000);
    setTimeout(refreshUploadWidget, 4000);
    uploadWidgetInterval = setInterval(refreshUploadWidget, 10000);
}

setupUploadWidget();

// -->
</script>"""
    upload_widget_script_text = re.sub("\$TOURNEY_NAME", tourney_name, upload_widget_script_text)
    writeln(upload_widget_script_text)


def show_sidebar(tourney, show_setup_links=True, show_misc_table_links=False):
    new_window_html = "<img src=\"/images/opensinnewwindow.png\" alt=\"Opens in new window\" title=\"Opens in new window\" />"
    writeln("<div class=\"sidebar\">");

    writeln("<a href=\"/cgi-bin/home.py\"><img src=\"/images/eyebergine128.png\" alt=\"Eyebergine\" /></a><br />");
    if tourney:
        writeln("<p><strong>%s</strong></p>" % escape(tourney.name));
        writeln(("<a href=\"/cgi-bin/tourneysetup.py?tourney=%s\"><strong>General Setup</strong></a>" % urllib.parse.quote_plus(tourney.name)));

        if show_setup_links:
            writeln("<div class=\"sidebarlinklist\">")
            writeln("<div>")
            writeln(("<a href=\"/cgi-bin/player.py?tourney=%s\">Players...</a>" % (urllib.parse.quote_plus(tourney.name))))
            writeln("</div>")
            writeln("<div>")
            writeln(("<a href=\"/cgi-bin/divsetup.py?tourney=%s\">Divisions...</a>" % (urllib.parse.quote_plus(tourney.name))))
            writeln("</div>")
            writeln("<div>")
            writeln(("<a href=\"/cgi-bin/tourneysetupadvanced.py?tourney=%s\">Advanced...</a>" % (urllib.parse.quote_plus(tourney.name))))
            writeln("</div>")
            writeln("</div>")
        else:
            writeln("<div style=\"clear: both;\"></div>")

        writeln("<br />")
        writeln("<div>")
        writeln(("<a href=\"/cgi-bin/uploadsetup.py?tourney=%s\"><strong>Broadcast Setup</strong></a>" % urllib.parse.quote_plus(tourney.name)));
        writeln("</div>")

        writeln(("<a class=\"widgetlink\" href=\"/cgi-bin/uploadsetup.py?tourney=%s\">" % urllib.parse.quote_plus(tourney.name)));
        write_live_upload_widget(tourney.name)
        writeln("</a>")

        writeln("<br />")

        writeln("<div>")
        writeln(("<a href=\"/cgi-bin/displayoptions.py?tourney=%s\"><strong>Display Setup</strong></a>" % urllib.parse.quote_plus(tourney.name)));
        writeln("<span class=\"sidebaropendisplaylink\" title=\"Open public display window\">")
        writeln("<a href=\"/cgi-bin/display.py?tourney=%s\" target=\"_blank\">Window <img src=\"/images/opensinnewwindow.png\" alt=\"Opens in new window\" title=\"Open public display in new window\"/></a>" % (urllib.parse.quote_plus(tourney.name)))
        writeln("</span>")
        writeln("</div>")

        banner_text = tourney.get_banner_text()
        if banner_text:
            writeln(("<a href=\"/cgi-bin/displayoptions.py?tourney=%s\">" % (urllib.parse.quote_plus(tourney.name))))
            writeln("<div class=\"sidebarbanner\" title=\"Banner is active\">")
            writeln((escape(banner_text)))
            writeln("</div>")
            writeln("</a>")

        writeln("<br />")

        rounds = tourney.get_rounds();
        current_round = tourney.get_current_round()
        if rounds:
            if current_round:
                writeln(("<div><a href=\"/cgi-bin/games.py?tourney=%s&amp;round=%s\"><strong>Results entry</strong></a></div>" % (urllib.parse.quote_plus(tourney.name), urllib.parse.quote_plus(str(current_round["num"])))))
            else:
                writeln("<div><strong>Games</strong></div>")
        writeln("<div class=\"roundlinks\">")
        for r in rounds:
            round_no = r["num"];
            round_name = r.get("name", None);
            if not round_name:
                round_name = "Round " + str(round_no);

            writeln("<div class=\"roundlink\">");
            writeln("<a href=\"/cgi-bin/games.py?tourney=%s&amp;round=%s\">%s</a>" % (urllib.parse.quote_plus(tourney.name), urllib.parse.quote_plus(str(round_no)), escape(round_name)));
            writeln("</div>");
        writeln("</div>")
        writeln("<br />");
        writeln("<div class=\"genroundlink\">");
        writeln("<a href=\"/cgi-bin/fixturegen.py?tourney=%s\"><strong>Generate fixtures...</strong></a>" % (urllib.parse.quote_plus(tourney.name)));
        writeln("</div>");
        writeln("<br />")

        writeln("<div class=\"misclinks\">")
        writeln("<a href=\"/cgi-bin/standings.py?tourney=%s\">Standings</a>" % (urllib.parse.quote_plus(tourney.name)));
        writeln("</div>")

        misc_links_html = """
<a href="/cgi-bin/tableindex.py?tourney=$TOURNEY">Name-table index</a>
<br />
<a href="/cgi-bin/tuffluck.py?tourney=$TOURNEY">Tuff Luck</a>
<br />
<a href="/cgi-bin/timdownaward.py?tourney=$TOURNEY">Tim Down Award</a>
<br />
<a href="/cgi-bin/luckystiff.py?tourney=$TOURNEY">Lucky Stiff</a>
<br />
<a href="/cgi-bin/overachievers.py?tourney=$TOURNEY">Overachievers</a>
"""
        misc_links_html = misc_links_html.replace("$TOURNEY", urllib.parse.quote_plus(tourney.name))

        writeln("<div class=\"misclinks\">")
        writeln("<a href=\"/cgi-bin/export.py?tourney=%s\">Export results...</a>" % (urllib.parse.quote_plus(tourney.name)))
        writeln("</div>")

        writeln("<noscript><div class=\"misclinks\">")
        writeln(misc_links_html)
        writeln("</div></noscript>")

        writeln("""<script>
function toggleMiscStats() {
    var miscStatsLink = document.getElementById("miscstatslink");
    var miscStatsDiv = document.getElementById("miscstats");
    if (miscStatsDiv.style.display == "block") {
        miscStatsDiv.style.display = "none";
        miscStatsLink.innerText = "[Expand]";
    }
    else {
        miscStatsDiv.style.display = "block";
        miscStatsLink.innerText = "[Collapse]";
    }
}
</script>""")

        writeln("More")
        writeln("<a id=\"miscstatslink\" class=\"fakelink\" onclick=\"toggleMiscStats();\">%s</a>" % ("[Collapse]" if show_misc_table_links else "[Expand]"))
        writeln("<div style=\"clear: both\"></div>")
        writeln("<div class=\"misclinks\" id=\"miscstats\" style=\"display: %s;\">" % ("block" if show_misc_table_links else "none"))
        writeln(misc_links_html)
        writeln("</div>")

    writeln("<br />")

    writeln("<div class=\"misclinks\">")
    writeln("<a href=\"/docs/\" target=\"_blank\">Help " + new_window_html + "</a>")
    writeln("</div>")

    writeln("<div class=\"globalprefslink\">")
    writeln("<a href=\"/cgi-bin/preferences.py\" target=\"_blank\" ")
    writeln("onclick=\"window.open('/cgi-bin/preferences.py', 'newwindow', 'width=700,height=750'); return false;\" >Preferences... " + new_window_html + "</a>")
    writeln("</div>")

    writeln("<br />")

    if tourney:
        writeln("<div class=\"sidebarversioninfo\" title=\"This is the version number of the Atropine installation you're using, and the version which created the database for this tourney.\">");
        writeln("<div class=\"sidebarversionline\">")
        writeln("Atropine version: %s" % (tourney.get_software_version()))
        writeln("</div>")
        writeln("<div class=\"sidebarversionline\">")
        writeln("This tourney version: %s" % (tourney.get_db_version()))
        writeln("</div>")
        writeln("</div>")

    writeln("</div>");

def make_team_dot_html(team):
    if team:
        team_string = '<span style="color: #%s;" class="faintoutline">&#x25cf;</span>' % team.get_hex_colour()
    else:
        team_string = ""
    return team_string

def make_player_dot_html(player):
    return make_team_dot_html(player.get_team())

def show_team_score_table(team_scores):
    writeln("<table class=\"ranktable\">")
    writeln('<th colspan="2">Team score</th>')
    for (team, score) in team_scores:
        writeln('<tr>')
        writeln('<td class="rankname">%s %s</td>' % (make_team_dot_html(team), escape(team.get_name())))
        writeln('<td class="ranknumber rankhighlight">%d</td>' % score)
        writeln('</tr>')
    writeln('</table>')

def show_games_as_html_table(games, editable=True, remarks=None,
        include_round_column=False, round_namer=None, player_to_link=None,
        remarks_heading="", show_game_type=True, game_onclick_fn=None,
        colour_win_loss=True, score_id_prefix=None, show_heading_row=True,
        hide_game_type_if_p=False):
    if round_namer is None:
        round_namer = lambda x : ("Round %d" % (x))

    if player_to_link is None:
        player_to_link = lambda x : escape(x.get_name())

    writeln("<table class=\"scorestable\">");

    if show_game_type and hide_game_type_if_p:
        for g in games:
            if g.game_type != 'P':
                break
        else:
            # There are no non-type-P games, so don't bother showing the game
            # type column at all
            show_game_type = False

    if show_heading_row:
        writeln("<tr>");
        if include_round_column:
            writeln("<th>Round</th>")

        writeln("<th>Table</th>");

        if show_game_type:
            writeln("<th>Type</th>");

        writeln("<th>Player 1</th><th>Score</th><th>Player 2</th>");
        if remarks is not None:
            writeln("<th>%s</th>" % (escape(remarks_heading)));
        writeln("</tr>")

    last_table_no = None;
    last_round_no = None
    game_seq = 0
    for g in games:
        player_html_strings = (player_to_link(g.p1), player_to_link(g.p2));
        tr_classes = ["gamerow"];

        if last_round_no is None or last_round_no != g.round_no or last_table_no is None or last_table_no != g.table_no:
            tr_classes.append("firstgameintable");
            # Count how many consecutive games appear with this table
            # number, so we can group them together in the table.
            num_games_on_table = 0;
            while game_seq + num_games_on_table < len(games) and games[game_seq + num_games_on_table].table_no == g.table_no and games[game_seq + num_games_on_table].round_no == g.round_no:
                num_games_on_table += 1;
            first_game_in_table = True;
        else:
            first_game_in_table = False;

        if last_round_no is None or last_round_no != g.round_no:
            tr_classes.append("firstgameinround")
            num_games_in_round = 0
            while game_seq + num_games_in_round < len(games) and games[game_seq + num_games_in_round].round_no == g.round_no:
                num_games_in_round += 1
            first_game_in_round = True
        else:
            first_game_in_round = False

        if g.is_complete():
            tr_classes.append("completedgame");
        else:
            tr_classes.append("unplayedgame");

        if game_onclick_fn:
            onclick_attr = "onclick=\"" + escape(game_onclick_fn(g.round_no, g.seq)) + "\""
            tr_classes.append("handcursor")
        else:
            onclick_attr = "";
        writeln("<tr class=\"%s\" %s>" % (" ".join(tr_classes), onclick_attr));
        if first_game_in_round and include_round_column:
            writeln("<td class=\"roundno\" rowspan=\"%d\">%s</td>" % (num_games_in_round, round_namer(g.round_no)))
        if first_game_in_table:
            writeln("<td class=\"tableno\" rowspan=\"%d\"><div class=\"tablebadge\">%d</div></td>" % (num_games_on_table, g.table_no));

        if show_game_type:
            writeln("<td class=\"gametype\">%s</td>" % (
                "" if g.game_type == "P" and hide_game_type_if_p else escape(g.game_type)
            ))

        p1_classes = ["gameplayer1"];
        p2_classes = ["gameplayer2"];
        if g.is_complete() and colour_win_loss:
            if g.is_double_loss():
                p1_classes.append("losingplayer")
                p2_classes.append("losingplayer")
            elif g.s1 == g.s2:
                p1_classes.append("drawingplayer");
                p2_classes.append("drawingplayer");
            elif g.s1 > g.s2:
                p1_classes.append("winningplayer");
                p2_classes.append("losingplayer");
            elif g.s2 > g.s1:
                p1_classes.append("losingplayer");
                p2_classes.append("winningplayer");

        team_string = make_player_dot_html(g.p1)

        writeln("<td class=\"%s\">%s %s</td>" % (" ".join(p1_classes), player_html_strings[0], team_string));
        if g.is_double_loss():
            edit_box_score = "0 - 0*"
            html_score = "&#10006; - &#10006;"
        else:
            edit_box_score = g.format_score()
            html_score = escape(g.format_score())

        if score_id_prefix:
            writeln("<td class=\"gamescore\" id=\"%s_%d_%d\">" % (escape(score_id_prefix), g.round_no, g.seq));
        else:
            writeln("<td class=\"gamescore\">");

        if editable:
            writeln("""
<input class="gamescore" id="gamescore_%d_%d" type="text" size="10"
name="gamescore_%d_%d" value="%s"
onchange="score_modified('gamescore_%d_%d');" />""" % (g.round_no, g.seq, g.round_no, g.seq, escape(edit_box_score, True), g.round_no, g.seq));
        else:
            writeln(html_score);

        writeln("</td>");
        team_string = make_player_dot_html(g.p2)
        writeln("<td class=\"%s\">%s %s</td>" % (" ".join(p2_classes), team_string, player_html_strings[1]));
        if remarks is not None:
            writeln("<td class=\"gameremarks\">%s</td>" % escape(remarks.get((g.round_no, g.seq), "")));
        writeln("</tr>");
        last_round_no = g.round_no
        last_table_no = g.table_no;
        game_seq += 1

    writeln("</table>");

def write_table(headings, td_classes, rows, no_escape_html=[], formatters={}, table_class=None):
    """Write out an HTML table with the CSS class table_class.

    headings: a list of strings, one per column, for the table headings.
    td_classes: a list of strings, one per column, for the CSS classes to be
        applied to each td element in a row. If a td is to have multiple class
        names they should be separated by a space.
    rows: a list of tuples, each of which must contain the same number of values
           as headings and td_classes. These will be converted to strings,
           escaped for HTML, and made the contents of the row's <td> element.
    no_escape_html: a list of 0-based field numbers in "rows" in which the
           usual HTML escaping should be suppressed. This is useful if a row
           value contains HTML you want to display as-is.
    formatters: if specified, it is a dict mapping the 0-based column number to
           a function which takes a column value and returns the string to go in
           the <td> element. The default if formatters is not given, or if the
           column number does not appear in the dict, is str().
    table_class: the CSS class to be given to the <table> element.
    """

    if table_class:
        writeln("<table class=\"ranktable\">")
    else:
        writeln("<table>")
    writeln("<tr>")
    for heading in headings:
        writeln("<th>")
        writeln(escape(heading))
        writeln("</th>")
    writeln("</tr>")
    no_escape_html = set(no_escape_html)
    for row in rows:
        writeln("<tr>")
        for (index, value) in enumerate(row):
            if td_classes[index]:
                writeln("<td class=\"%s\">" % (td_classes[index]))
            else:
                writeln("<td>")
            formatted_value = formatters.get(index, str)(value)
            if index in no_escape_html:
                writeln(formatted_value)
            else:
                writeln(escape(formatted_value))
            writeln("</td>")
        writeln("</tr>")
    writeln("</table>")

def write_ranked_table(headings, td_classes, rows, key_fn, no_escape_html=[], formatters={}):
    """Write out a table with an additional rank column at the start indicating position.

    headings, td_classes, rows, no_escape_html and formatters have the same
    meaning as in write_table().

    key_fn should be a function translating a row object (an element of rows)
    to a value suitable for comparing one row against another, for the purpose
    of deciding whether this row should get a new rank number or be given the
    same rank number as the previous row.
    """

    ranked_rows = []
    pos = 0
    joint = 0
    prev_key_value = None
    for row in rows:
        key_value = key_fn(row)
        if prev_key_value is not None and prev_key_value == key_value:
            joint += 1
        else:
            pos += joint + 1
            joint = 0
        ranked_rows.append(tuple([pos] + list(row)))
        prev_key_value = key_value
    new_formatters = {}
    for col in formatters:
        new_formatters[col + 1] = formatters[col]
    write_table([""] + headings, ["rankpos"] + td_classes, ranked_rows,
            no_escape_html=[ x + 1 for x in no_escape_html ],
            formatters=new_formatters, table_class="ranktable")


def show_standings_table(tourney, show_draws_column, show_points_column,
        show_spread_column, show_first_second_column=False,
        linkify_players=False, show_tournament_rating_column=False,
        show_qualified=False, which_division=None, show_finals_column=True):
    writeln(make_standings_table(tourney, show_draws_column, show_points_column,
        show_spread_column, show_first_second_column, linkify_players,
        show_tournament_rating_column, show_qualified, which_division,
        show_finals_column))

def make_standings_table(tourney, show_draws_column, show_points_column,
        show_spread_column, show_first_second_column=False,
        linkify_players=False, show_tournament_rating_column=False,
        show_qualified=False, which_division=None, show_finals_column=True):
    html = []

    num_divisions = tourney.get_num_divisions()
    ranking_by_wins = tourney.is_ranked_by_wins()
    rank_method = tourney.get_rank_method()

    secondary_rank_headings = rank_method.get_secondary_rank_headings()

    if linkify_players:
        linkfn = lambda x : player_to_link(x, tourney.get_name(), open_in_new_window=True)
    else:
        linkfn = lambda x : escape(x.get_name())

    if which_division is None:
        div_list = range(num_divisions)
    else:
        div_list = [which_division]

    html.append("<table class=\"ranktable\">")
    for div_index in div_list:
        standings = tourney.get_standings(div_index)
        if num_divisions > 1:
            div_string = tourney.get_division_name(div_index)
        else:
            div_string = ""

        finals_form_exists = False
        for s in standings:
            if "W" in s.finals_form or "D" in s.finals_form or "L" in s.finals_form:
                finals_form_exists = True
                break
        if not finals_form_exists:
            show_finals_column = False

        if div_index > 0:
            html.append("<tr class=\"ranktabledivspacer\"><td></td></tr>")
        html.append("<tr><th colspan=\"2\">%s</th>" % (escape(div_string)))
        if show_finals_column:
            html.append("<th>Finals</th>")
        html.append("<th>Played</th><th>Wins</th>")
        if show_draws_column:
            html.append("<th>Draws</th>")
        for heading in secondary_rank_headings:
            html.append("<th>" + escape(heading) + "</th>")
        if show_points_column and "Points" not in secondary_rank_headings:
            html.append("<th>Points</th>")
        if show_spread_column and "Spread" not in secondary_rank_headings:
            html.append("<th>Spread</th>")
        if show_first_second_column:
            html.append("<th>1st/2nd</th>")
        if show_tournament_rating_column:
            html.append("<th>Tournament Rating</th>")
        html.append("</tr>")

        last_wins_inc_draws = None;
        tr_bgcolours = ["#ffdd66", "#ffff88" ];
        bgcolour_index = 0;
        for s in standings:
            (pos, name, played, wins, points, draws, spread, num_first) = s[0:8];
            tournament_rating = s.tournament_rating
            finals_form = s.finals_form

            # Remove any leading dashes
            while finals_form and finals_form[0] == '-':
                finals_form = finals_form[1:]

            finals_points = s.finals_points
            player = tourney.get_player_from_name(name)
            if finals_form:
                bgcolour = "#aaffaa"
            elif ranking_by_wins:
                if last_wins_inc_draws is None:
                    bgcolour_index = 0;
                elif last_wins_inc_draws != wins + 0.5 * draws:
                    bgcolour_index = (bgcolour_index + 1) % 2;
                last_wins_inc_draws = wins + 0.5 * draws;

                if player.is_withdrawn():
                    bgcolour = "#cccccc"
                elif s.qualified and show_qualified:
                    bgcolour = "#66ff66"
                else:
                    bgcolour = tr_bgcolours[bgcolour_index]
            else:
                if player.is_withdrawn():
                    bgcolour = "#cccccc"
                elif s.qualified and show_qualified:
                    bgcolour = "#66ff66"
                else:
                    bgcolour = "#ffdd66"

            html.append("<tr style=\"background-color: %s\">" % (bgcolour));

            highlight_class = " rankhighlight"
            if ranking_by_wins:
                wins_class = highlight_class
                draws_class = highlight_class
            else:
                wins_class = ""
                draws_class = ""
            html.append("<td class=\"rankpos\">%d</td>" % pos);
            html.append("<td class=\"rankname\">%s</td>" % (linkfn(player)));

            if show_finals_column:
                html.append("<td class=\"rankright rankhighlight\"\">%s</td>" % (finals_form))
            html.append("<td class=\"ranknumber\">%d</td>" % played);
            html.append("<td class=\"ranknumber%s\">%d</td>" % (wins_class, wins));
            if show_draws_column:
                html.append("<td class=\"ranknumber%s\">%d</td>" % (draws_class, draws));
            for sec_value in s.get_secondary_rank_value_strings():
                html.append("<td class=\"ranknumber rankhighlight\">%s</td>" % (sec_value))
            if show_points_column and "Points" not in secondary_rank_headings:
                html.append("<td class=\"ranknumber\">%d</td>" % (points))
            if show_spread_column and "Spread" not in secondary_rank_headings:
                html.append("<td class=\"ranknumber\">%+d</td>" % (spread))
            if show_first_second_column:
                html.append("<td class=\"rankright\">%d/%d</td>" % (num_first, played - num_first))
            if show_tournament_rating_column:
                html.append("<td class=\"ranknumber\">")
                if tournament_rating is not None:
                    html.append("%.2f" % (tournament_rating))
                html.append("</td>")
            html.append("</tr>");
    html.append("</table>");
    return "\n".join(html)

def player_to_link(player, tourney_name, emboldenise=False, disable_tab_order=False, open_in_new_window=False, custom_text=None, withdrawn=False):
    if player.is_auto_prune():
        # Auto-prune never has a link
        if emboldenise:
            return "<span style=\"font-weight: bold\">%s</span>" % (escape(player.get_name()))
        else:
            return escape(player.get_name())
    else:
        return "<a class=\"playerlink%s%s\" href=\"player.py?tourney=%s&id=%d\" %s%s>%s</a>" % (
            "withdrawn" if withdrawn else " ",
            " thisplayerlink" if emboldenise else "",
            urllib.parse.quote_plus(tourney_name), player.get_id(),
            "tabindex=\"-1\" " if disable_tab_order else "",
            "target=\"_blank\"" if open_in_new_window else "",
            escape(custom_text) if custom_text is not None else escape(player.get_name())
        )

def player_to_non_link(player, emboldenise=False):
    html = ""
    if emboldenise:
        html += "<span style=\"font-weight: bold;\">"
    html += escape(player.get_name())
    html += "</span>"
    return html

def ordinal_number(n):
    if (n // 10) % 10 == 1:
        return "%dth" % (n)
    elif n % 10 == 1:
        return "%dst" % (n)
    elif n % 10 == 2:
        return "%dnd" % (n)
    elif n % 10 == 3:
        return "%drd" % (n)
    else:
        return "%dth" % (n)

class GlobalPreferences(object):
    def __init__(self, names_values):
        self.mapping = names_values.copy()

    def get_result_entry_tab_order(self):
        return self.mapping.get("resultsentrytaborder", "nnss")

    def set_result_entry_tab_order(self, value):
        self.mapping["resultsentrytaborder"] = value

    def get_map(self):
        return self.mapping.copy()

def get_global_preferences():
    db = sqlite3.connect(globaldbfile)

    cur = db.cursor()
    cur.execute("create table if not exists prefs(name text, value text)")
    cur.execute("select name, value from prefs")
    prefs = dict()
    for row in cur:
        prefs[row[0]] = row[1]
    cur.close()

    db.close()

    return GlobalPreferences(prefs)

def set_global_preferences(prefs):
    db = sqlite3.connect(globaldbfile)
    db.execute("delete from prefs")

    rows_to_insert = []

    mapping = prefs.get_map()
    for name in mapping:
        rows_to_insert.append((name, mapping[name]))

    db.executemany("insert into prefs values (?, ?)", rows_to_insert)

    db.commit()

    db.close()

def is_client_from_localhost():
    # If the web server is listening only on the loopback interface, then
    # disable this check - instead we'll rely on the fact that we're only
    # listening on that interface.
    if os.environ.get("ATROPINE_LISTEN_ON_LOCALHOST_ONLY", "0") == "1":
        return True

    valid_answers = ["127.0.0.1", "localhost"]

    remote_addr = os.environ.get("REMOTE_ADDR", None)
    if remote_addr:
        if remote_addr in valid_answers:
            return True
    else:
        remote_host = os.environ.get("REMOTE_HOST", None)
        if remote_host in valid_answers:
            return True
    return False

class FakeException(object):
    def __init__(self, description):
        self.description = description

def assert_client_from_localhost():
    if not is_client_from_localhost():
        show_tourney_exception(FakeException(
            "You're only allowed to access this page from the same computer " +
            "as the one on which atropine is running. Your address is " +
            os.environ.get("REMOTE_ADDR", "(unknown)") + " and I'll only " +
            "serve you this page if you're from localhost."))
        writeln("</body></html>")
        sys.exit(1)

