#!/usr/bin/python3

import uploader

class UploaderClientException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

def send_request(request_type, request_body):
    rep = uploader.uploader_request({ "type" : request_type, "request" : request_body })
    if not rep.get("success", False):
        raise UploaderClientException(rep.get("message", "No message"))
    return rep

def start_uploading(tourney_name, username, password, private):
    return send_request("start_uploading", {
        "tourney": tourney_name,
        "username" : username,
        "password" : password,
        "private" : private
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
