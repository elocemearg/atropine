#!/usr/bin/python3

import sys
import htmltraceback
import json
import cgicommon

def send_error_reply(description):
    reply = dict()
    reply["success"] = False
    reply["description"] = description
    json.dump(reply, sys.stdout)

htmltraceback.enable()

cgicommon.writeln("Content-Type: application/json; charset=utf-8")
cgicommon.writeln("")

form = cgicommon.FieldStorage()
tourney_name = form.getfirst("tourney")
request = form.getfirst("request")

cgicommon.set_module_path()

import countdowntourney
import tourney2json

options = dict()
for option_name in form:
    options[option_name] = form.getfirst(option_name)

if tourney_name is None:
    send_error_reply("Bad request: no tourney name specified.")
    sys.exit(0)

if request is None:
    # Information we fetch depends on current mode
    request = "default"

if request not in tourney2json.valid_requests:
    send_error_reply("Bad request: request type \"%s\" is not recognised." % (request))
    sys.exit(0)

try:
    tourney = countdowntourney.tourney_open(tourney_name, cgicommon.dbdir)
    reply_object = tourney2json.valid_requests[request](tourney, options)

except countdowntourney.TourneyException as e:
    send_error_reply(e.description)
    sys.exit(0)

json.dump(reply_object, sys.stdout, indent=4)

sys.exit(0)
