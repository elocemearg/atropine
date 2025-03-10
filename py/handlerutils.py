#!/usr/bin/python3

import json
import httpresponse
import htmltraceback

# http_response is an HTTPResponse object, defined in httpresponse.py
def send_response(http_handler, http_response, charset="utf-8", cache_max_sec=0):
    status_code = http_response.get_status_code()
    http_handler.send_response(status_code)
    if http_response.is_binary():
        http_handler.send_header("Content-Type", http_response.get_content_type())
        response_binary = http_response.get_bytes()
    else:
        http_handler.send_header("Content-Type", http_response.get_content_type() + ("" if charset is None else ("; charset=" + charset)))
        response_binary = http_response.get_string().encode(charset)
    http_handler.send_header("Content-Length", str(len(response_binary)))

    if cache_max_sec <= 0:
        # Do not allow the browser to cache this response, because it's
        # dynamic content - for example, scores and standings may change at any
        # time. When a script on the page requests this information, the
        # browser must actually fetch it and not just use the old copy.
        http_handler.send_header("Cache-Control", "no-cache")
    else:
        # The browser may cache this response for up to cache_max_sec seconds.
        http_handler.send_header("Cache-Control", "max-age=%d" % (cache_max_sec))

    for (name, value) in http_response.get_header_pairs():
        http_handler.send_header(name, value)
    http_handler.end_headers()
    http_handler.wfile.write(response_binary)

def make_error_response(error_text):
    return {
        "success" : False,
        "description" : error_text
    }

def send_error_response(http_handler, error_text, status_code=400):
    response = httpresponse.HTTPResponse()
    response.set_content_type("application/json; charset=utf-8")
    response.write(json.dumps(make_error_response(error_text), indent=4))
    response.set_status_code(status_code)
    send_response(http_handler, response)

def send_html_error_response(http_handler, error_text, status_code=400):
    response = httpresponse.HTTPResponse()
    response.write("""<html>
<head><title>Atropine: error</title></head>
<body>
<p>%s</p>
</body>
</html>""" % (error_text))
    response.set_status_code(status_code)
    send_response(http_handler, response)

def send_exception_response(http_handler, exc, status_code=500):
    response = httpresponse.HTTPResponse()
    htmltraceback.write_html_exception_page(http_handler, response, exc)
    response.set_status_code(status_code)
    send_response(http_handler, response)
