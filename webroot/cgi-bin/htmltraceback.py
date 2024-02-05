#!/usr/bin/python3

# Substitute for the cgitb module which is being removed from Python in
# version 3.13. Call htmltraceback.enable() to set sys.excepthook to attempt
# printing an uncaught exception in an HTML page.

import sys
import traceback
from cgicommon import writeln, escape

def html_traceback_hook(typ, value, tb):
    writeln(">")
    writeln("""
<div id="traceback_background" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgb(64, 64, 64, 0.7); text-align: center;">
<div style="position: relative; display: inline-block; min-width: 600px; max-width: min(80vw, 1200px); box-shadow: 5px 5px 10px black; border: 3px groove gray; border-radius: 6px; background-color: hsl(0deg, 50%, 80%);">
<div style="display: block; text-align: left; padding: 20px;">
<h1>Uncaught exception!</h1>
<p>
In the course of generating this page, this CGI script has thrown an exception
which wasn't caught. The rest of this page will not be generated.
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
    writeln("<table>")
    for row in table:
        writeln("<tr>")
        writeln("<td style=\"font-weight: bold; padding-right: 1em;\">" + row[0] + "</td>")
        writeln("<td style=\"font-family: monospace;\">" + row[1] + "</td>")
        writeln("</tr>")
    writeln("</table>")

    writeln("<p style=\"font-weight: bold;\">Traceback:</p>")
    writeln("<table style=\"background-color: white; font-family: monospace\">")
    lines = traceback.format_tb(tb)
    row_num = 0
    traceback_background_colors = [ "#ddffdd", "#bbffbb" ]
    for line in lines:
        writeln("<tr style=\"background-color: %s; border-bottom: 1px solid gray;\">" % (traceback_background_colors[row_num % 2]))
        writeln("<td>" + escape(line).replace("\n", "<br>").replace(" ", "&nbsp;"))
        writeln("</td>")
        writeln("</tr>")
        row_num += 1
    writeln("</table>")

    writeln("<!--")
    writeln("Here's that same information again in plain text, just in case you aren't reading this in a browser...")
    writeln()
    writeln("Python version: %s, %s" % (sys.version.split()[0], sys.executable))
    writeln("Exception type: " + str(typ).replace("-->", "- - >"))
    writeln("Exception value: " + str(value).replace("-->", "- - >"))
    writeln()
    writeln("Traceback:")
    writeln()
    for line in lines:
        writeln(line.replace("-->", "- - >"))
    writeln("-->")

    writeln("""
    <div style="text-align: right; padding: 10px; margin-top: 20px;">
    <button type="button" onclick="document.getElementById('traceback_background').style.display = 'none'; return false;">Close</button>
    </div>
</div>
</div>
</div>
""")
    
    writeln("</body></html>")

def enable():
    sys.excepthook = html_traceback_hook
