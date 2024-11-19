#!/usr/bin/python3

import os
from urllib.parse import unquote
import htmlcommon

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    # No parameters expected - we just return the database file as a download.
    # tourney is None.

    # Fish the tourney name out of the path
    components = [ unquote(x) for x in httpreq.path.split("/") if x ]
    tourney_name = components[1]

    response.set_content_type("application/x-sqlite3")
    response.add_header("Content-Disposition", "attachment; filename=\"%s.db\"" % (htmlcommon.escape(tourney_name)))

    tourney_file_path = os.path.join(htmlcommon.dbdir, tourney_name + ".db")
    with open(tourney_file_path, "rb") as f:
        data = f.read()
        response.writebinary(data)

