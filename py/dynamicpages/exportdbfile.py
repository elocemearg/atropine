#!/usr/bin/python3

import os
from urllib.parse import unquote
import htmlcommon
from countdowntourney import get_tourney_filename, DBNameDoesNotExistException

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    # No parameters expected - we just return the database file as a download.
    # tourney is None.

    # Fish the tourney name out of the path
    components = [ unquote(x) for x in httpreq.path.split("/") if x ]
    tourney_name = components[1]

    # get_tourney_filename() throws an InvalidDBNameException if tourney_name
    # contains disallowed characters, but doesn't check whether the file exists.
    tourney_file_path = get_tourney_filename(tourney_name)

    # If the file doesn't exist, raise a DBNameDoesNotExistException, which
    # will cause atropinehttprequesthandler to return a 404 response.
    if not os.path.exists(tourney_file_path):
        raise DBNameDoesNotExistException()

    response.set_content_type("application/x-sqlite3")
    response.add_header("Content-Disposition", "attachment; filename=\"%s.db\"" % (htmlcommon.escape(tourney_name)))

    with open(tourney_file_path, "rb") as f:
        data = f.read()
        response.writebinary(data)

