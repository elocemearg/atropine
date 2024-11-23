import sys
import os
from urllib.parse import parse_qsl
from email.message import EmailMessage
from email import message_from_bytes, policy

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

        # name -> value
        # except for file uploads in multipart/form-data requests, which are
        # name -> filename
        self.parameters = {}

        # For file uploads, name -> file data (bytes)
        self.file_data = {}

        if self.query_string:
            for (name, value) in parse_qsl(self.query_string, encoding=encoding, errors=errors):
                if name not in self.parameters:
                    self.parameters[name] = value

        if self.request_method == "POST":
            # Use the EmailMessage code to parse the CONTENT_TYPE value and any arguments
            msg = EmailMessage()
            content_type_header_value = self.content_type
            msg["content-type"] = self.content_type
            self.content_type = msg.get_content_type()
            self.content_type_params = msg["content-type"].params
            if "charset" in self.content_type_params:
                character_encoding = self.content_type_params["charset"]
            else:
                character_encoding = encoding

            if self.content_type == "application/x-www-form-urlencoded":
                if post_data is None:
                    # The urlencoded postdata should be valid UTF-8, because it
                    # should be valid ASCII. We'll use the character encoding
                    # above to determine how to interpret the byte sequences
                    # once they're decoded.
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
            elif self.content_type == "multipart/form-data":
                # Parse the request body as a multipart message
                #sys.stderr.write("POST DATA: ")
                #sys.stderr.write(str(post_data))
                header = ("Content-Type: " + content_type_header_value + "\r\n\r\n").encode("utf-8")
                msg = message_from_bytes(header + post_data, policy=policy.HTTP)
                # Walk the tree of parts...
                for part in msg.walk():
                    if not part.is_multipart():
                        # For each part that's not itself a multipart message,
                        # get the field name, and if it's a file upload, get
                        # the filename.
                        if "Content-Disposition" in part:
                            cd = part.get("Content-Disposition").params
                            name = cd.get("name")
                            if name:
                                if "filename" in cd:
                                    # form element name maps to filename
                                    self.parameters[name] = cd["filename"]
                                    # self.file_data[name] maps to file data
                                    self.file_data[name] = part.get_content()
                                else:
                                    # ordinary parameter
                                    self.parameters[name] = part.get_content()
                #sys.stderr.write(str(self.parameters.keys()))
                #sys.stderr.write("\n")
            else:
                raise CGIException("Content-Type is %s: this is not supported by Atropine." % (self.content_type))

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

    def set(self, name, value):
        self.parameters[name] = value

    def get_file_data(self, name):
        return self.file_data.get(name)

