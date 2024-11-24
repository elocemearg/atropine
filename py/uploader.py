#!/usr/bin/python3

# The uploader service runs in a separate thread, and there is only one of it
# in the Python process. Entrypoint is uploader_request(), which is passed
# { "type" : ..., "request" : ... } objects.
# These used to be encoded as JSON and sent to port 3961 on which this
# module would be listening, but that was only required when we had CGI
# scripts which ran in separate Python processes.

# Callers to uploader_request() can tell us to:
#   * Add a tourney to the list of tourneys we're periodically uploading to
#     greem.co.uk
#   * Remove a tourney from that list (i.e. stop uploading it)
#   * Delete a tourney from greem.co.uk
#   * Get the upload state of a tourney (are we uploading it, when was the
#     last successful upload, was the last upload successful, and if not, what
#     went wrong)
#
# The service is started with atropine.py, and runs alongside the web server
# which serves the web interface used by the tournament administrator. At
# startup, no tourneys are being uploaded.

import sys
import json
import threading
import time
import http.client
import traceback

http_server_host = "greem.co.uk"
http_server_port = None
http_submit_path = "/cgi-bin/colive/submit.py"
http_delete_path = "/cgi-bin/colive/submit.py"

upload_interval_sec = 10

import tourney2json
import countdowntourney

uploader_thread = None

class FieldNotFoundException(Exception):
    pass

def make_error_response(message):
    return { "success" : False, "message" : message }

def make_ok_response():
    return { "success" : True }

def get_game_state(tourney):
    return tourney2json.get_state_for_upload(tourney)

def get_tourney_unique_id(tourney):
    return tourney.get_unique_id()

def delete_tourney_from_web(tourney_name, username, password):
    req = {
            "username" : username,
            "password" : password,
            "tourney" : tourney_name,
            "delete" : True
    }
    return make_https_json_request(http_server_host, http_server_port, http_delete_path, req)

def make_https_json_request(server_host, server_port, path, request):
    post_data = json.dumps(request)
    httpcon = None
    try:
        httpcon = http.client.HTTPSConnection(host=server_host, port=server_port, timeout=30)
        httpcon.connect()
    except Exception as e:
        if httpcon:
            httpcon.close()
        sys.stderr.write("Failed to connect to %s: %s\r\n" % (server_host, str(e)))
        return { "success" : False, "http_failure" : True, "message" : "Failed to connect to %s: %s. Check your internet connection." % (server_host, str(e)) }

    try:
        while path and path[0] == '/':
            path = path[1:]
        url = "https://%s%s/%s" % (server_host, (":" + str(server_port)) if server_port else "", path)
        httpcon.request("POST", url, post_data)
    except ConnectionError as e:
        httpcon.close()
        sys.stderr.write("Failed to send HTTP request to %s: %s\r\n" % (url, str(e)))
        return {
                "success" : False,
                "http_failure" : True,
                "message" : "Failed to upload game state to server %s: %s. Check your internet connection." % (url, str(e))
        }
    except Exception as e:
        httpcon.close()
        sys.stderr.write("Failed to send HTTP request to %s: %s\r\n" % (url, str(e)))
        return { "success" : False, "http_failure" : True, "message" : str(e) }

    try:
        response = httpcon.getresponse()
    except Exception as e:
        sys.stderr.write("Failed to read response from %s: %s\r\n" % (url, str(e)))
        httpcon.close()
        return { "success" : False, "http_failure" : True, "message" : str(e) }

    if response.status != 200:
        sys.stderr.write("Failed to post data to %s: HTTP response %d: %s\r\n" % (url, response.status, response.reason))
        rep = {
                "success" : False,
                "http_failure" : True,
                "message" : "Failed to post update to server: HTTP %d: %s" % (response.status, response.reason)
        }
    else:
        response_body = None
        rep = None
        try:
            response_body = response.read()
        except Exception as e:
            sys.stderr.write("Failed to read response data from HTTP: " + str(e) + "\r\n")
            rep = {
                    "success" : False,
                    "http_failure" : True,
                    "message" : str(e)
            }
        if response_body is not None:
            try:
                rep = json.loads(response_body.decode("utf-8"))
                if not rep.get("success", False):
                    message = rep.get("message", "(none)")
                    sys.stderr.write("Update failed. Message: " + message + "\r\n")
            except Exception as e:
                sys.stderr.write("Failed to parse server response: " + str(e) + "\r\n")
                rep = {
                        "success" : False,
                        "message" : "Server response was invalid JSON: " + str(e)
                }
    httpcon.close()
    return rep


class UploaderThread(object):
    def __init__(self):
        self.uploading_tourneys = set()
        self.tourney_upload_start_time = {}
        self.tourney_last_upload_attempt_time = {}
        self.tourney_last_uploaded_game_state = {}
        self.tourney_num_viewers = {}
        self.tourney_auth = {}
        self.thread = threading.Thread(target=self.body)
        self.thread.daemon = True
        self.thread.start()

    def is_uploading_tourney(self, tourney):
        return (tourney in self.uploading_tourneys)

    def add_tourney_to_upload_list(self, tourney, username, password, private):
        self.uploading_tourneys.add(tourney)
        self.tourney_auth[tourney] = { "username" : username, "password" : password, "private" : private }
        self.tourney_upload_start_time[tourney] = int(time.time());
        if tourney in self.tourney_last_uploaded_game_state:
            del self.tourney_last_uploaded_game_state[tourney]
        self.tourney_last_upload_attempt_time[tourney] = 0

    def remove_tourney_from_upload_list(self, tourney):
        self.uploading_tourneys.discard(tourney)

    def get_last_successful_upload_time(self, tourney_name):
        try:
            with countdowntourney.tourney_open(tourney_name) as tourney:
                upload_time = tourney.get_last_successful_upload_time()

                # Don't return this time if it's before the user even pressed
                # the "start uploading" button"
                if upload_time is None or upload_time < self.tourney_upload_start_time.get(tourney_name, 0):
                    return None
                else:
                    return upload_time
        except countdowntourney.TourneyException as e:
            sys.stderr.write("Failed to get last successful upload time: %s\n" % (str(e)))
            return None

    def get_last_failed_upload(self, tourney_name):
        try:
            with countdowntourney.tourney_open(tourney_name) as tourney:
                failed_upload = tourney.get_last_failed_upload()
                if failed_upload is not None and failed_upload.get("ts", None) is not None and failed_upload["ts"] >= self.tourney_upload_start_time.get(tourney_name, 0):
                    return failed_upload
                else:
                    return None
        except countdowntourney.TourneyException as e:
            sys.stderr.write("Failed to get last failed upload info: %s\n" % (str(e)))
            return None

    def get_num_viewers(self, tourney_name):
        return self.tourney_num_viewers.get(tourney_name, None)

    def get_tourney_auth(self, tourney):
        return self.tourney_auth.get(tourney)

    def set_tourney_auth(self, tourney, username, password):
        self.tourney_auth[tourney] = { "username" : username, "password" : password }

    def get_upload_button_pressed_time(self, tourney):
        if tourney not in self.uploading_tourneys:
            return None
        else:
            return self.tourney_upload_start_time.get(tourney, None)

    def write_log(self, message):
        sys.stderr.write("%s: %s\r\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), message))

    def body(self):
        while True:
            uploading_tourneys = self.uploading_tourneys.copy()
            for tourney_name in uploading_tourneys:
                now = time.time()
                last_upload_time = self.tourney_last_upload_attempt_time.get(tourney_name, 0)
                if now >= last_upload_time + upload_interval_sec:
                    # Upload this tourney to the web if it's been at least
                    # upload_interval_sec seconds since the previous upload
                    # attempt.
                    try:
                        self.tourney_last_upload_attempt_time[tourney_name] = now
                        with countdowntourney.tourney_open(tourney_name) as tourney:
                            game_state = get_game_state(tourney)
                            tourney_unique_id = get_tourney_unique_id(tourney)
                            auth = self.tourney_auth.get(tourney_name, None)
                            if auth:
                                username = auth.get("username")
                                password = auth.get("password")
                                private = auth.get("private", False)
                            else:
                                username = None
                                password = None
                                private = False
                            req = {
                                    "username" : username,
                                    "password" : password,
                                    "private" : private,
                                    "unique_id" : tourney_unique_id,
                                    "tourney" : tourney_name
                            }

                            # If the game state has changed since the last time
                            # we did a successful upload, include the new game
                            # state, otherwise we just submit a null update
                            # which only checks the server still works and
                            # reads how many current visitors there are.
                            if tourney_name not in self.tourney_last_uploaded_game_state or game_state != self.tourney_last_uploaded_game_state[tourney_name]:
                                req["state"] = game_state

                            # Send the submission to the server & get the reply
                            rep = make_https_json_request(http_server_host, http_server_port, http_submit_path, req)
                            num_viewers = None
                            if rep.get("success", False):
                                self.tourney_last_uploaded_game_state[tourney_name] = game_state
                                tourney.log_successful_upload()
                                if "state" in req:
                                    self.write_log("Successfully uploaded state for tourney \"%s\"" % (tourney_name))
                                else:
                                    self.write_log("No change since last upload of tourney \"%s\"" % (tourney_name))
                                num_viewers = rep.get("viewers", None)
                                if num_viewers is not None:
                                    self.write_log("Server reports %d viewer%s." % (num_viewers, "s" if num_viewers != 1 else ""))
                            else:
                                if rep.get("http_failure", False):
                                    failure_type = countdowntourney.UPLOAD_FAIL_TYPE_HTTP
                                else:
                                    failure_type = countdowntourney.UPLOAD_FAIL_TYPE_REJECTED
                                tourney.log_failed_upload(failure_type, rep.get("message", "(no message)"))
                                self.write_log("Failed to upload state for tourney \"%s\": %s" % (tourney_name, rep.get("message", "(no message")))
                            self.tourney_num_viewers[tourney_name] = num_viewers
                    except countdowntourney.TourneyException as e:
                        self.write_log("UploaderThread: couldn't open tourney %s: %s" % (tourney_name, str(e)))
                        traceback.print_tb(e.__traceback__)
                        continue
                    except Exception as e:
                        self.write_log("Uploader thread threw exception: %s" % (str(e)))
                        traceback.print_tb(e.__traceback__)
                        continue
            time.sleep(1)

def get_fields_from_req(req, field_names):
    field_values = []
    for name in field_names:
        value = req.get(name, None)
        if value is None:
            raise FieldNotFoundException()
        field_values.append(value)
    return tuple(field_values)

def uploader_request(req):
    global uploader_thread

    if not uploader_thread:
        return make_error_response("Uploader thread not running")

    req_type = req.get("type", None)
    if not req_type:
        return make_error_response("Request has no request type")
    req_body = req.get("request", None)
    if req_body is None:
        return make_error_response("Request has no body")

    try:
        if req_type == "start_uploading":
            (tourney, username, password, private) = get_fields_from_req(req_body, ["tourney", "username", "password", "private"])
            uploader_thread.add_tourney_to_upload_list(tourney, username, password, private)
            rep = make_ok_response()
        elif req_type == "stop_uploading":
            (tourney,) = get_fields_from_req(req_body, ["tourney"])
            uploader_thread.remove_tourney_from_upload_list(tourney)
            rep = make_ok_response()
        elif req_type == "delete":
            (tourney, username, password) = get_fields_from_req(req_body, ["tourney", "username", "password"])
            uploader_thread.remove_tourney_from_upload_list(tourney)
            rep = delete_tourney_from_web(tourney, username, password)
            uploader_thread.set_tourney_auth(tourney, username, password)
        elif req_type == "status":
            (tourney,) = get_fields_from_req(req_body, ["tourney"])
            rep = { "success" : True }
            auth = uploader_thread.get_tourney_auth(tourney)
            rep["publishing"] = uploader_thread.is_uploading_tourney(tourney)
            rep["viewers"] = uploader_thread.get_num_viewers(tourney)
            if auth:
                rep["username"] = auth.get("username", None)
                rep["password"] = auth.get("password", None)
                rep["private"] = auth.get("private", False)
            rep["last_successful_upload_time"] = uploader_thread.get_last_successful_upload_time(tourney)
            rep["last_failed_upload"] = uploader_thread.get_last_failed_upload(tourney)
            rep["upload_button_pressed_time"] = uploader_thread.get_upload_button_pressed_time(tourney)
            rep["now"] = int(time.time())
        else:
            rep = make_error_response("Unrecognised request type")
    except FieldNotFoundException:
        return make_error_response("Request is not valid for type")
    return rep

def start_uploader_thread():
    global uploader_thread
    if not uploader_thread:
        uploader_thread = UploaderThread()
