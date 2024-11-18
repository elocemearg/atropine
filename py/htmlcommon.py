#!/usr/bin/python3

import os
import sqlite3
import html
import re

# Environment variable set by atropine.py before this module is first loaded
dbdir = os.getenv("TOURNEYSPATH")
if not dbdir:
    dbdir = os.path.join("..", "tourneys");

def int_or_none(s):
    try:
        i = int(s)
        return i
    except:
        return None

def escape(string, quote=True):
    if string is None:
        return "(None)"
    else:
        return html.escape(string, quote)

def js_string(contents):
    return "\"" + contents.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

def print_html_head(response, title, cssfile="style.css", othercssfiles=[]):
    response.writeln("<!DOCTYPE html>")
    response.writeln("<html lang=\"en\">")
    response.writeln("<head>");
    response.writeln("<title>%s</title>" % (escape(title)));
    response.writeln("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />");
    response.writeln("<link rel=\"stylesheet\" type=\"text/css\" href=\"/%s\" />" % (escape(cssfile, True)));
    for f in othercssfiles:
        response.writeln("<link rel=\"stylesheet\" type=\"text/css\" href=\"/%s\" />" % (escape(f, True)));
    response.writeln("<link rel=\"shortcut icon\" href=\"/favicon.ico\" type=\"image/x-icon\" />")
    response.writeln("<link rel=\"shortcut icon\" href=\"/favicon.png\" type=\"image/png\" />")
    response.writeln("</head>");

def print_html_head_local(response, title):
    response.writeln("<!DOCTYPE html>")
    response.writeln("<html lang=\"en\">")
    response.writeln("<head>")
    response.writeln("<title>%s</title>" % (escape(title)))
    response.writeln("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />")
    response.writeln("<style>")

    # Current directory should already be webroot
    try:
        f = open("style.css")
        for line in f:
            response.write(line)
        f.close()
    except IOError:
        response.writeln("<!-- Failed to load style.css -->")
        pass

    response.writeln("</style>")
    response.writeln("</head>")

def show_tourney_exception(response, exc):
    show_error_text(response, exc.description)

def show_error_text(response, text):
    response.writeln("<div class=\"tourneyexception\">")
    response.writeln("<div class=\"tourneyexceptionimage\">")
    response.writeln("<img src=\"/images/facepalm.png\" alt=\"Facepalm\" />")
    response.writeln("</div>")
    response.writeln("<div class=\"tourneyexceptionmessagecontainer\">")
    response.writeln("<div class=\"tourneyexceptionmessage\">")
    response.writeln(escape(text))
    response.writeln("</div>")
    response.writeln("</div>")
    response.writeln("</div>")

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

def show_warning_box(response, html, wide=False):
    response.writeln(make_warning_box(html, wide))

def show_info_box(response, html):
    response.writeln("<div class=\"infoboxcontainer\">")
    response.writeln("<div class=\"infoboximage\">")
    response.writeln("<img src=\"/images/info.png\" alt=\"Info\" />")
    response.writeln("</div>")
    response.writeln("<div class=\"infoboxmessagecontainer\">")
    response.writeln("<div class=\"infoboxmessage\">")
    response.writeln(html)
    response.writeln("</div>")
    response.writeln("</div>")
    response.writeln("</div>")

def show_success_box(response, html):
    response.writeln("<div class=\"infoboxcontainer successinfoboxcontainer\">")
    response.writeln("<div class=\"infoboximage\">")
    response.writeln("<img src=\"/images/success.png\" alt=\"Success\" />")
    response.writeln("</div>")
    response.writeln("<div class=\"infoboxmessagecontainer\">")
    response.writeln("<div class=\"infoboxmessage\">")
    response.writeln(html)
    response.writeln("</div>")
    response.writeln("</div>")
    response.writeln("</div>")


# Write out the uploader widget for the sidebar, and write the necessary
# Javascript so that it's updated automatically.
def write_live_upload_widget(response, tourney_name):
    response.writeln("<div class=\"uploaderwidget\">")

    response.writeln("<div class=\"uploaderwidgeticon\" id=\"uploaderwidgeticondiv\">")
    response.writeln("<img id=\"uploaderwidgeticon\" />")
    response.writeln("</div>")

    response.writeln("<div class=\"uploaderwidgetstatus\" id=\"uploaderwidgetstatus\">")
    response.writeln("</div>")

    response.writeln("</div>")

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
    //el.setAttribute("title", "HTTP fetch failed: " + uploadStatusRequest.statusText);
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
        uploadStatusRequest.open("GET", "/service/$TOURNEY_NAME/state/uploader", true);
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
    upload_widget_script_text = re.sub(r"\$TOURNEY_NAME", tourney_name, upload_widget_script_text)
    response.writeln(upload_widget_script_text)


def show_sidebar(response, tourney, show_setup_links=True, show_misc_table_links=False, non_local_client=False):
    new_window_html = "<img src=\"/images/opensinnewwindow.png\" alt=\"Opens in new window\" title=\"Opens in new window\" />"
    response.writeln("<div class=\"sidebar\">");
    response.writeln("<a href=\"/\"><img src=\"/images/eyebergine128.png\" alt=\"Eyebergine\" /></a><br />");

    players = []
    if tourney:
        response.writeln("<p><strong>%s</strong></p>" % escape(tourney.name));

    if tourney and not non_local_client:
        players = tourney.get_players()
        num_games = tourney.get_num_games()
        response.writeln(("<a href=\"/atropine/%s/tourneysetup\"><strong>Tourney Setup</strong></a>" % escape(tourney.name)));

        if show_setup_links:
            response.writeln("<div class=\"sidebarlinklist\">")
            response.writeln("<div>")
            response.writeln("<a href=\"/atropine/%s/player\">Players...</a>" % (escape(tourney.name)))
            response.writeln("</div>")
            if players:
                response.writeln("<div>")
                response.writeln("<a href=\"/atropine/%s/divsetup\">Divisions...</a>" % (escape(tourney.name)))
                response.writeln("</div>")
            response.writeln("<div>")
            response.writeln(("<a href=\"/atropine/%s/tourneysetupadvanced\">Advanced...</a>" % (escape(tourney.name))))
            response.writeln("</div>")
            response.writeln("</div>")
        else:
            response.writeln("<div style=\"clear: both;\"></div>")

        if players and num_games == 0:
            response.writeln("<br />")
            response.writeln("<div>")
            response.writeln("<a href=\"/atropine/%s/checkin\"><strong>Player Check-In</strong></a>" % (escape(tourney.name)))
            response.writeln("</div>")

        if players:
            response.writeln("<br />")
            response.writeln("<div>")
            response.writeln("<a href=\"/atropine/%s/uploadsetup\"><strong>Broadcast Setup</strong></a>" % escape(tourney.name))
            response.writeln("</div>")

            response.writeln("<a class=\"widgetlink\" href=\"/atropine/%s/uploadsetup\">" % escape(tourney.name))
            write_live_upload_widget(response, tourney.name)
            response.writeln("</a>")

        response.writeln("<br />")

        response.writeln("<div>")
        response.writeln(("<a href=\"/atropine/%s/displayoptions\"><strong>Display Setup</strong></a>" % escape(tourney.name)));
        response.writeln("<span class=\"sidebaropendisplaylink\" title=\"Open public display window\">")
        response.writeln("<a href=\"/atropine/%s/display\" target=\"_blank\">Window <img src=\"/images/opensinnewwindow.png\" alt=\"Opens in new window\" title=\"Open public display in new window\"/></a>" % (escape(tourney.name)))
        response.writeln("</span>")
        response.writeln("</div>")

        banner_text = tourney.get_banner_text()
        if banner_text:
            response.writeln("<a href=\"/atropine/%s/displayoptions\">" % (escape(tourney.name)))
            response.writeln("<div class=\"sidebarbanner\" title=\"Banner is active\">")
            response.writeln((escape(banner_text)))
            response.writeln("</div>")
            response.writeln("</a>")

        current_teleost_mode = tourney.get_current_teleost_mode()
        if current_teleost_mode != 0:
            response.writeln("<div>")
            response.writeln("<div style=\"display: inline-block; padding: 5px; border-radius: 5px; font-size: 10pt; background-color: orange; color: black;\" title=\"Display mode is manually overridden.\">Auto OFF</div>")
            response.writeln("</div>")

        response.writeln("<br />")

        rounds = tourney.get_rounds();
        current_round = tourney.get_current_round()
        if rounds:
            if current_round:
                response.writeln(("<div><a href=\"/atropine/%s/games/%s\"><strong>Results entry</strong></a></div>" % (escape(tourney.name), escape(str(current_round["num"])))))
            else:
                response.writeln("<div><strong>Games</strong></div>")
        response.writeln("<div class=\"roundlinks\">")
        for r in rounds:
            round_no = r["num"];
            round_name = r.get("name", None);
            if not round_name:
                round_name = "Round " + str(round_no);

            response.writeln("<div class=\"roundlink\">")
            response.writeln("<a href=\"/atropine/%s/games/%s\">%s</a>" % (escape(tourney.name), escape(str(round_no)), escape(round_name)))
            response.writeln("</div>")
        response.writeln("</div>")
        if players:
            response.writeln("<br />");
            response.writeln("<div class=\"genroundlink\">");
            response.writeln("<a href=\"/atropine/%s/fixturegen\"><strong>Generate fixtures...</strong></a>" % (escape(tourney.name)));
            response.writeln("</div>");
            response.writeln("<br />")

            response.writeln("<div class=\"misclinks\">")
            response.writeln("<a href=\"/atropine/%s/standings\">Standings</a>" % (escape(tourney.name)))
            response.writeln("</div>")

            misc_links_html = """
<a href="/atropine/$TOURNEY/tableindex">Name-table index</a>
<br />
<a href="/atropine/$TOURNEY/tuffluck">Tuff Luck</a>
<br />
<a href="/atropine/$TOURNEY/timdownaward">Tim Down Award</a>
<br />
<a href="/atropine/$TOURNEY/luckystiff">Lucky Stiff</a>
<br />
<a href="/atropine/$TOURNEY/overachievers">Overachievers</a>
"""
            misc_links_html = misc_links_html.replace("$TOURNEY", escape(tourney.name))

            response.writeln("<div class=\"misclinks\">")
            response.writeln("<a href=\"/atropine/%s/export\">Export results...</a>" % (escape(tourney.name)))
            response.writeln("</div>")

            response.writeln("<noscript><div class=\"misclinks\">")
            response.writeln(misc_links_html)
            response.writeln("</div></noscript>")

            response.writeln("""<script>
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

            response.writeln("More")
            response.writeln("<a id=\"miscstatslink\" class=\"fakelink\" onclick=\"toggleMiscStats();\">%s</a>" % ("[Collapse]" if show_misc_table_links else "[Expand]"))
            response.writeln("<div style=\"clear: both\"></div>")
            response.writeln("<div class=\"misclinks\" id=\"miscstats\" style=\"display: %s;\">" % ("block" if show_misc_table_links else "none"))
            response.writeln(misc_links_html)
            response.writeln("</div>")

    if not non_local_client:
        response.writeln("<br />")
        response.writeln("<div class=\"misclinks\">")
        response.writeln("<a href=\"/docs/\" target=\"_blank\">Help " + new_window_html + "</a>")
        response.writeln("</div>")

    if tourney and players and not non_local_client:
        response.writeln("<div class=\"globalprefslink\">")
        response.writeln("<a href=\"/atropine/global/preferences\" target=\"_blank\" ")
        response.writeln("onclick=\"window.open('/atropine/global/preferences', 'newwindow', 'width=700,height=750'); return false;\" >Preferences... " + new_window_html + "</a>")
        response.writeln("</div>")

    response.writeln("<br />")

    if tourney:
        atropine_version = tourney.get_software_version(as_tuple=True)
        atropine_version_string = tourney.get_software_version()
        tourney_version = tourney.get_db_version(as_tuple=True)
        tourney_version_string = tourney.get_db_version()
        response.writeln("<div class=\"sidebarversioninfo\" title=\"This is the version number of the Atropine installation you're using, and the version which created the database for this tourney.\">");
        response.writeln("<div class=\"sidebarversionline\">")
        response.writeln("Atropine version: " + atropine_version_string)
        response.writeln("</div>")
        response.writeln("<div class=\"sidebarversionline\">")
        response.writeln("This tourney: ")
        if tourney_version < atropine_version:
            response.writeln("<span class=\"sidebarversionold\" title=\"This tourney's database file was created by an earlier version of Atropine. Some functionality may be unavailable.\">")
        response.writeln(tourney_version_string)
        if tourney_version < atropine_version:
            response.writeln("</span>")
        response.writeln("</div>")
        response.writeln("</div>")

    response.writeln("</div>");

def make_team_dot_html(team):
    if team:
        team_string = '<span style="color: #%s;" class="faintoutline">&#x25cf;</span>' % team.get_hex_colour()
    else:
        team_string = ""
    return team_string

def make_player_dot_html(player):
    return make_team_dot_html(player.get_team())

def show_team_score_table(response, team_scores):
    response.writeln("<table class=\"ranktable\">")
    response.writeln('<th colspan="2">Team score</th>')
    for (team, score) in team_scores:
        response.writeln('<tr>')
        response.writeln('<td class="rankname">%s %s</td>' % (make_team_dot_html(team), escape(team.get_name())))
        response.writeln('<td class="ranknumber rankhighlight">%d</td>' % score)
        response.writeln('</tr>')
    response.writeln('</table>')

def show_games_as_html_table(response, games, editable=True, remarks=None,
        include_round_column=False, round_namer=None, player_to_link=None,
        remarks_heading="", show_game_type=True, game_onclick_fn=None,
        colour_win_loss=True, score_id_prefix=None, show_heading_row=True,
        hide_game_type_if_p=False):
    if round_namer is None:
        round_namer = lambda x : ("Round %d" % (x))

    if player_to_link is None:
        player_to_link = lambda x : escape(x.get_name())

    response.writeln("<table class=\"scorestable\">");

    if show_game_type and hide_game_type_if_p:
        for g in games:
            if g.game_type != 'P':
                break
        else:
            # There are no non-type-P games, so don't bother showing the game
            # type column at all
            show_game_type = False

    if show_heading_row:
        response.writeln("<tr>");
        if include_round_column:
            response.writeln("<th>Round</th>")

        response.writeln("<th>Table</th>");

        if show_game_type:
            response.writeln("<th>Type</th>");

        response.writeln("<th>Player 1</th><th>Score</th><th>Player 2</th>");
        if remarks is not None:
            response.writeln("<th>%s</th>" % (escape(remarks_heading)));
        response.writeln("</tr>")

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
        response.writeln("<tr class=\"%s\" %s>" % (" ".join(tr_classes), onclick_attr));
        if first_game_in_round and include_round_column:
            response.writeln("<td class=\"roundno\" rowspan=\"%d\">%s</td>" % (num_games_in_round, round_namer(g.round_no)))
        if first_game_in_table:
            response.writeln("<td class=\"tableno\" rowspan=\"%d\"><div class=\"tablebadge\">%d</div></td>" % (num_games_on_table, g.table_no));

        if show_game_type:
            response.writeln("<td class=\"gametype\">%s</td>" % (
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

        response.writeln("<td class=\"%s\">%s %s</td>" % (" ".join(p1_classes), player_html_strings[0], team_string));
        if g.is_double_loss():
            edit_box_score = "0 - 0*"
            html_score = "&#10006; - &#10006;"
        else:
            edit_box_score = g.format_score()
            html_score = escape(g.format_score())

        if score_id_prefix:
            response.writeln("<td class=\"gamescore\" id=\"%s_%d_%d\">" % (escape(score_id_prefix), g.round_no, g.seq));
        else:
            response.writeln("<td class=\"gamescore\">");

        if editable:
            response.writeln("""
<input class="gamescore" id="gamescore_%d_%d" type="text" size="10"
name="gamescore_%d_%d" value="%s"
onchange="score_modified('gamescore_%d_%d');" />""" % (g.round_no, g.seq, g.round_no, g.seq, escape(edit_box_score, True), g.round_no, g.seq));
        else:
            response.writeln(html_score);

        response.writeln("</td>");
        team_string = make_player_dot_html(g.p2)
        response.writeln("<td class=\"%s\">%s %s</td>" % (" ".join(p2_classes), team_string, player_html_strings[1]));
        if remarks is not None:
            response.writeln("<td class=\"gameremarks\">%s</td>" % escape(remarks.get((g.round_no, g.seq), "")));
        response.writeln("</tr>");
        last_round_no = g.round_no
        last_table_no = g.table_no;
        game_seq += 1

    response.writeln("</table>");

def write_table(response, headings, td_classes, rows, no_escape_html=[], formatters={}, table_class=None):
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
        response.writeln("<table class=\"ranktable\">")
    else:
        response.writeln("<table>")
    response.writeln("<tr>")
    for heading in headings:
        response.writeln("<th>")
        response.writeln(escape(heading))
        response.writeln("</th>")
    response.writeln("</tr>")
    no_escape_html = set(no_escape_html)
    for row in rows:
        response.writeln("<tr>")
        for (index, value) in enumerate(row):
            if td_classes[index]:
                response.writeln("<td class=\"%s\">" % (td_classes[index]))
            else:
                response.writeln("<td>")
            formatted_value = formatters.get(index, str)(value)
            if index in no_escape_html:
                response.writeln(formatted_value)
            else:
                response.writeln(escape(formatted_value))
            response.writeln("</td>")
        response.writeln("</tr>")
    response.writeln("</table>")

def write_ranked_table(response, headings, td_classes, rows, key_fn, no_escape_html=[], formatters={}):
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
    write_table(response, [""] + headings, ["rankpos"] + td_classes,
            ranked_rows, no_escape_html=[ x + 1 for x in no_escape_html ],
            formatters=new_formatters, table_class="ranktable")


def show_standings_table(response, tourney, show_draws_column,
        show_points_column, show_spread_column, show_first_second_column=False,
        linkify_players=False, show_tournament_rating_column=None,
        show_qualified=False, which_division=None, show_finals_column=True,
        rank_finals=None, starting_from_round=1):
    response.writeln(make_standings_table(tourney, show_draws_column,
        show_points_column, show_spread_column, show_first_second_column,
        linkify_players, show_tournament_rating_column, show_qualified,
        which_division, show_finals_column, rank_finals, starting_from_round))

def make_standings_table(tourney, show_draws_column, show_points_column,
        show_spread_column, show_first_second_column=False,
        linkify_players=False, show_tournament_rating_column=None,
        show_qualified=False, which_division=None, show_finals_column=True,
        rank_finals=None, starting_from_round=1):
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

    if rank_finals is None:
        rank_finals = tourney.get_rank_finals()

    if show_tournament_rating_column is None:
        show_tournament_rating_column = tourney.get_show_tournament_rating_column()

    html.append("<table class=\"ranktable\">")
    for div_index in div_list:
        if starting_from_round > 1:
            standings = tourney.get_standings_from_round_onwards(div_index, starting_from_round)
        else:
            standings = tourney.get_standings(div_index, rank_finals=rank_finals)
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
            if finals_form and show_finals_column:
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
                html.append("<td class=\"rankright winlossform\">%s</td>" % (finals_form.upper()))
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
        return "<a class=\"playerlink%s%s\" href=\"/atropine/%s/player/%d\" %s%s>%s</a>" % (
            "withdrawn" if withdrawn else " ",
            " thisplayerlink" if emboldenise else "",
            escape(tourney_name), player.get_id(),
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

def win_loss_string_to_html(win_loss_string):
    html = []
    for x in win_loss_string.upper():
        if x in "WDL":
            wdl_class = "wdl_" + x.lower()
        elif x == "-":
            x = "&ndash;"
            wdl_class = "wdl_unplayed"
        else:
            wdl_class = ""
        html.append("<span class=\"wdl %s\">%s</span>" % (wdl_class, x))
    return "".join(html)

def show_division_drop_down_box(response, control_name, tourney, player):
    num_divisions = tourney.get_num_divisions()
    response.writeln("<select name=\"%s\">" % (escape(control_name, True)))
    for div in range(num_divisions):
        response.writeln("<option value=\"%d\" %s >%s (%d active players)</option>" % (div,
                "selected" if (player is not None and div == player.get_division()) or (player is None and div == 0) else "",
                escape(tourney.get_division_name(div)),
                tourney.get_num_active_players(div)))
    response.writeln("</select>")

def show_player_form(response, tourney, player, custom_query_string=""):
    # Output HTML for a form for adding a new player (if player is None) or
    # editing an existing player (if player is not None).
    num_divisions = tourney.get_num_divisions()
    tourneyname = tourney.get_name()
    if player:
        player_id = player.get_id()
    else:
        player_id = None

    response.writeln("<form method=\"POST\" %s>" % (("action=\"?" + escape(custom_query_string) + "\"") if custom_query_string else ""))
    response.writeln("<table>")
    response.writeln("<tr><td>Name</td><td><input type=\"text\" name=\"setname\" value=\"%s\" /></td></tr>" % ("" if not player else escape(player.get_name(), True)))
    response.writeln("<tr><td>Rating</td><td><input style=\"width: 5em;\" type=\"text\" name=\"setrating\" value=\"%g\"/>" % (1000 if not player else player.get_rating()))
    response.writeln("<span class=\"playercontrolhelp\">(1000 is the default; 0 will make this player a Prune)</span>")
    response.writeln("</td></tr>")
    if num_divisions > 1:
        response.writeln("<tr><td>Division</td>")
        response.writeln("<td>")
        show_division_drop_down_box(response, "setdivision", tourney, player)
        response.writeln("</td></tr>")

    # Only show withdrawn checkbox for "add new player..." form. For the "edit
    # player" form, we have a specific form to withdraw or reinstate.
    if not player:
        response.writeln("<tr><td>Withdrawn?</td><td><input type=\"checkbox\" name=\"setwithdrawn\" value=\"1\" %s /> <span class=\"playercontrolhelp\">(if ticked, fixture generators will not include this player)</span></td></tr>" % ("checked" if player and player.is_withdrawn() else ""))

    if tourney.has_accessible_table_feature():
        response.writeln("<tr><td>Requires accessible table?</td><td><input type=\"checkbox\" name=\"setrequiresaccessibletable\" value=\"1\" %s /> <span class=\"playercontrolhelp\">(if ticked, fixture generators will place this player and their opponents on an accessible table, as defined in <a href=\"/atropine/%s/tourneysetup\">Tourney Setup</a>)</span></td></tr>" % (
            "checked" if player and player.is_requiring_accessible_table() else "",
            escape(tourneyname)
        ))

    if tourney.has_preferred_table_feature():
        if player is None:
            pref = None
        else:
            pref = player.get_preferred_table()
        response.writeln("<tr><td>Preferred table number</td><td><input type=\"number\" name=\"setpreferredtable\" value=\"%d\" min=\"0\" /> <span class=\"playercontrolhelp\">(player will be assigned this table number if possible; a value of 0 means the player has no specific table preference)</span></td></tr>" % (pref if pref is not None else 0))

    if tourney.has_avoid_prune_feature():
        response.writeln("<tr><td>Avoid Prune?</td><td><input type=\"checkbox\" name=\"setavoidprune\" value=\"1\" %s /> <span class=\"playercontrolhelp\">(if ticked, the Swiss fixture generator will behave as if this player has already played a Prune)</span></td></tr>" % ("checked" if player and player.is_avoiding_prune() else ""))

    if tourney.has_player_newbie_feature():
        response.writeln("<tr><td>Newbie?</td><td><input type=\"checkbox\" name=\"setnewbie\" value=\"1\" %s> <span class=\"playercontrolhelp\">(if ticked, some fixture generators can be made to avoid generating all-newbie tables)</span></td></tr>" % ("checked" if player and player.is_newbie() else ""))
    response.writeln("</table>")
    response.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (escape(tourney.get_name(), True)))
    if player:
        response.writeln("<input type=\"hidden\" name=\"id\" value=\"%d\" />" % (player_id))

    if player:
        response.writeln("<input type=\"submit\" name=\"editplayer\" class=\"bigbutton\" style=\"margin-top: 10px;\" value=\"Save Changes\" />")
    else:
        response.writeln("<input type=\"submit\" name=\"newplayersubmit\" class=\"bigbutton\" style=\"margin-top: 10px\" value=\"Create Player\" />")
    response.writeln("</form>")

def int_or_none(s):
    if s is None:
        return None;
    try:
        return int(s);
    except ValueError:
        return None;

def int_or_zero(s):
    if s is None:
        return 0
    try:
        return int(s)
    except ValueError:
        return 0

def float_or_none(s):
    if s is None:
        return None;
    try:
        return float(s);
    except ValueError:
        return None;

def add_new_player_from_form(tourney, form):
    new_player_name = form.getfirst("setname")

    # If no rating has been entered, default to 1000
    rating_str = form.getfirst("setrating")
    if rating_str is None or rating_str.strip() == "":
        new_player_rating = 1000.0
    else:
        new_player_rating = float_or_none(rating_str)
    new_player_division = int_or_none(form.getfirst("setdivision"))
    if new_player_division is None:
        new_player_division = 0
    new_withdrawn = int_or_zero(form.getfirst("setwithdrawn"))
    new_avoid_prune = int_or_zero(form.getfirst("setavoidprune"))
    new_requires_accessible_table = int_or_zero(form.getfirst("setrequiresaccessibletable"))
    new_preferred_table = int_or_none(form.getfirst("setpreferredtable"))
    new_newbie = int_or_zero(form.getfirst("setnewbie"))
    tourney.add_player(new_player_name, new_player_rating, new_player_division)
    if new_withdrawn:
        tourney.set_player_withdrawn(new_player_name, True)
    if new_avoid_prune:
        tourney.set_player_avoid_prune(new_player_name, True)
    if new_requires_accessible_table:
        tourney.set_player_requires_accessible_table(new_player_name, True)
    if new_preferred_table:
        tourney.set_player_preferred_table(new_player_name, new_preferred_table)
    if new_newbie:
        tourney.set_player_newbie(new_player_name, True)
