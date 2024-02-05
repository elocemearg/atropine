#!/usr/bin/python3

import sys
import cgicommon
from cgicommon import writeln, escape
import urllib.request, urllib.parse, urllib.error
import htmltraceback
import re
import os

htmltraceback.enable()

def include_scripts(dir_name, url_path):
    for filename in sorted(os.listdir(dir_name)):
        if (os.path.isdir(dir_name + "/" + filename)):
            include_scripts(dir_name + "/" + filename, url_path + "/" + filename)
        elif filename[-3:] == ".js":
            base_filename = os.path.basename(filename)
            cgicommon.writeln("<script src=\"%s/%s\"></script>" % (cgicommon.escape(url_path, True), cgicommon.escape(base_filename, True)))

def print_html_head(title, font_defs_css):
    writeln("<!DOCTYPE html>")
    writeln("<html lang=\"en\">")
    writeln("<head>");
    writeln("<title>%s</title>" % (escape(title)));
    writeln("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />");
    if font_defs_css:
        escaped = escape(font_defs_css, True)
        writeln("<link rel=\"stylesheet\" type=\"text/css\" id=\"linkcssfont\" href=\"/teleost/style/%s\" relativepath=\"/teleost/style/%s\"/>" % (escaped, escaped))
    writeln("<link rel=\"stylesheet\" type=\"text/css\" href=\"/teleost/style/main.css\" />");
    writeln("<link rel=\"shortcut icon\" href=\"/favicon.ico\" type=\"image/x-icon\" />")
    writeln("<link rel=\"shortcut icon\" href=\"/favicon.png\" type=\"image/png\" />")
    writeln("</head>");

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

form = cgicommon.FieldStorage()
tourney_name = form.getfirst("tourney")
mode = form.getfirst("mode")
if mode is not None:
    try:
        mode = int(mode)
    except ValueError:
        mode = None

cgicommon.set_module_path()
font_defs_css = "fontdefs.css"

import countdowntourney

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
except countdowntourney.TourneyException as e:
    print_html_head("Display: " + str(tourney_name), font_defs_css)
    cgicommon.writeln("<body>")
    cgicommon.writeln("<p>")
    cgicommon.writeln(cgicommon.escape(e.description))
    cgicommon.writeln("</p>")
    cgicommon.writeln("</body></html>")
    sys.exit(0)

# Look up the value of the display font profile option. Use this as an index
# into DISPLAY_FONT_PROFILES to get the appropriate CSS filename.
display_font_profile = tourney.get_display_font_profile_id()
font_defs_css = countdowntourney.DISPLAY_FONT_PROFILES[display_font_profile]["cssfile"]

print_html_head("Display: " + str(tourney_name), font_defs_css)

teleost_modes = tourney.get_teleost_modes()

cgicommon.writeln("<body class=\"display\" onload=\"displaySetup();\">")

cgicommon.writeln("<script>")
cgicommon.writeln("const tourneyName = \"%s\";" % (tourney_name));

if mode is None:
    cgicommon.writeln("const displayMode = -1;") # display whatever the db says the current mode is
else:
    cgicommon.writeln("const displayMode = %d;" % (mode))

for mode in teleost_modes:
    cgicommon.writeln("const %s = %d;" % (mode["id"], mode["num"]))

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
