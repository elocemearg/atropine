#!/usr/bin/python3

import json

def send_response(http_handler, content_type_value, response_body, status_code=200, charset="utf-8", other_headers=[]):
    http_handler.send_response(status_code)
    http_handler.send_header("Content-Type", content_type_value + ("" if charset is None else ("; charset=" + charset)))
    response_binary = response_body.encode(charset)
    http_handler.send_header("Content-Length", str(len(response_binary)))
    for (name, value) in other_headers:
        http_handler.send_header(name, value)
    http_handler.end_headers()
    http_handler.wfile.write(response_binary)

def make_error_response(error_text):
    return {
        "success" : False,
        "description" : error_text
    }

def send_error_response(http_handler, error_text, status_code=400):
    send_response(http_handler, "application/json; charset=utf-8",
            json.dumps(make_error_response(error_text), indent=4),
            status_code=status_code
    )

