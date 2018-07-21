#!/usr/bin/python3

import sys
import cgicommon
import urllib.request, urllib.parse, urllib.error
import cgi
import cgitb
import re
import os

cgitb.enable()

def include_scripts(dir_name, url_path):
    for filename in sorted(os.listdir(dir_name)):
        if (os.path.isdir(dir_name + "/" + filename)):
            include_scripts(dir_name + "/" + filename, url_path + "/" + filename)
        elif filename[-3:] == ".js":
            base_filename = os.path.basename(filename)
            cgicommon.writeln("<script src=\"%s/%s\"></script>" % (cgicommon.escape(url_path, True), cgicommon.escape(base_filename, True)))

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

form = cgi.FieldStorage()
tourney_name = form.getfirst("tourney")
mode = form.getfirst("mode")
if mode is not None:
    try:
        mode = int(mode)
    except ValueError:
        mode = None

cgicommon.set_module_path()

import countdowntourney

cgicommon.print_html_head("Display: " + str(tourney_name), cssfile="teleoststyle.css")

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
except countdowntourney.TourneyException as e:
    cgicommon.writeln("<body>")
    cgicommon.writeln("<p>")
    cgicommon.writeln(cgicommon.escape(e.description))
    cgicommon.writeln("</p>")
    cgicommon.writeln("</body></html>")
    sys.exit(0)

teleost_modes = tourney.get_teleost_modes()

cgicommon.writeln("<body class=\"display\" onload=\"displaySetup();\">")

cgicommon.writeln("<script>")
cgicommon.writeln("var tourneyName = \"%s\";" % (tourney_name));

if mode is None:
    cgicommon.writeln("var displayMode = -1;") # display whatever the db says the current mode is
else:
    cgicommon.writeln("var displayMode = %d;" % (mode))

for mode in teleost_modes:
    cgicommon.writeln("var %s = %d;" % (mode["id"], mode["num"]))

cgicommon.writeln("</script>")

# Load main.js first
cgicommon.writeln("<script src=\"/teleost/main.js\"></script>")

# Now load everything under teleost/views, loading the files and contents of
# directories in alphabetical order. The order is important, because some files
# depend on others.
include_scripts("./teleost/views", "/teleost/views")

# Finally, load main_post.js
cgicommon.writeln("<script src=\"/teleost/main_post.js\"></script>")


if tourney_name is None:
    cgicommon.show_tourney_exception(countdowntourney.TourneyException("No tourney name specified."))
    cgicommon.writeln("</body>")
    cgicommon.writeln("</html>")
    sys.exit(0)

cgicommon.writeln("<div id=\"teleostbanner\">")
cgicommon.writeln("</div>")

cgicommon.writeln("<div id=\"displaymainpane\">")
cgicommon.writeln("</div>")

cgicommon.writeln("</body>")
cgicommon.writeln("</html>")
