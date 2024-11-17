#!/usr/bin/python3

import sys
import os
import io

sys.path.append("py")

import fieldstorage

field_storage_tests = [
    # REQUEST_METHOD, QUERY_STRING, post data, CONTENT_LENGTH, CONTENT_TYPE, expected name-value relationship
    # If content type is None, use "application/x-www-form-urlencoded".
    # If content length is None, we default to the postdata's byte length.
    ( "GET", "a=1&b=2&c=3", "", None, None,
        { "a" : "1", "b" : "2", "c" : "3" } ),
    ( "GET", "", "", None, None, {} ),
    ( "POST", "", "", None, None, {} ),
    ( "GET", "alpha=bravo&charlie=delta&charlie=echo", "", None, None,
        { "alpha" : "bravo", "charlie" : "delta" } ),
    ( "POST", "foo=bar&eurosymbol=%E2%82%AC", "u%5Fwith%5Fumlaut=%C3%BC", None, None,
        { "foo" : "bar", "eurosymbol" : "€", "u_with_umlaut" : "ü" } ),
    ( "POST", "tourney=colin&selectedview=0", "somedata=alpha%2Cbravo%0Acharlie%2Cdelta%0Aecho%2Cfoxtrot%0A&amp=%26&equals=%3D", None, None,
        { "tourney" : "colin", "selectedview" : "0", "somedata" : "alpha,bravo\ncharlie,delta\necho,foxtrot\n", "amp" : "&", "equals" : "=" } ),

    # Everything after the first CONTENT_LENGTH (15) bytes of post data should
    # be ignored, so no charlie=3 in the expected result.
    ( "POST", "qs1=a&qs2=b", "alpha=1&bravo=2&charlie=3", "15", None,
        { "qs1" : "a", "qs2" : "b", "alpha" : "1", "bravo" : "2" } ),

    # Post data contains URL-encoded latin-1 character sequences, which are
    # not valid UTF-8 on their own. Make sure that if we set charset=latin1 in
    # the content-type, the strings are decoded correctly.
    ( "POST", "", "half=%BD&quarter=%BC&%BE=threequarters", None, "application/x-www-form-urlencoded; charset=latin1",
        { "quarter" : "¼", "half" : "½", "¾" : "threequarters" } ),

    # Content type contains irrelevant arguments that should be ignored.
    # Check that '+' is decoded as space.
    ( "POST", "q=foo&qq=foo+bar", "postdata1=The+quick+brown+fox&postdata2=jumps+over+the+lazy+dog", None, "application/x-www-form-urlencoded; wibble=foo; bibble=wobble; a=1; b=2",
        { "q" : "foo", "qq" : "foo bar", "postdata1" : "The quick brown fox", "postdata2" : "jumps over the lazy dog" } ),

    # Check that URL-encoded strings only get decoded once.
    ( "POST", "a=100%2541&%2525=foobar", "b=100%2541&%2526=baz", None, None,
        { "a" : "100%41", "%25" : "foobar", "b" : "100%41", "%26" : "baz" } ),
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
    form = fieldstorage.FieldStorage(
            content_type=("application/x-www-form-urlencoded" if content_type is None else content_type),
            request_method=request_method, query_string=query_string,
            post_data=(post_data.encode("utf-8") if content_length is None else post_data.encode("utf-8")[:int(content_length)])
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
    sys.exit(1)
else:
    print("FieldStorage: %d tests passed." % (len(field_storage_tests)))
    sys.exit(0)

