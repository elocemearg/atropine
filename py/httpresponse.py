#!/usr/bin/python3

from io import StringIO, BytesIO

class HTTPResponse(object):
    """
    Object passed to former CGI scripts under cgi-bin/webroot, which are now
    modules with a handle() function. The handle() function calls write() and
    writeln() to build up a (usually HTML) response to the request.

    Data supplied with write() or writeln() is expected to be text. If you
    want to return binary data, call writebinary(), set an appropriate
    content type, and do not call write() or writeln().

    When the handle() function returns, the main AtropineHTTPRequestHandler
    calls get_string() on it and sends the resulting string as the response
    body back to the client.

    The content type we send to the client is "text/html; charset=utf-8"
    unless the handle() function overrides it with set_content_type().
    """

    def __init__(self):
        self.response_data = StringIO()
        self.response_data_binary = None
        self.content_type = "text/html; charset=utf-8"
        self.headers = {}
        self.status_code = 200

    def writeln(self, s=""):
        self.response_data.write(s)
        self.response_data.write("\n")

    def write(self, s):
        self.response_data.write(s)

    def writebinary(self, b):
        if self.response_data_binary is None:
            self.response_data_binary = BytesIO()
        self.response_data_binary.write(b)

    def get_string(self):
        return self.response_data.getvalue()

    def get_bytes(self):
        return self.response_data_binary.getvalue()

    def is_binary(self):
        return self.response_data_binary is not None

    def set_content_type(self, content_type):
        self.content_type = content_type

    def get_content_type(self):
        return self.content_type

    def add_header(self, name, value):
        self.headers[name.lower()] = value

    def get_header_pairs(self):
        return [ (name, self.headers[name]) for name in self.headers ]

    def set_status_code(self, status_code):
        self.status_code = status_code

    def get_status_code(self):
        return self.status_code

