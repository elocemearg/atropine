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
            print("<script type=\"text/javascript\" src=\"%s/%s\"></script>" % (cgi.escape(url_path, True), cgi.escape(base_filename, True)))

print("Content-Type: text/html; charset=utf-8")
print("")

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
    print("<body>")
    print("<p>")
    print(cgi.escape(e.description))
    print("</p>")
    print("</body></html>")
    sys.exit(0)

teleost_modes = tourney.get_teleost_modes()

print("<script type=\"text/javascript\">")
print("var tourneyName = \"%s\";" % (tourney_name));

if mode is None:
    print("var displayMode = -1;") # display whatever the db says the current mode is
else:
    print("var displayMode = %d;" % (mode))

for mode in teleost_modes:
    print("var %s = %d;" % (mode["id"], mode["num"]))

print("</script>")

# Load main.js first
print("<script type=\"text/javascript\" src=\"/teleost/main.js\"></script>")

# Now load everything under teleost/views, loading the files and contents of
# directories in alphabetical order. The order is important, because some files
# depend on others.
include_scripts("./teleost/views", "/teleost/views")

# Finally, load main_post.js
print("<script type=\"text/javascript\" src=\"/teleost/main_post.js\"></script>")

print("<body class=\"display\" onload=\"displaySetup();\">")

if tourney_name is None:
    cgicommon.show_tourney_exception(countdowntourney.TourneyException("No tourney name specified."))
    print("</body>")
    print("</html>")
    sys.exit(0)

print("<div id=\"teleostbanner\">")
print("</div>")

print("<div id=\"displaymainpane\">")
print("</div>")

print("</body>")
print("</html>")
