#!/usr/bin/python3

import cgicommon
import urllib
import time
import html
import countdowntourney
import uploadercli
import uploader

colive_url_base = "https://%s%s/co" % (uploader.http_server_host, (":" + str(uploader.http_server_port) if uploader.http_server_port else ""))

def unix_time_to_str(unix_time):
    if unix_time is None:
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(unix_time))

def handle(httpreq, response, tourney, request_method, form, query_string):
    tourney_name = tourney.get_name()

    cgicommon.print_html_head(response, "Live Broadcast Setup: %s" % (tourney_name))

    response.writeln("<body>")

    httpreq.assert_client_from_localhost()

    cgicommon.show_sidebar(response, tourney)

    response.writeln("<div class=\"mainpane\">")
    response.writeln("<h1>Live Broadcast Setup</h1>")

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
        cgicommon.show_error_text(response, exception_context + ": " + exception_text)
    if delete_success:
        cgicommon.show_success_box(response, "Successfully deleted tourney <strong>%s</strong> from the website." % (cgicommon.escape(tourney_name)))

    web_link = colive_url_base + "/" + cgicommon.escape(tourney_name, True)
    web_link_raw = colive_url_base + "/" + tourney_name
    response.writeln("<p>This will upload the tourney state every few seconds so that games, scores and standings are visible at <a href=\"%s\" target=\"_blank\">%s <img src=\"/images/opensinnewwindow.png\" alt=\"Opens in new window\"/></a></p>" % (web_link, web_link))
    response.writeln("""
<p>You will need:</p>
<ul>
<li>A username and password for the server at %(httpserverhost)s. If you don't have these, then ignore this whole feature. Just pretend it doesn't exist.</li>
<li>A connection to the internet.</li>
</ul>
<p>
You can manage your account and published tourneys at
<a href="%(coliveadminurl)s" target="_blank">%(coliveadminurl)s <img src="/images/opensinnewwindow.png" alt="Opens in new window"/></a>
</p>
<p>
If you lose internet access, uploads will be suspended but everything that
doesn't require internet access such as results entry, fixture generation and
the public display window will be unaffected. Uploads to the server will resume
when the internet connection is restored.
</p>
""" % {
        "coliveadminurl" : "https://" + uploader.http_server_host + "/coliveadmin",
        "httpserverhost" : uploader.http_server_host
    })

    response.writeln("<div class=\"formbox\">")
    response.writeln("<form action=\"uploadsetup.py?tourney=%s\" method=\"POST\">" % (urllib.parse.quote_plus(tourney_name)))

    form_info = [
            { "type" : "text", "name" : "username", "label" : "Username",
                "autocomplete" : "username", "value" : username },
            { "type" : "password", "name" : "password", "label" : "Password",
                "autocomplete" : "current-password", "value" : password }
    ]
    for info in form_info:
        response.writeln("<div class=\"formline\">")
        response.writeln("""<div class="formlabel" style="width: 7em;">
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
        response.writeln("</div>")
    response.writeln("<div class=\"formline\">")
    response.writeln("<div class=\"formlabel\" style=\"width: 7em;\">")
    response.writeln("Unlisted")
    response.writeln("</div>")
    response.writeln("<div class=\"formcontrol\">")
    response.writeln("<input type=\"checkbox\" name=\"privatetourney\" id=\"privatetourney\" %s %s />" % ("checked" if private_tourney else "", "disabled" if upload_on else ""))
    response.writeln("<label for=\"privatetourney\" style=\"font-size: 10pt; color: gray;\">If ticked, this tourney will not appear in the public list and will be visible only to people with the link. This is useful if you're just testing things.</label>")
    response.writeln("</div>")
    response.writeln("</div>")

    response.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney_name)))
    if show_delete_confirm:
        warning_html = "<div class=\"formline\">\n"
        warning_html += "<p>Are you sure you want to delete the tourney <strong>%s</strong> from the web?</p>\n" % (cgicommon.escape(tourney_name))
        warning_html += "<p>If you click Confirm below, <a href=\"%s/%s\" target=\"_blank\">this tourney called <strong>%s</strong></a> will be deleted from the website.</p>\n" % (
            colive_url_base, cgicommon.escape(tourney_name, True),
            cgicommon.escape(tourney_name))
        warning_html += "<p>Your local copy of this tourney will not be affected.</p>\n"
        warning_html += "</div>\n"
        warning_html += "<div class=\"formline submitline\">\n"
        warning_html += "<input type=\"submit\" name=\"submitdeletefromwebconfirm\" value=\"Confirm\" class=\"bigbutton destroybutton\" />\n"
        warning_html += "<input type=\"submit\" name=\"submitdeletefromwebcancel\" value=\"Cancel\" class=\"bigbutton chickenoutbutton\" />\n"
        warning_html += "</div>\n"
        cgicommon.show_warning_box(response, warning_html, True)
    else:
        response.writeln("<div class=\"formline submitline\">")
        response.writeln("<input type=\"submit\" name=\"%s\" value=\"%s\" class=\"bigbutton\" />" % (
            "submitstopuploading" if upload_on else "submitstartuploading",
            "Stop Broadcasting" if upload_on else "Start Broadcasting"
        ))

        if not upload_on:
            response.writeln("<input type=\"submit\" name=\"submitdeletefromweb\" value=\"Delete from website\" class=\"bigbutton\" />")
        response.writeln("</div>")
    response.writeln("</form>")
    response.writeln("</div>") #formbox

    if not show_delete_confirm:
        response.writeln("""<div class="uploadconsole">
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

    response.writeln("""
<script>
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

function uploadConsoleRefresh(enabled, success, numViewers, secondsOfFailure,
        errorMessage, uploadWidgetFailureIsHTTP, lastAttemptFailed,
        uploaderThreadFailed) {
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
        statusDiv.innerText = "Connected";
        statusDiv.style.backgroundColor = "green";
        statusDiv.style.color = "white";
        statusDiv.style.display = null;

        if (numViewers != null) {
            statusDiv.innerText += ", " + numViewers.toString() + " viewing";
        }
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
</script>
""")

    response.writeln("</div>") #mainpane
    response.writeln("</body>")
    response.writeln("</html>")
