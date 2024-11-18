#!/usr/bin/python3

import os
import htmlcommon
import countdowntourney

def include_scripts(response, dir_name, url_path):
    for filename in sorted(os.listdir(dir_name)):
        if (os.path.isdir(dir_name + "/" + filename)):
            include_scripts(response, dir_name + "/" + filename, url_path + "/" + filename)
        elif filename[-3:] == ".js":
            base_filename = os.path.basename(filename)
            response.writeln("<script src=\"%s/%s\"></script>" % (htmlcommon.escape(url_path, True), htmlcommon.escape(base_filename, True)))

def print_html_head(response, title, font_defs_css):
    response.writeln("<!DOCTYPE html>")
    response.writeln("<html lang=\"en\">")
    response.writeln("<head>");
    response.writeln("<title>%s</title>" % (htmlcommon.escape(title)));
    response.writeln("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />");
    if font_defs_css:
        escaped = htmlcommon.escape(font_defs_css, True)
        response.writeln("<link rel=\"stylesheet\" type=\"text/css\" id=\"linkcssfont\" href=\"/teleost/style/%s\" relativepath=\"/teleost/style/%s\"/>" % (escaped, escaped))
    response.writeln("<link rel=\"stylesheet\" type=\"text/css\" href=\"/teleost/style/main.css\" />");
    response.writeln("<link rel=\"shortcut icon\" href=\"/favicon.ico\" type=\"image/x-icon\" />")
    response.writeln("<link rel=\"shortcut icon\" href=\"/favicon.png\" type=\"image/png\" />")
    response.writeln("</head>");

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    content_type = "text/html; charset=utf-8"
    tourney_name = tourney.get_name()
    mode = form.getfirst("mode")
    if mode is not None:
        try:
            mode = int(mode)
        except ValueError:
            mode = None

    font_defs_css = "fontdefs.css"

    # Look up the value of the display font profile option. Use this as an index
    # into DISPLAY_FONT_PROFILES to get the appropriate CSS filename.
    display_font_profile = tourney.get_display_font_profile_id()
    font_defs_css = countdowntourney.DISPLAY_FONT_PROFILES[display_font_profile]["cssfile"]

    print_html_head(response, "Display: " + str(tourney_name), font_defs_css)

    teleost_modes = tourney.get_teleost_modes()

    response.writeln("<body class=\"display\" onload=\"displaySetup();\">")

    response.writeln("<script>")
    response.writeln("const tourneyName = \"%s\";" % (tourney_name));

    if mode is None:
        response.writeln("const displayMode = -1;") # display whatever the db says the current mode is
    else:
        response.writeln("const displayMode = %d;" % (mode))

    for mode in teleost_modes:
        response.writeln("const %s = %d;" % (mode["id"], mode["num"]))

    response.writeln("</script>")

    # Load main.js first
    response.writeln("<script src=\"/teleost/main.js\"></script>")

    # Now load everything under teleost/views, loading the files and contents
    # of directories in alphabetical order. The order is important, because
    # some files depend on others.
    include_scripts(response, "./teleost/views", "/teleost/views")

    # Finally, load main_post.js
    response.writeln("<script src=\"/teleost/main_post.js\"></script>")

    response.writeln("<div id=\"teleostbanner\">")
    response.writeln("</div>")

    response.writeln("<div id=\"displaymainpane\">")
    response.writeln("</div>")

    response.writeln("</body>")
    response.writeln("</html>")
