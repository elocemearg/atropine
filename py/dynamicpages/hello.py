#!/usr/bin/python3

def handle(httpreq, response, tourney, request_method, form, query_string, extra_components):
    response.set_content_type("text/plain; charset=utf-8")
    response.writeln("Hello, world!");
    response.writeln("Tourney is %s" % tourney.get_name());
