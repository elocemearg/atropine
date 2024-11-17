#!/usr/bin/python3

# Substitute for the cgitb module which is being removed from Python in
# version 3.13. Call htmltraceback.enable() to set sys.excepthook to attempt
# printing an uncaught exception in an HTML page.

import sys
import traceback
import html

def escape(string, quote=True):
    if string is None:
        return "(None)"
    else:
        return html.escape(string, quote)

def write_html_traceback(response, typ, value, tb):
    response.writeln(">")
    response.writeln("""
<div id="traceback_background" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgb(64, 64, 64, 0.7); text-align: center;">
<div style="position: relative; display: inline-block; min-width: 600px; max-width: min(80vw, 1200px); box-shadow: 5px 5px 10px black; border: 3px groove gray; border-radius: 6px; background-color: hsl(0deg, 50%, 80%);">
<div style="display: block; text-align: left; padding: 20px;">
<h1>Uncaught exception!</h1>
<div style="padding: 10px; margin-top: 20px;">
<button type="button" onclick="document.getElementById('traceback_background').style.display = 'none'; return false;">Close</button>
</div>
<p>
In the course of generating this page, an exception has been thrown which
wasn't caught. The rest of this page will not be generated.
</p>
<p>
Please report this as a bug if you haven't done so already. When you do so,
please also screenshot or copy-paste all the information below. It will help to
diagnose and fix the
problem.
</p>
""")

    table = [
            ( "Python version", "%s, %s" % (escape(sys.version.split()[0]), escape(sys.executable)) ),
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
    lines = traceback.format_tb(tb)
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

    response.writeln("""
</div>
</div>
</div>
""")
    
    response.writeln("</body></html>")
