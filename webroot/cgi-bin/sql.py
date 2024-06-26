#!/usr/bin/python3

import htmltraceback
import cgicommon
import os
import sqlite3
import urllib.parse
import re

import sys

class Column(object):
    def __init__(self, seq, name, typ):
        self.seq = seq
        self.name = name
        self.type = typ

    def get_name(self):
        return self.name

    def get_type(self):
        return self.type

class Table(object):
    def __init__(self, name):
        self.name = name
        self.columns = []

    def get_name(self):
        return self.name

    def add_column(self, column):
        self.columns.append(column)

    def get_columns(self):
        return self.columns[:]


baseurl = "/cgi-bin/sql.py"

htmltraceback.enable()

cgicommon.writeln("Content-Type: text/html; charset=utf-8")
cgicommon.writeln("")

cgicommon.print_html_head("Raw SQL interface")
cgicommon.assert_client_from_localhost()

form = cgicommon.FieldStorage()

request_method = os.environ.get("REQUEST_METHOD", "")

sql_text = None
execute_sql = None
tourney_name = form.getfirst("tourney")
error_text = None
error_text_context = ""
db = None
result_rows = []
num_result_cols = 0
num_rows_affected = None
result_col_names = []
result_col_types = []
show_warning = True

tables = []
views = []

if form.getfirst("nowarning"):
    show_warning = False

if request_method == "POST" and tourney_name:
    sql_text = form.getfirst("sql")
    execute = form.getfirst("execute")
    if execute:
        execute_sql = sql_text

if tourney_name:
    if not re.match("^[A-Za-z0-9_-]+$", tourney_name):
        error_text_context = "Can't open tourney database"
        error_text = "The tourney name is invalid. It may consist only of letters, numbers, underscores and hyphens."
    else:
        db_path = cgicommon.dbdir
        if db_path and db_path[-1] != os.sep:
            db_path += os.sep
        db_path += tourney_name + ".db"
        if not os.path.exists(db_path):
            error_text_context = "Can't open tourney database"
            error_text = "The tourney \"%s\" does not exist." % (tourney_name)
        else:
            db = sqlite3.connect(db_path)

if db and execute_sql:
    # Execute SQL supplied by user, and fetch results if applicable
    try:
        cur = db.cursor()
        cur.execute(execute_sql)
        if cur.description:
            num_result_cols = len(cur.description)
            for col in cur.description:
                result_col_names.append(col[0])
                result_col_types.append(col[1])
            for row in cur:
                result_rows.append(tuple([ str(value) if value is not None else None for value in row ]))
        else:
            num_rows_affected = cur.rowcount
        cur.close()
        db.commit()
    except sqlite3.Error as e:
        error_text_context = "SQL Error"
        error_text = str(e)
    except sqlite3.Warning as e:
        error_text_context = "SQL Warning"
        error_text = str(e)

if db:
    try:
        # Build data dictionary
        cur = db.cursor()
        cur.execute("select type, name from sqlite_master where name not like 'sqlite_%' order by type, name")
        for row in cur:
            table = Table(row[1])
            if row[0] == "table":
                tables.append(table)
            elif row[0] == "view":
                views.append(table)

        cur.close()

        for tl in (tables, views):
            for t in tl:
                try:
                    cur = db.cursor()
                    table_name = t.get_name()
                    if not re.match("^[A-Za-z_][A-Za-z0-9_]*$", table_name):
                        table_name = "\"" + "".join([ x if x != "\"" else "\\\"" for x in table_name ]) + "\""
                    cur.execute("pragma table_info(" + table_name + ")")
                    columns = []
                    for row in cur:
                        columns.append(Column(int(row[0]), row[1], row[2]))
                    columns = sorted(columns, key=lambda c : c.seq)
                    for c in columns:
                        t.add_column(c)
                    cur.close()
                except sqlite3.Error as e:
                    sys.stderr.write("Failed to fetch columns for table " + table_name + ": " + str(e) + "\r\n")
                except sqlite3.Warning as e:
                    sys.stderr.write("Failed to fetch columns for table " + table_name + ": " + str(e) + "\r\n")
        db.commit()
    except sqlite3.Error as e:
        sys.stderr.write("Failed to build data dictionary: " + str(e) + "\r\n")
    except sqlite3.Warning as e:
        sys.stderr.write("Failed to build data dictionary: " + str(e) + "\r\n")

if db:
    db.close()

cgicommon.writeln("<body class=\"scary\" onload=\"bodyLoad();\">")

cgicommon.writeln("""
<script>
function clickTableName(name) {
    var ul = document.getElementById("col_list_" + name);
    var sym = document.getElementById("table_expand_symbol_" + name);
    if (ul != null) {
        if (ul.style.display == "block") {
            ul.style.display = "none";
            if (sym != null) {
                sym.innerHTML = "&#x25b8;"; // right-pointing triangle
            }
        }
        else {
            ul.style.display = "block";
            if (sym != null) {
                sym.innerHTML = "&#x25be;"; // down-pointing triangle
            }
        }
    }
}

function bodyLoad() {
    var textArea = document.getElementById("sql");
    if (textArea != null) {
        textArea.addEventListener("keydown", function(e) {
            if ((e.ctrlKey || e.metaKey) && (e.keyCode == 13 || e.keyCode == 10)) {
                var form = document.getElementById("sqlform");
                if (form != null) {
                    form.submit();
                }
            }
        });
    }
}

function rowHighlight(rowNum, highlightOn) {
    var el = document.getElementById("row" + rowNum.toString());
    if (el) {
        if (highlightOn) {
            el.style.backgroundColor = "#ffffaa";
        }
        else {
            el.style.backgroundColor = null;
        }
    }
}

</script>
""")


# Write the sidebar, but not the normal sidebar, because that requires a
# tourney, and we might not have a usable one.
cgicommon.writeln("<div class=\"sidebar sqlsidebar\">")

cgicommon.writeln("<div style=\"margin-bottom: 20px;\">")
cgicommon.writeln("<img src=\"/images/eyebergine128.png\" alt=\"Eyebergine\" />")
cgicommon.writeln("</div>")

cgicommon.writeln("<div class=\"sqlsidebarname\">")
if tourney_name:
    cgicommon.writeln("<a href=\"/cgi-bin/tourneysetup.py?tourney=%s\">%s</a>" % (urllib.parse.quote_plus(tourney_name), cgicommon.escape(tourney_name)))
cgicommon.writeln("</div>")

# Display list of tables and views, which can be expanded to show columns
if db:
    for (tl, object_type) in ((tables, "Tables"), (views, "Views")):
        cgicommon.writeln("<div class=\"sqldictsection\">")
        cgicommon.writeln("<div class=\"sqldictsectionheading\">%s</div>" % (cgicommon.escape(object_type)))
        cgicommon.writeln("<ul class=\"sqldict\">")
        for tab in tl:
            tab_escaped = cgicommon.escape(tab.get_name())
            tab_sq_escaped = "".join([x if x != '\'' else '\\\'' for x in tab.get_name()])
            cgicommon.writeln("<li class=\"tablename handcursor\" onclick=\"clickTableName('%s');\"><span style=\"display: inline-block; min-width: 0.75em;\" id=\"table_expand_symbol_%s\">&#x25b8;</span> %s</li>" % (
                cgicommon.escape(tab_sq_escaped),
                tab_escaped, tab_escaped))
            cgicommon.writeln("<ul class=\"sqldictcolumnlist\" id=\"col_list_%s\">" % (tab_escaped))
            for col in tab.get_columns():
                cgicommon.writeln("<li>%s (%s)</li>" % (cgicommon.escape(col.get_name()), cgicommon.escape(col.get_type())))
            cgicommon.writeln("</ul>")
        cgicommon.writeln("</ul>")
        cgicommon.writeln("</div>")
else:
    cgicommon.writeln("<p>No database.</p>")

cgicommon.writeln("</div>") #sidebar

cgicommon.writeln("<div class=\"sqlmainpane\">")

if tourney_name:
    cgicommon.writeln("<h1>Raw SQL interface</h1>")

    if show_warning:
        cgicommon.show_warning_box(
                "<div style=\"max-width: 800px;\">" +
                "<p style=\"font-weight: bold;\">Warning!</p>" +
                "<p>This page allows you to run arbitrary SQL on your tourney's " +
                "<a href=\"https://sqlite.org/lang.html\" target=\"_blank\">SQLite</a> " +
                "database. " +
                "It is intended for debugging and emergency database " +
                "surgery by people who know what they're doing.</p>"
                "<p>If you don't know what SQL is or what the various tables " +
                "in the database do, then I strongly recommend that you " +
                "<a href=\"/cgi-bin/tourneysetup.py?tourney=%s\">flee to safety</a>.</p>" % (urllib.parse.quote_plus(tourney_name)) +
                "</div>",
                wide=True
                )
    else:
        cgicommon.writeln("<p><a href=\"https://sqlite.org/lang.html\" target=\"_blank\">SQLite language reference</a></p>")
        cgicommon.writeln("<p><a href=\"/cgi-bin/tourneysetup.py?tourney=%s\">Back to tourney setup</a></p>" % (urllib.parse.quote_plus(tourney_name)))

    cgicommon.writeln("<div class=\"sqlentry\">")

    cgicommon.writeln("<h2>Enter SQL query</h2>")
    cgicommon.writeln("<form id=\"sqlform\" action=\"%s?tourney=%s\" method=\"POST\">" % (baseurl, urllib.parse.quote_plus(tourney_name)))
    cgicommon.writeln("<div class=\"sqlentrybox\">")
    cgicommon.writeln("<textarea autofocus id=\"sql\" name=\"sql\" style=\"width: 600px; height: 100px;\">")
    if sql_text:
        cgicommon.write(cgicommon.escape(sql_text))
    cgicommon.writeln("</textarea>")
    cgicommon.writeln("</div>")
    cgicommon.writeln("<div class=\"sqlentrysubmit\">")
    #cgicommon.writeln("<input type=\"text\" name=\"sql\" />")
    cgicommon.writeln("<input type=\"hidden\" name=\"tourney\" value=\"%s\" />" % (cgicommon.escape(tourney_name)))
    cgicommon.writeln("<input type=\"hidden\" name=\"execute\" value=\"1\" />")
    cgicommon.writeln("<input type=\"hidden\" name=\"nowarning\" value=\"1\" />")

    cgicommon.writeln("<input class=\"bigbutton\" type=\"submit\" name=\"submitsql\" value=\"Run SQL (Ctrl-Enter)\" />")
    cgicommon.writeln("</div>")
    cgicommon.writeln("</form>")
    cgicommon.writeln("</div>")

    cgicommon.writeln("<div class=\"sqlresults\">")

    if execute_sql:
        if num_result_cols == 0:
            result_count_text = ""
        else:
            result_count_text = " (%d row%s)" % (len(result_rows), "" if len(result_rows) == 1 else "s")

        cgicommon.writeln("<h2>Results%s</h2>" % (result_count_text))

        if error_text:
            cgicommon.show_error_text(error_text_context + ": " + error_text)
        elif num_result_cols > 0:
            cgicommon.writeln("<table class=\"sqlresults\">")
            cgicommon.writeln("<tr>")
            for i in range(num_result_cols):
                cgicommon.writeln("<th>%s</th>" % (cgicommon.escape(result_col_names[i])))
            cgicommon.writeln("</tr>")

            row_num = 0
            for row in result_rows:
                cgicommon.writeln("<tr id=\"row%d\" onmouseover=\"rowHighlight(%d, true);\" onmouseout=\"rowHighlight(%d, false);\">" % (row_num, row_num, row_num))
                for index in range(len(row)):
                    value = row[index]
                    if value is None:
                        value_str = "NULL"
                    else:
                        value_str = value
                    typ = result_col_types[index]
                    cgicommon.writeln("<td%s>%s</td>" % (
                        " class=\"sqlnull\"" if value is None else "",
                        cgicommon.escape(value_str)))
                cgicommon.writeln("</tr>")
                row_num += 1
            cgicommon.writeln("</table>")
        else:
            if num_rows_affected is not None and num_rows_affected >= 0:
                cgicommon.show_success_box("Query successful, %d row%s affected." % (num_rows_affected, "" if num_rows_affected == 1 else "s"))
            else:
                cgicommon.show_success_box("Query successful.")

    cgicommon.writeln("</div>")

cgicommon.writeln("</div>")

cgicommon.writeln("</body></html>")

sys.exit(0)
