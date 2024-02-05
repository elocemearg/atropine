#!/usr/bin/python3

import sys
import os
import io

sys.path.append(os.path.join("webroot", "cgi-bin"))

import fieldstorage

field_storage_tests = [
    # REQUEST_METHOD, QUERY_STRING, post data, CONTENT_LENGTH, CONTENT_TYPE, expected name-value relationship
    # If content type is None, use "application/x-www-form-urlencoded".
    # If content length is None, we default to the postdata's byte length.
    ( "GET", "a=1&b=2&c=3", "", None, None,
        { "a" : "1", "b" : "2", "c" : "3" } ),
    ( "GET", "", "", None, None, {} ),
    ( "GET", "alpha=bravo&charlie=delta&charlie=echo", "", None, None,
        { "alpha" : "bravo", "charlie" : "delta" } ),
    ( "POST", "foo=bar&eurosymbol=%E2%82%AC", "u%5Fwith%5Fumlaut=%C3%BC", None, None,
        { "foo" : "bar", "eurosymbol" : "€", "u_with_umlaut" : "ü" } ),
    ( "POST", "tourney=colin&selectedview=0", "somedata=alpha%2Cbravo%0Acharlie%2Cdelta%0Aecho%2Cfoxtrot%0A&amp=%26&equals=%3D", None, None,
        { "tourney" : "colin", "selectedview" : "0", "somedata" : "alpha,bravo\ncharlie,delta\necho,foxtrot\n", "amp" : "&", "equals" : "=" } )
]

def compare_dicts(expected_output, observed_output, preamble):
    expected_names = sorted(expected_output)
    observed_names = sorted(observed_output)
    ei = 0
    oi = 0
    failed = False

    # Compare the expected dict with the observed dict
    while ei < len(expected_names) or oi < len(observed_names):
        if ei >= len(expected_names):
            en = None
        else:
            en = expected_names[ei]
        if oi >= len(observed_names):
            on = None
        else:
            on = observed_names[oi]
        if en == on:
            ev = expected_output[en]
            ov = observed_output[on]
            if ev != ov:
                print("%s:\n\tname '%s', expected '%s', observed '%s'" % (preamble, en, ev, ov))
                failed = True
            ei += 1
            oi += 1
        elif on is None or (en is not None and en < on):
            print("%s: expected name '%s', not present in observed output" % (preamble, en))
            ei += 1
            failed = True
        else: # en is None or en > on:
            print("%s: observed name '%s', not present in expected output" % (preamble, on))
            oi += 1
            failed = True
    return failed

test_num = 1
num_failures = 0
for (request_method, query_string, post_data, content_length, content_type, expected_output) in field_storage_tests:
    post_data_buffer = io.BytesIO(post_data.encode("utf-8"))
    form = fieldstorage.FieldStorage(environment={
            "REQUEST_METHOD" : request_method, "QUERY_STRING" : query_string,
            "CONTENT_LENGTH" : (len(post_data) if content_length is None else content_length),
            "CONTENT_TYPE" : ("application/x-www-form-urlencoded" if content_type is None else content_type)
        },
        input_buffer=post_data_buffer
    )
    observed_output = {}
    for key in form:
        observed_output[key] = form.getfirst(key)
        assert(key in form)
    failed = compare_dicts(expected_output, observed_output, "Test %d" % (test_num))
    if failed:
        num_failures += 1
    test_num += 1

if num_failures > 0:
    print("FieldStorage: %d tests failed." % (num_failures))
else:
    print("FieldStorage: %d tests passed." % (len(field_storage_tests)))

