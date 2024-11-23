#!/usr/bin/python3

import os
import http.server
import socketserver
from urllib.parse import unquote
from html import escape
import httpresponse
import countdowntourney
import handlerutils
import fieldstorage

# List of former CGI handlers which do not take a countdowntourney object
WEBPAGE_HANDLERS_WITHOUT_TOURNEY = frozenset(["home", "sql", "preferences", "exportdbfile"])
def webpage_handler_needs_tourney(handler_name):
    return handler_name not in WEBPAGE_HANDLERS_WITHOUT_TOURNEY

# List of former CGI handlers which are allowed to be accessed from clients
# other than localhost
WEBPAGE_HANDLERS_PUBLIC = frozenset(["home", "export", "display", "hello"])

# Put a limit on the size of a request. The biggest requests will be imports
# of tourney .db files, but these are usually around 100K.
# Anyone sending a request bigger than 20MB is probably doing something weird.
MAX_REQUEST_CONTENT_LENGTH = 20 * 1024 * 1024

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

class AtropineHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    # Modules with a handle() method which want to handle requests to
    # /service/<tourneyname>/<handlername> are put in this dictionary.
    # ATROPINE_HANDLER_MODULES[<handlername>] = module
    ATROPINE_HANDLER_MODULES = {}

    # Modules with a handle() method which want to handle requests to
    # /cgi-bin/<somescript>.py are put in this dictionary.
    # ATROPINE_WEBPAGE_MODULES[<somescript>] = module
    # These are modules which used to be standalone CGI scripts, and are
    # now rewritten not to expect to be called as their own process.
    ATROPINE_WEBPAGE_MODULES = {}

    """
    All HTTP requests are handled by AtropineHTTPRequestHandler.
    Requests to /service/<tourneyname>/<handlername> are passed to the
    appropriate handler module in ATROPINE_HANDLER_MODULES.
    Requests to /atropine/<tourney>/<script>
    (formerly /cgi-bin/<script>?tourney=<tourney>) are passed to the handler
    module in py/dynamicpages/.

    All other requests are handled by the SimpleHTTPRequestHandler, which
    returns the contents of a file under the webroot directory.
    """

    def add_handler_module(handler_name, module):
        AtropineHTTPRequestHandler.ATROPINE_HANDLER_MODULES[handler_name] = module

    def add_webpage_module(handler_name, module):
        AtropineHTTPRequestHandler.ATROPINE_WEBPAGE_MODULES[handler_name] = module

    def handle_redirect(self, location):
        response = httpresponse.HTTPResponse()
        response.set_status_code(301)
        response.add_header("Location", location)
        response.writeln("<html><head><title>301 Moved Permanently</title></head><body><p>This page doesn't exist any more. Redirecting to <a href=\"%(url)s\">%(url)s</a>...</p></body></html>" % {
            "url" : escape(location)
        })
        handlerutils.send_response(self, response)

    def handle_service_request(self, request_method, path_components, query_string):
        # If we have a /service handler for this path, call it.
        if len(path_components) < 3:
            handlerutils.send_error_response(self, "Bad URL: format is /service/<tourneyname>/<servicename>/...", status_code=400)
            return
        tourney_name = path_components[1]
        handler_name = path_components[2]
        remaining_path_components = path_components[3:]
        if handler_name not in AtropineHTTPRequestHandler.ATROPINE_HANDLER_MODULES:
            # Unknown handler name
            handlerutils.send_error_response(self, "Bad URL: unknown service \"%s\"" % (handler_name), status_code=404)
            return

        try:
            # Open this tourney DB file.
            with countdowntourney.tourney_open(tourney_name) as tourney:
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

    def handle_page_request(self, request_method, path_components, query_string):
        tourney_name = path_components[1]
        handler_name = path_components[2]
        extra_components = path_components[3:]
        if handler_name not in AtropineHTTPRequestHandler.ATROPINE_WEBPAGE_MODULES:
            handlerutils.send_html_error_response(self, "%s: not found" % (self.path), status_code=404)
            return

        if handler_name not in WEBPAGE_HANDLERS_PUBLIC and not self.is_client_from_localhost():
            # Non-localhost connection to a non-public page
            handlerutils.send_html_error_response(self, "This page is only accessible from the same computer that is running Atropine.", status_code=403)
            return

        if request_method == "POST":
            # Read this request's POST data
            try:
                content_length = int(self.headers.get("content-length"))
                if content_length > MAX_REQUEST_CONTENT_LENGTH:
                    handlerutils.send_html_error_response(self, "Request content too large: more than %d bytes." % (MAX_REQUEST_CONTENT_LENGTH), status_code=413)
                    return
            except ValueError:
                handlerutils.send_html_error_response(self, "Bad request: request method is POST but no Content-Length header", status_code=411)
                return
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
            if webpage_handler_needs_tourney(handler_name):
                if not tourney_name:
                    handlerutils.send_html_error_response(self, "No tourney name specified.", status_code=400)
                    return

            handler_module = AtropineHTTPRequestHandler.ATROPINE_WEBPAGE_MODULES[handler_name]
            if not webpage_handler_needs_tourney(handler_name):
                handler_module.handle(self, response, None, request_method, field_storage, query_string, extra_components)
                handlerutils.send_response(self, response)
            else:
                # Open this tourney DB file.
                with countdowntourney.tourney_open(tourney_name) as tourney:
                    # If this tourney exists and we opened it, call the
                    # handler's handle() method which will send the
                    # response to the client.
                    handler_module.handle(self, response, tourney, request_method, field_storage, query_string, extra_components)
                    handlerutils.send_response(self, response)
        except countdowntourney.DBNameDoesNotExistException as e:
            handlerutils.send_html_error_response(self, e.description, status_code=404)
        except countdowntourney.TourneyException as e:
            # If TourneyException is thrown by a page module, it's a bug
            handlerutils.send_exception_response(self, e, status_code=500)
        except Exception as e:
            # If any other exception is thrown by a page module, it's a bug
            handlerutils.send_exception_response(self, e, status_code=500)

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

        # If the user requests the root then rewrite this to /cgi-bin/home.py
        if len(path_components) == 0 or (len(path_components) == 1 and path_components[0] == ""):
            path_components = [ "atropine", "global", "home" ]

        if len(path_components) == 2 and path_components[0] == "cgi-bin" and path_components[1] == "home.py":
            # Browsers which were previously used with old Atropine will
            # "helpfully" autocomplete http://localhost:3960 to
            # http://localhost:3960/cgi-bin/home.py, so redirect to the
            # correct location.
            self.handle_redirect("/")
        elif len(path_components) >= 1 and path_components[0] == "service":
            # /service/<tourneyname>/<handlername>/...
            # A URL for internal use that probably returns some JSON.
            # Pass the request to the appropriate module in py/httphandler/.
            self.handle_service_request(request_method, path_components, query_string)
        elif len(path_components) >= 3 and path_components[0] == "atropine":
            # /atropine/<tourneyname>/<modulename>/...
            # It's an old link to what used to be a CGI script.
            # Pass this request to the appropriate module in py/dynamicpages/.
            self.handle_page_request(request_method, path_components, query_string)
        else:
            # Return false to say this needs passing to the appropriate
            # method in SimpleHTTPRequestHandler - it's just a plain fetch of a
            # file from a directory.
            return False

        # Return true to say we handled this request.
        return True

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
