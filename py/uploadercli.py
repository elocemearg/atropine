#!/usr/bin/python3

import sys
import socket
import json

uploader_service_port = 3961

class UploaderClientException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

def read_line_from_socket(sock):
    byte_array = b''
    b = b'a'
    while b != b'\n' and b != b'':
        b = sock.recv(1)
        if b is not None and len(b) > 0:
            byte_array += b
    return byte_array.decode("utf-8")

def send_request(request_type, request_body):
    try:
        sock = socket.create_connection(("127.0.0.1", uploader_service_port), 10)

        req = {
                "type" : request_type,
                "request" : request_body
        }

        json_str = json.dumps(req) + "\n"
        sock.sendall(json_str.encode("utf-8"))
        json_str = read_line_from_socket(sock)
        sock.close()

        rep = json.loads(json_str)
    except OSError as e:
        raise UploaderClientException("Failed to send request to local uploader service: " + str(e))

    if not rep.get("success", False):
        raise UploaderClientException(rep.get("message", "No message"))
    return rep

def start_uploading(tourney_name, username, password):
    return send_request("start_uploading", {
        "tourney": tourney_name,
        "username" : username,
        "password" : password
    })

def stop_uploading(tourney_name):
    return send_request("stop_uploading", {
        "tourney": tourney_name
    })

def get_tourney_upload_state(tourney_name):
    return send_request("status", {
        "tourney" : tourney_name
    })

def delete_tourney_from_web(tourney_name, username, password):
    return send_request("delete", {
        "tourney": tourney_name,
        "username" : username,
        "password" : password
    })
