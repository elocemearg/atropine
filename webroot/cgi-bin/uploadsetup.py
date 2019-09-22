#!/usr/bin/python3

import sys
import os
import cgi
import cgitb
import cgicommon
import urllib
import time
import html

cgitb.enable()
cgicommon.set_module_path()

import countdowntourney
import uploadercli
import uploader

colive_url_base = "https://%s%s/co" % (uploader.http_server_host, (":" + str(uploader.http_server_port) if uploader.http_server_port else ""))

def unix_time_to_str(unix_time):
    if unix_time is None:
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(unix_time))

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

form = cgi.FieldStorage()
tourney_name = form.getfirst("tourney")

cgicommon.print_html_head("Live Broadcast Setup: %s" % (tourney_name))

cgicommon.writeln("<body>")

cgicommon.assert_client_from_localhost()

tourney = None
if tourney_name is not None:
    try:
        tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
    except countdowntourney.TourneyException as e:
        cgicommon.show_tourney_exception(e);
        cgicommon.writeln("<p><a href=\"/cgi-bin/home.py\">Home</a></p>")
        cgicommon.writeln("</body></html>")
        sys.exit(1)

cgicommon.show_sidebar(tourney)

cgicommon.writeln("<div class=\"mainpane\">")
cgicommon.writeln("<h1>Live Broadcast Setup</h1>")

if tourney_name is None:
    show_error_text("No tourney name specified in query string")
elif tourney is None:
    show_error_text("No valid tourney name specified")
else:
    request_method = os.environ.get("REQUEST_METHOD", "")
    username = ""
    password = ""
    private_tourney = None

    exception_context = None
    exception_text = None
    upload_on = False
    show_delete_confirm = False
    delete_success = False

    if request_method == "POST":
        try:
            username = form.getfirst("username", "")
            password = form.getfirst("password", "")
            if form.getfirst("submitstartuploading"):
                private_tourney = ("privatetourney" in form)
                uploadercli.start_uploading(tourney_name, username, password, private_tourney)
                tourney.set_broadcast_private(private_tourney)
                upload_on = True
            elif form.getfirst("submitstopuploading"):
                uploadercli.stop_uploading(tourney_name)
                upload_on = False
            elif form.getfirst("submitdeletefromweb"):
                show_delete_confirm = True
            elif form.getfirst("submitdeletefromwebconfirm"):
                uploadercli.delete_tourney_from_web(tourney_name, username, password)
                delete_success = True
        except uploadercli.UploaderClientException as e:
            exception_text = str(e)
            exception_context = "Request to website failed"

    try:
        state = uploadercli.get_tourney_upload_state(tourney_name)
    except uploadercli.UploaderClientException:
        state = {}

    if not username:
        username = state.get("username", "")
    if not password:
        password = state.get("password", "")
    if private_tourney is None:
        private_tourney = state.get("private", None)
        if private_tourney is None:
            private_tourney = tourney.is_broadcast_private()

    upload_on = state.get("publishing", False)

    if exception_text:
        cgicommon.show_error_text(exception_context + ": " + exception_text)
    if delete_success:
        cgicommon.show_success_box("Successfully deleted tourney <strong>%s</strong> from the website." % (cgicommon.escape(tourney_name)))

    web_link = colive_url_base + "/" + cgi.escape(tourney_name, True)
    web_link_raw = colive_url_base + "/" + tourney_name
    cgicommon.writeln("<p>This will upload the tourney state every few seconds so that games, scores and standings are visible at <a href=\"%s\" target=\"_blank\">%s <img src=\"/images/opensinnewwindow.png\" alt=\"Opens in new window\"/></a></p>" % (web_link, web_link))
    cgicommon.writeln("<p>You will need:</p>")
    cgicommon.writeln("<ul>")
    cgicommon.writeln("<li>A username and password for the server at %s. If you don't have these, then ignore this whole feature. Just pretend it doesn't exist.</li>" % (cgi.escape(uploader.http_server_host)))
    cgicommon.writeln("<li>A connection to the internet.</li>")
    cgicommon.writeln("</ul>")
    cgicommon.writeln("<p>If you lose internet access, uploads will be suspended but everything that doesn't require internet access such as results entry, fixture generation and the public display window will be unaffected. Uploads to the server will resume when the internet connection is restored.</p>")

    cgicommon.writeln("<div class=\"formbox\">")
    cgicommon.writeln("<form action=\"uploadsetup.py?tourney=%s\" method=\"POST\">" % (urllib.parse.quote_plus(tourney_name)))

    form_info = [
            { "type" : "text", "name" : "username", "label" : "Username",
                "autocomplete" : "username", "value" : username },
            { "type" : "password", "name" : "password", "label" : "Password",
                "autocomplete" : "current-password", "value" : password }
    ]
    for info in form_info:
        cgicommon.writeln("<div class=\"formline\">")
        cgicommon.writeln("""<div class="formlabel" style="width: 7em;">
        <label for="%s">%s</label>
        </div>
        <div class="formcontrol">
        <input type="%s" name="%s" id="%s" value="%s" autocomplete="%s" %s />
        </div>""" % (
            cgicommon.escape(info["name"]),
            cgicommon.escape(info["label"]),
            cgicommon.escape(info["type"]),
            cgicommon.escape(info["name"]),
            cgicommon.escape(info["name"]),
            cgicommon.escape(info["value"]),
            cgicommon.escape(info["autocomplete"]),
            "class=\"noteditable\" readonly" if upload_on else "")
        )
        cgicommon.writeln("</div>")
    cgicommon.writeln("<div class=\"formline\">")
    cgicommon.writeln("<div class=\"formlabel\" style=\"width: 7em;\">")
    cgicommon.writeln("Unlisted")
    cgicommon.writeln("</div>")
    cgicommon.writeln("<div class=\"formcontrol\">")
    cgicommon.writeln("<input type=\"checkbox\" name=\"privatetourney\" id=\"privatetourney\" %s %s />" % ("checked" if private_tourney else "", "disabled" if upload_on else ""))
    cgicommon.writeln("<label for=\"privatetourney\" style=\"font-size: 10pt; color: gray;\">If ticked, this tourney will not appear in the public list and will be visible only to people with the link. This is useful if you're just testing things.</label>")
    cgicommon.writeln("</div>")
    cgicommon.writeln("</div>")

    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney_name)))
    if show_delete_confirm:
        warning_html = "<div class=\"formline\">\n"
        warning_html += "<p>Are you sure you want to delete the tourney <strong>%s</strong> from the web?</p>\n" % (cgicommon.escape(tourney_name))
        warning_html += "<p>If you click Confirm below, <a href=\"%s/%s\" target=\"_blank\">this tourney called <strong>%s</strong></a> will be deleted from the website.</p>\n" % (
            colive_url_base, cgi.escape(tourney_name, True),
            cgicommon.escape(tourney_name))
        warning_html += "<p>Your local copy of this tourney will not be affected.</p>\n"
        warning_html += "</div>\n"
        warning_html += "<div class=\"formline submitline\">\n"
        warning_html += "<input type=\"submit\" name=\"submitdeletefromwebconfirm\" value=\"Confirm\" class=\"bigbutton destroybutton\" />\n"
        warning_html += "<input type=\"submit\" name=\"submitdeletefromwebcancel\" value=\"Cancel\" class=\"bigbutton chickenoutbutton\" />\n"
        warning_html += "</div>\n"
        cgicommon.show_warning_box(warning_html, True)
    else:
        cgicommon.writeln("<div class=\"formline submitline\">")
        cgicommon.writeln("<input type=\"submit\" name=\"%s\" value=\"%s\" class=\"bigbutton\" />" % (
            "submitstopuploading" if upload_on else "submitstartuploading",
            "Stop Broadcasting" if upload_on else "Start Broadcasting"
        ))

        if not upload_on:
            cgicommon.writeln("<input type=\"submit\" name=\"submitdeletefromweb\" value=\"Delete from website\" class=\"bigbutton\" />")
        cgicommon.writeln("</div>")
    cgicommon.writeln("</form>")
    cgicommon.writeln("</div>") #formbox

    if not show_delete_confirm:
        cgicommon.writeln("""<div class="uploadconsole">
<div class="uploadconsoleenabled" id="uploadconsoleenabled"></div>
<div class="uploadconsolestatus" id="uploadconsolestatus"></div>
<div class="uploadconsolediag" id="uploadconsolediag">
</div>
    <div class="shareablelinkbox" id="shareablelinkbox" style="display: none;" >
    <div style="font-size: 10pt; color: gray;">Shareable link</div>
    <input type="text" name="linktext" id="linktext" value="%s" style="width: 270px; background-color: #eee;" readonly />
    <button type="button" onclick="copyLink();" style="width: 155px; float: right">Copy to clipboard</button>
    </div>
</div>
    """ % (html.escape(web_link_raw)))
    #<div style="display: inline-block; width: 120px;">Shareable link</div>
    
    cgicommon.writeln("""
<script>
// <!--

function copyLink() {
    var element = document.getElementById("linktext");
    if (element != null) {
        element.focus();
        element.select();
        try {
            document.execCommand("copy");
        }
        catch (err) {
            console.log("Unable to copy link text");
        }
    }
}

function uploadConsoleRefresh(enabled, success, secondsOfFailure, errorMessage,
            uploadWidgetFailureIsHTTP, lastAttemptFailed, uploaderThreadFailed) {
    var enabledDiv = document.getElementById("uploadconsoleenabled");
    var statusDiv = document.getElementById("uploadconsolestatus");
    var shareableDiv = document.getElementById("shareablelinkbox");

    if (enabledDiv == null || statusDiv == null)
        return;

    if (uploaderThreadFailed) {
        enabledDiv.innerText = "Internal error: uploader thread failed";
        enabledDiv.style.backgroundColor = "black";
        enabledDiv.style.color = "white";
    }
    else if (enabled) {
        enabledDiv.innerText = "Broadcasting enabled";
        enabledDiv.style.backgroundColor = "#88ff88";
        enabledDiv.style.color = "black";
    }
    else {
        enabledDiv.innerText = "Not broadcasting";
        enabledDiv.style.backgroundColor = "white";
        enabledDiv.style.color = "black";
    }

    statusDiv.style.backgroundColor = "white";
    statusDiv.style.color = "black";
    if (!enabled) {
        statusDiv.innerText = "";
        statusDiv.style.display = "none";
    }
    else if (success) {
        statusDiv.innerText = "Running";
        statusDiv.style.backgroundColor = "green";
        statusDiv.style.color = "white";
        statusDiv.style.display = null;
    }
    else {
        statusDiv.style.display = null;
        if (secondsOfFailure > 0 && lastAttemptFailed) {
            statusDiv.innerText = "Failing for " + makeDurationString(secondsOfFailure);
            statusDiv.style.backgroundColor = "#ff0000";
            statusDiv.style.color = "white";
        }
        else {
            /* Haven't had a successful upload for a while, but we haven't
               actually had a failure either */
            statusDiv.innerText = "Please wait...";
            statusDiv.style.backgroundColor = "yellow";
            statusDiv.style.color = "black";
        }
    }

    if (success) {
        shareableDiv.style.display = "block";
    }
    else {
        shareableDiv.style.display = "none";
    }

    var diagDiv = document.getElementById("uploadconsolediag");
    if (errorMessage) {
        diagDiv.innerText = errorMessage;
        diagDiv.style.display = null;
    }
    else {
        diagDiv.innerText = "";
        diagDiv.style.display = "none";
    }
}

uploadWidgetExtraCallback = uploadConsoleRefresh;

-->
</script>
""")

cgicommon.writeln("</div>") #mainpane
cgicommon.writeln("</body>")
cgicommon.writeln("</html>")
