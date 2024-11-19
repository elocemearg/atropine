#!/usr/bin/python3

# Substitute for the cgitb module which is being removed from Python in
# version 3.13. Call htmltraceback.enable() to set sys.excepthook to attempt
# printing an uncaught exception in an HTML page.

import sys
import traceback
import html
import htmlcommon
from htmlcommon import escape

def write_html_exception_page(httpreq, response, exc):
    typ = str(type(exc))
    value = str(exc)
    htmlcommon.print_html_head(response, "Exception")
    response.writeln("""
    <body style=\"background-color: rgb(255, 192, 208);\">
<h1>Uncaught exception!</h1>
<p>An exception has been thrown which wasn't caught. This page will not be generated.</p>
<p>
Please report this as a bug if you haven't done so already. When you do so,
please also screenshot or copy-paste all the information below. It will help to
diagnose and fix the problem.
</p>
""" % {
        "path" : httpreq.path,
    })

    table = [
            ( "Python version", "%s, %s" % (escape(sys.version.split()[0]), escape(sys.executable)) ),
            ( "Request method", escape(httpreq.command)),
            ( "Request path and query", escape(httpreq.path) ),
            ( "Exception type", escape(str(typ)) ),
            ( "Exception value", escape(str(value)) )
    ]
    response.writeln("<table>")
    for row in table:
        response.writeln("<tr>")
        response.writeln("<td style=\"font-weight: bold; padding-right: 1em;\">" + row[0] + "</td>")
        response.writeln("<td style=\"font-family: monospace;\">" + row[1] + "</td>")
        response.writeln("</tr>")
    response.writeln("</table>")

    response.writeln("<p style=\"font-weight: bold;\">Traceback:</p>")
    response.writeln("<table style=\"background-color: white; font-family: monospace\">")
    lines = traceback.format_tb(exc.__traceback__)
    row_num = 0
    traceback_background_colors = [ "#ddffdd", "#bbffbb" ]
    for line in lines:
        response.writeln("<tr style=\"background-color: %s; border-bottom: 1px solid gray;\">" % (traceback_background_colors[row_num % 2]))
        response.writeln("<td>" + escape(line).replace("\n", "<br>").replace(" ", "&nbsp;"))
        response.writeln("</td>")
        response.writeln("</tr>")
        row_num += 1
    response.writeln("</table>")

    response.writeln("<!--")
    response.writeln("Here's that same information again in plain text, just in case you aren't reading this in a browser...")
    response.writeln()
    response.writeln("Python version: %s, %s" % (sys.version.split()[0], sys.executable))
    response.writeln("Exception type: " + str(typ).replace("-->", "- - >"))
    response.writeln("Exception value: " + str(value).replace("-->", "- - >"))
    response.writeln()
    response.writeln("Traceback:")
    response.writeln()
    for line in lines:
        response.writeln(line.replace("-->", "- - >"))
    response.writeln("-->")
    response.writeln("<p><a href=\"/\">Back to the home page</a>")
    response.writeln("</body></html>")
