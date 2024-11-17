#!/usr/bin/python3

import os
import http.server
import socketserver
from urllib.parse import unquote
import httpresponse
import countdowntourney
import handlerutils
import fieldstorage
import htmltraceback

# List of former CGI handlers which do not take a countdowntourney object
CGI_HANDLERS_WITHOUT_TOURNEY = frozenset(["home", "sql", "preferences"])
def cgi_handler_needs_tourney(handler_name):
    return handler_name not in CGI_HANDLERS_WITHOUT_TOURNEY

# List of former CGI handlers which are allowed to be access from clients
# other than localhost
CGI_HANDLERS_PUBLIC = frozenset(["home", "export", "display", "hello"])

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

class AtropineHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    # Modules with a handle() method which want to handle requests to
    # /atropine/<tourneyname>/<handlername> are put in this dictionary.
    # ATROPINE_HANDLER_MODULES[<handlername>] = module
    ATROPINE_HANDLER_MODULES = {}

    # Modules with a handle() method which want to handle requests to
    # /cgi-bin/<somescript>.py are put in this dictionary.
    # ATROPINE_FORMER_CGI_MODULES[<somescript>] = module
    # These are modules which used to be standalone CGI scripts, and are
    # now rewritten not to expect to be called as their own process.
    ATROPINE_FORMER_CGI_MODULES = {}

    """
    All HTTP requests are handled by AtropineHTTPRequestHandler.
    Requests to /atropine/<tourneyname>/<handlername> are passed to the
    appropriate handler module in ATROPINE_HANDLER_MODULES.
    Requests to /cgi-bin/<script>.py are passed to the handler module in

    All other requests
    are handled by the SimpleHTTPRequestHandler, which returns the contents of
    a file.
    """

    def add_handler_module(handler_name, module):
        AtropineHTTPRequestHandler.ATROPINE_HANDLER_MODULES[handler_name] = module

    def add_former_cgi_module(handler_name, module):
        AtropineHTTPRequestHandler.ATROPINE_FORMER_CGI_MODULES[handler_name] = module

    def atropine_handle_request(self, request_method):
        # Split up "path" into its path component and query string
        fields = self.path.split("?", 1)

        if len(fields) > 0:
            path_components = [ unquote(x) for x in fields[0].split("/") if x != "" ]
        else:
            path_components = []
        if len(fields) > 1:
            query_string = fields[1]
        else:
            query_string = ""

        tourneys_path = os.getenv("TOURNEYSPATH")

        # If we have a handler for this path, call it, otherwise let
        # SimpleHTTPRequestHandler handle it.
        if len(path_components) >= 1 and path_components[0] == "atropine":
            if len(path_components) < 3:
                handlerutils.send_error_response(self, "Bad URL: format is /atropine/<tourneyname>/<service>/...", status_code=400)
                return True
            tourney_name = path_components[1]
            handler_name = path_components[2]
            remaining_path_components = path_components[3:]
            if handler_name not in AtropineHTTPRequestHandler.ATROPINE_HANDLER_MODULES:
                # Unknown handler name
                handlerutils.send_error_response(self, "Bad URL: unknown service \"%s\"" % (handler_name), status_code=404)
                return True

            try:
                # Open this tourney DB file.
                with countdowntourney.tourney_open(tourney_name, tourneys_path) as tourney:
                    # If this tourney exists and we opened it, call the
                    # handler's handle() method which will send the response to
                    # the client.
                    try:
                        AtropineHTTPRequestHandler.ATROPINE_HANDLER_MODULES[handler_name].handle(self, tourney, remaining_path_components, query_string)
                    except Exception as e:
                        handlerutils.send_error_response(self, "Failed to execute request handler %s for tourney %s: %s" % (handler_name, tourney_name, str(e)), status_code=400)
            except countdowntourney.DBNameDoesNotExistException as e:
                handlerutils.send_error_response(self, e.description, status_code=404)
            except countdowntourney.TourneyException as e:
                handlerutils.send_error_response(self, "Failed to open tourney \"%s\": %s" % (tourney_name, e.description), status_code=400)
            except Exception as e:
                handlerutils.send_error_response(self, "Failed to open tourney \"%s\": %s" % (tourney_name, str(e)), status_code=400)
            return True
        elif len(path_components) == 2 and path_components[0] == "cgi-bin" and path_components[1].endswith(".py"):
            # It's an old link to what used to be a CGI script.
            # Pass this request to the appropriate module. The tourney name
            # is expected to be part of the query string or POST data.
            handler_name = path_components[1][:-3]
            if handler_name not in AtropineHTTPRequestHandler.ATROPINE_FORMER_CGI_MODULES:
                handlerutils.send_html_error_response(self, "Bad URL: /cgi-bin/%s.py not found" % (handler_name), status_code=404)
                return True

            if handler_name not in CGI_HANDLERS_PUBLIC and not self.is_client_from_localhost():
                # Non-localhost connection to a non-public page
                handlerutils.send_html_error_response(self, "This page is only accessible from the same computer that is running Atropine.", status_code=403)
                return True

            if request_method == "POST":
                # Read this request's POST data
                try:
                    content_length = int(self.headers.get("content-length"))
                except ValueError:
                    handlerutils.send_html_error_response(self, "Bad request: request method is POST but no Content-Length header")
                    return True
                post_data = self.rfile.read(content_length)
            else:
                # No POST data for this request
                post_data = None

            # Create an HTTPResponse for the script to put its response into...
            response = httpresponse.HTTPResponse()

            # Package up the name=value settings from the query string and any
            # POST data into a FieldStorage object.
            field_storage = fieldstorage.FieldStorage(
                    content_type=self.headers.get("content-type"),
                    request_method=request_method, query_string=query_string,
                    post_data=post_data)

            # Most former CGI scripts had a tourney=... parameter - validate
            # that here and open the countdowntourney object, to avoid every
            # individual script having to do it.
            try:
                if not cgi_handler_needs_tourney(handler_name):
                    tourney_name = None
                else:
                    tourney_name = field_storage.getfirst("tourney")
                    if not tourney_name:
                        handlerutils.send_html_error_response(self, "No tourney name specified.", status_code=400)
                        return True

                handler_module = AtropineHTTPRequestHandler.ATROPINE_FORMER_CGI_MODULES[handler_name]
                if tourney_name is None:
                    # This script doesn't have or need a tourney=... parameter
                    try:
                        handler_module.handle(self, response, None, request_method, field_storage, query_string)
                        handlerutils.send_response(self, response.get_content_type(), response.get_string(), other_headers=response.get_header_pairs())
                    except Exception as e:
                        handlerutils.send_html_error_response(self, "Failed to execute request handler %s: %s" % (handler_name, str(e)), status_code=400)
                else:
                    # Open this tourney DB file.
                    with countdowntourney.tourney_open(tourney_name, tourneys_path) as tourney:
                        # If this tourney exists and we opened it, call the
                        # handler's handle() method which will send the
                        # response to the client.
                        try:
                            handler_module.handle(self, response, tourney, request_method, field_storage, query_string)
                            handlerutils.send_response(self, response.get_content_type(), response.get_string(), other_headers=response.get_header_pairs())
                        except Exception as e:
                            htmltraceback.write_html_traceback(response, type(e), e, e.__traceback__)
                            handlerutils.send_response(self, response.get_content_type(), response.get_string(), status_code=500)
            except countdowntourney.DBNameDoesNotExistException as e:
                handlerutils.send_html_error_response(self, e.description, status_code=404)
            except countdowntourney.TourneyException as e:
                htmltraceback.write_html_traceback(response, type(e), e, e.__traceback__)
                handlerutils.send_response(self, response.get_content_type(), response.get_string(), status_code=400)
            except Exception as e:
                htmltraceback.write_html_traceback(response, type(e), e, e.__traceback__)
                handlerutils.send_response(self, response.get_content_type(), response.get_string(), status_code=500)

            # Return true to say we handled this
            return True
        else:
            # Return false to say this needs passing to the appropriate
            # method in SimpleHTTPRequestHandler - it's just a plain fetch of a
            # file from a directory.
            return False

    def do_GET(self):
        if not self.atropine_handle_request("GET"):
            # Just a regular fetch of a file from under webroot
            super().do_GET()

    def do_POST(self):
        if not self.atropine_handle_request("POST"):
            # If we get a POST request and it isn't for a path handled by
            # atropine_handle_request(), then this path doesn't support POST.
            handlerutils.send_html_error_response(self, "This path (%s) does not support POST requests." % (self.path), status_code=405)

    def is_client_from_localhost(self):
        # If the web server is listening only on the loopback interface, then
        # disable this check - instead we'll rely on the fact that we're only
        # listening on that interface.
        if os.environ.get("ATROPINE_LISTEN_ON_LOCALHOST_ONLY", "0") == "1":
            return True

        valid_answers = ["127.0.0.1", "localhost", "::1"]

        remote_addr = self.client_address[0]
        if remote_addr:
            if remote_addr in valid_answers:
                return True
        return False
