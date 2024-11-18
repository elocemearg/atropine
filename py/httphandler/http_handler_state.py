#!/usr/bin/python3

"""
Handler for service/<tourneyname>/state/...

Replaces the old CGI script cgi-bin/jsonreq.py. Fetches tourney state as a
JSON object. Only GET is supported.
"""

from urllib.parse import parse_qsl

import handlerutils
import countdowntourney
import tourney2json
import json

def handle(handler, tourney, remaining_path_components, query_string):
    query_string_key_value = parse_qsl(query_string, encoding="utf-8", errors="replace")
    options = {}
    for (key, value) in query_string_key_value:
        options[key] = value
    if not remaining_path_components or not remaining_path_components[0]:
        request = "default"
    else:
        request = remaining_path_components[0]

    status_code = 200
    if request not in tourney2json.valid_requests:
        reply_object = handlerutils.make_error_response("Bad request: request type \"%s\" is not recognised." % (request))
        status_code = 400
    else:
        try:
            reply_object = tourney2json.valid_requests[request](tourney, options)
        except countdowntourney.TourneyException as e:
            reply_object = handlerutils.make_error_response(e.description)
            status_code = 500
        except Exception as e:
            reply_object = handlerutils.make_error_response("tourney2json handler threw exception: " + str(e))
            status_code = 500

    handlerutils.send_response(handler, "application/json", json.dumps(reply_object), status_code=status_code)
