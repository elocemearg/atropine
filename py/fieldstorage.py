import sys
import os
from urllib.parse import parse_qsl
from email.message import EmailMessage

class CGIException(Exception):
    def __init__(self, description):
        self.description = description


# FieldStorage class to replace the one from the Python cgi module which is
# being removed in 3.11.
# We don't implement everything that cgi.FieldStorage implemented, only the
# functionality Atropine actually uses. In particular, this doesn't support
# file upload by a POST or PUT with content-type "multipart/form-data",
# because Atropine doesn't use that anywhere.
# This class no longer uses the environment, because we don't have any real
# CGI scripts in Atropine any more. Instead, an HTTP request handler already
# knows the request content-type, request method, query string and POST data,
# and it supplies them all as arguments to the constructor.
class FieldStorage(object):
    def __init__(self, content_type=None, request_method=None, query_string=None, post_data=None, encoding="utf-8", errors="replace"):
        self.request_method = request_method
        self.query_string = query_string
        if content_type:
            self.content_type = content_type
        else:
            self.content_type = "application/x-www-form-urlencoded; charset=" + encoding
        self.parameters = {}
        if self.query_string:
            for (name, value) in parse_qsl(self.query_string, encoding=encoding, errors=errors):
                if name not in self.parameters:
                    self.parameters[name] = value

        if self.request_method == "POST":
            # Use the EmailMessage code to parse the CONTENT_TYPE value and any arguments
            msg = EmailMessage()
            msg["content-type"] = self.content_type
            self.content_type = msg.get_content_type()
            self.content_type_params = msg["content-type"].params
            if "charset" in self.content_type_params:
                character_encoding = self.content_type_params["charset"]
            else:
                character_encoding = encoding

            if self.content_type != "application/x-www-form-urlencoded":
                raise CGIException("Content-Type is %s: the only supported content type for POST requests is application/x-www-form-urlencoded.")

            if post_data is None:
                # The urlencoded postdata should be valid UTF-8, because it
                # should be valid ASCII. We'll use the character encoding above
                # to determine how to interpret the byte sequences once they're
                # decoded.
                if self.content_length > 0:
                    post_data = input_buffer.read(self.content_length).decode("utf-8")
                else:
                    post_data = ""
            else:
                post_data = post_data.decode("utf-8")
            #sys.stderr.write("POST DATA: " + post_data + "\n")
            for (name, value) in parse_qsl(post_data, encoding=character_encoding, errors=errors):
                if name not in self.parameters:
                    self.parameters[name] = value

    # There is no support for the same name appearing twice in the query
    # string with two different values. If this happens, you only get the
    # first value.
    def getfirst(self, name, default_value=None):
        return self.parameters.get(name, default_value)

    def __contains__(self, name):
        return name in self.parameters

    def __iter__(self):
        return iter(self.parameters)

    def __len__(self):
        return len(self.parameters)

    def keys(self):
        return self.parameters.keys()

