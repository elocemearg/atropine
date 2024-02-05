import sys
import os
from urllib.parse import parse_qsl

class CGIException(Exception):
    def __init__(self, description):
        self.description = description

PARAM_STATE_NAME = 0
PARAM_STATE_VALUE_OR_QUOTE = 1
PARAM_STATE_QUOTED_STRING = 2
PARAM_STATE_STRING = 3
PARAM_STATE_AFTER_QUOTED_STRING = 4
# Format is: name=value; name=value; ...
# name is a token, value is either a token or a quoted string.
def cgi_parse_params(s):
    params = {}
    name = []
    value = []
    state = 0
    s = s + "\0"
    for c in s:
        if state == PARAM_STATE_NAME:
            # name
            if c == '=':
                # value follows
                state = PARAM_STATE_VALUE_OR_QUOTE
            elif c == ';' or c == '\0':
                # new parameter follows
                state = PARAM_STATE_NAME
                params["".join(name).strip()] = ""
                name = []
                value = []
            else:
                name.append(c)
        elif state == PARAM_STATE_VALUE_OR_QUOTE:
            # value or quote character
            if c == '\"':
                # quoted string value
                state = PARAM_STATE_QUOTED_STRING
            elif c == ';' or c == '\0':
                # Blank value
                params["".join(name).strip()] = ""
                name = []
                value = []
                state = PARAM_STATE_NAME
            elif not c.isspace():
                # unquoted string value
                state = PARAM_STATE_STRING
                value.append(c)
        elif state == PARAM_STATE_QUOTED_STRING:
            # quoted string value
            if c == '\"' or c == '\0':
                # after the end of the value, expect semicolon next
                state = PARAM_STATE_AFTER_QUOTED_STRING
                params["".join(name).strip()] = "".join(value)
                name = []
                value = []
            elif c != '\0':
                value.append(c)
        elif state == PARAM_STATE_STRING:
            # Unquoted value - read until we see a semicolon or end
            if c == ';' or c == '\0':
                state = PARAM_STATE_NAME
                params["".join(name).strip()] = "".join(value).strip()
                name = []
                value = []
            else:
                value.append(c)
        elif state == PARAM_STATE_AFTER_QUOTED_STRING:
            # Ignore characters until the next semicolon
            if c == ';':
                state = PARAM_STATE_NAME
    if "" in params:
        del params[""]
    return params


# FieldStorage class to replace the one from the Python cgi module which is
# being removed in 3.11.
# We don't implement everything that cgi.FieldStorage implemented, only the
# functionality Atropine actually uses. In particular, this doesn't support
# file upload by a POST or PUT with content-type "multipart/form-data",
# because Atropine doesn't use that anywhere.
class FieldStorage(object):
    def __init__(self, encoding="utf-8", errors="replace", environment=None, input_buffer=None):
        if environment is None:
            environment = os.environ
        if input_buffer is None:
            input_buffer = sys.stdin.buffer
        self.request_method = environment.get("REQUEST_METHOD")
        self.query_string = environment.get("QUERY_STRING", "")
        self.parameters = {}
        self.content_length = None
        self.content_type = None
        if self.query_string:
            for (name, value) in parse_qsl(self.query_string, encoding=encoding, errors=errors):
                if name not in self.parameters:
                    self.parameters[name] = value

        if self.request_method == "POST":
            # If the content-type is not specified, assume it's
            # application/x-www-form-urlencoded, which happens to be the only
            # only thing we know how to deal with.
            self.content_type = environment.get("CONTENT_TYPE", None)
            if not self.content_type:
                self.content_type = "application/x-www-form-urlencoded; charset=utf-8"
            semi_colon_pos = self.content_type.find(";")
            self.content_type_params = {}
            if semi_colon_pos >= 0:
                self.content_type_params = cgi_parse_params(self.content_type[(semi_colon_pos + 1):])
                self.content_type = self.content_type[0:semi_colon_pos]

            if "charset" in self.content_type_params:
                character_encoding = self.content_type_params["charset"]
            else:
                character_encoding = encoding

            if self.content_type != "application/x-www-form-urlencoded":
                raise CGIException("CONTENT_TYPE is %s: the only supported content type for POST requests is application/x-www-form-urlencoded.")

            # CONTENT_LENGTH: number of bytes to read from stdin.
            self.content_length = environment.get("CONTENT_LENGTH", "0")
            try:
                self.content_length = int(self.content_length)
            except ValueError:
                raise CGIException("CONTENT_LENGTH environment variable is not a number: " + self.content_length)

            # The urlencoded postdata should be valid UTF-8, because it should
            # be valid ASCII. We'll use the character encoding above to
            # determine how to interpret the byte sequences once they're
            # decoded.
            if self.content_length > 0:
                post_data = input_buffer.read(self.content_length).decode("utf-8")
            else:
                post_data = ""
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

