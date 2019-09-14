#!/usr/bin/python3

# The uploader service listens for connections from localhost on port 3961.
# It expects a JSON object on a line by itself as the request. It responds
# with another JSON object on a line by itself, then closes the connection.
# Atropine CGI scripts can send requests to this service to tell it to:
#   * Add a tourney to the list of tourneys we're periodically uploading to
#     greem.co.uk
#   * Remove a tourney from that list (i.e. stop uploading it)
#   * Get the upload state of a tourney (are we uploading it, when was the
#     last successful upload, was the last upload successful, and if not what
#     went wrong)
#
# The service is started with atropine.py, and runs alongside the web server
# which serves the web interface used by the tournament administrator. At
# startup, no tourneys are being uploaded.

import sys
import os
import socketserver
from socketserver import BaseRequestHandler
import json
import threading
import time
import http.client
import traceback

http_server_host = "greem.co.uk"
http_server_port = None
http_submit_path = "/cgi-bin/colive/submit.py"
http_delete_path = "/cgi-bin/colive/submit.py"

db_dir = os.path.join(os.getcwd(), "tourneys")

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

def read_line_from_socket(sock):
    byte_array = b'';
    b = 0
    while b != b'\n':
        b = sock.recv(1)
        if b is None or len(b) == 0:
            return None
        byte_array += b
    return byte_array.decode("utf-8")

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
                "message" : "Failed to upload game state to server %s: %s. Check your internet connection." % (url, str(e)) }
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
        self.tourney_auth = {}
        self.thread = threading.Thread(target=self.body)
        self.thread.daemon = True
        self.thread.start()

    def is_uploading_tourney(self, tourney):
        return (tourney in self.uploading_tourneys)

    def add_tourney_to_upload_list(self, tourney, username, password):
        self.uploading_tourneys.add(tourney)
        self.tourney_auth[tourney] = { "username" : username, "password" : password }
        self.tourney_upload_start_time[tourney] = int(time.time());
        self.tourney_last_upload_attempt_time[tourney] = 0

    def remove_tourney_from_upload_list(self, tourney):
        self.uploading_tourneys.discard(tourney)

    def get_last_successful_upload_time(self, tourney_name):
        try:
            with countdowntourney.tourney_open(tourney_name, db_dir) as tourney:
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
            with countdowntourney.tourney_open(tourney_name, db_dir) as tourney:
                failed_upload = tourney.get_last_failed_upload()
                if failed_upload is not None and failed_upload.get("ts", None) is not None and failed_upload["ts"] >= self.tourney_upload_start_time.get(tourney_name, 0):
                    return failed_upload
                else:
                    return None
        except countdowntourney.TourneyException as e:
            sys.stderr.write("Failed to get last failed upload info: %s\n" % (str(e)))
            return None
    
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
        upload_period_sec = 10
        while True:
            for tourney_name in self.uploading_tourneys:
                now = time.time()
                last_upload_time = self.tourney_last_upload_attempt_time.get(tourney_name, 0)
                if now >= last_upload_time + upload_period_sec:
                    # Upload this tourney to the web if it's been at least
                    # upload_period_sec seconds since the previous upload
                    # attempt.
                    try:
                        self.tourney_last_upload_attempt_time[tourney_name] = now
                        with countdowntourney.tourney_open(tourney_name, db_dir) as tourney:
                            game_state = get_game_state(tourney)
                            tourney_unique_id = get_tourney_unique_id(tourney)
                            auth = self.tourney_auth.get(tourney_name, None)
                            if auth:
                                username = auth.get("username")
                                password = auth.get("password")
                            else:
                                username = None
                                password = None
                            req = {
                                    "username" : username,
                                    "password" : password,
                                    "unique_id" : tourney_unique_id,
                                    "tourney" : tourney_name,
                                    "state" : game_state
                            }

                            rep = make_https_json_request(http_server_host, http_server_port, http_submit_path, req)
                            if rep.get("success", False):
                                tourney.log_successful_upload()
                                self.write_log("Successfully uploaded state for tourney \"%s\"" % (tourney_name))
                            else:
                                if rep.get("http_failure", False):
                                    failure_type = countdowntourney.UPLOAD_FAIL_TYPE_HTTP
                                else:
                                    failure_type = countdowntourney.UPLOAD_FAIL_TYPE_REJECTED
                                tourney.log_failed_upload(failure_type, rep.get("message", "(no message)"))
                                self.write_log("Failed to upload state for tourney \"%s\": %s" % (tourney_name, rep.get("message", "(no message")))
                    except countdowntourney.TourneyException as e:
                        self.write_log("UploaderThread: couldn't open tourney %s: %s" % (tourney_name, str(e)))
                        traceback.print_tb(e.__traceback__)
                        continue
                    except Exception as e:
                        self.write_log("Uploader thread threw exception: %s" % (str(e)))
                        traceback.print_tb(e.__traceback__)
                        continue
            time.sleep(1)

class UploaderServiceHandler(BaseRequestHandler):
    def get_fields_from_req(self, req, field_names):
        field_values = []
        for name in field_names:
            value = req.get(name, None)
            if value is None:
                raise FieldNotFoundException()
            field_values.append(value)
        return tuple(field_values)

    def process_request(self, req):
        global uploader_thread

        req_type = req.get("type", None)
        if not req_type:
            return make_error_response("Request has no request type")
        req_body = req.get("request", None)
        if req_body is None:
            return make_error_response("Request has no body")

        try:
            if req_type == "start_uploading":
                (tourney, username, password) = self.get_fields_from_req(req_body, ["tourney", "username", "password"])
                uploader_thread.add_tourney_to_upload_list(tourney, username, password)
                rep = make_ok_response()
            elif req_type == "stop_uploading":
                (tourney,) = self.get_fields_from_req(req_body, ["tourney"])
                uploader_thread.remove_tourney_from_upload_list(tourney)
                rep = make_ok_response()
            elif req_type == "delete":
                (tourney, username, password) = self.get_fields_from_req(req_body, ["tourney", "username", "password"])
                uploader_thread.remove_tourney_from_upload_list(tourney)
                rep = delete_tourney_from_web(tourney, username, password)
                uploader_thread.set_tourney_auth(tourney, username, password)
            elif req_type == "status":
                (tourney,) = self.get_fields_from_req(req_body, ["tourney"])
                rep = { "success" : True }
                auth = uploader_thread.get_tourney_auth(tourney)
                rep["publishing"] = uploader_thread.is_uploading_tourney(tourney)
                if auth:
                    rep["username"] = auth.get("username", None)
                    rep["password"] = auth.get("password", None)
                rep["last_successful_upload_time"] = uploader_thread.get_last_successful_upload_time(tourney)
                rep["last_failed_upload"] = uploader_thread.get_last_failed_upload(tourney)
                rep["upload_button_pressed_time"] = uploader_thread.get_upload_button_pressed_time(tourney)
                rep["now"] = int(time.time())
            else:
                rep = make_error_response("Unrecognised request type")
        except FieldNotFoundException:
            return make_error_response("Request is not valid for type")

        return rep

    def handle(self):
        # Request is expected to be a JSON object, on a line by itself
        line = read_line_from_socket(self.request)
        if line is not None:
            rep = None
            try:
                req = json.loads(line)
            except Exception as e:
                rep = make_error_response("Request is not valid JSON")

            if not rep:
                rep = self.process_request(req)
            self.request.sendall((json.dumps(rep) + "\n").encode("utf-8"))

        self.request.close()

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, addr_port, service_handler):
        self.allow_reuse_address = True
        super().__init__(addr_port, service_handler)

class TourneyUploaderService(object):
    def __init__(self, listen_port):
        global uploader_thread
        self.listen_port = listen_port
        self.socket_server = ThreadedTCPServer(("127.0.0.1", listen_port), UploaderServiceHandler)
        self.server_thread = threading.Thread(target=self.socket_server.serve_forever)

        if not uploader_thread:
            uploader_thread = UploaderThread()
        self.server_thread.daemon = True
        self.server_thread.start()

    def shutdown(self):
        self.socket_server.shutdown()
