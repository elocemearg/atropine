#!/usr/bin/python3

from io import StringIO

class HTTPResponse(object):
    """
    Object passed to former CGI scripts under cgi-bin/webroot, which are now
    modules with a handle() function. The handle() function calls write() and
    writeln() to build up a (usually HTML) response to the request.

    When the handle() function returns, the main AtropineHTTPRequestHandler
    calls get_string() on it and sends the resulting string as the response
    body back to the client.

    The content type we send to the client is "text/html; charset=utf-8"
    unless the handle() function overrides it with set_content_type().
    """

    def __init__(self):
        self.response_data = StringIO()
        self.content_type = "text/html; charset=utf-8"
        self.headers = {}

    def writeln(self, s=""):
        self.response_data.write(s)
        self.response_data.write("\n")

    def write(self, s):
        self.response_data.write(s)

    def get_string(self):
        return self.response_data.getvalue()

    def set_content_type(self, content_type):
        self.content_type = content_type

    def get_content_type(self):
        return self.content_type

    def add_header(self, name, value):
        self.headers[name.lower()] = value

    def get_header_pairs(self):
        return [ (name, self.headers[name]) for name in self.headers ]

