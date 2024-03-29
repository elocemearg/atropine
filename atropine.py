#!/usr/bin/python3

import sys
import os
import http.server
import socketserver
import socket
import errno
import argparse
import textwrap

http_listen_port = 3960
uploader_listen_port = 3961
tourneys_path = None

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

def fatal_error(context, exc=None):
    print()
    print("Fatal error. There is more information below.")
    print("Current directory: " + os.getcwd())
    print("Python version: %d.%d.%d" % tuple(sys.version_info[0:3]))
    print()
    for line in textwrap.wrap(context, width=78):
        print(line)
    print()
    if exc:
        print("The following exception was thrown, and its text may help:")
        print(str(exc))
    print()
    print("Press ENTER to exit...")
    input()
    sys.exit(1)

try:
    parser = argparse.ArgumentParser(description="Run Atropine's web server.")
    parser.add_argument("-p", "--port", default=http_listen_port, type=int)
    parser.add_argument("-u", "--uploader-port", default=uploader_listen_port, type=int)
    parser.add_argument("-t", "--tourneys", default=None, type=str)

    args = parser.parse_args()
    http_listen_port = args.port
    uploader_listen_port = args.uploader_port
    tourneys_path = args.tourneys
except Exception as e:
    fatal_error("Error parsing command-line arguments.", e)

try:
    full_exe_path = os.path.abspath(__file__)
    full_exe_path = os.path.realpath(full_exe_path)
except OSError as e:
    fatal_error("Failed to establish full filesystem path to atropine.py.", e)

atropine_home_dir = None
try:
    atropine_home_dir = os.path.dirname(full_exe_path)
    os.chdir(atropine_home_dir)
except Exception as e:
    fatal_error("Failed to chdir to directory: " + str(atropine_home_dir), e)

# Now check whether we at least have the py and webroot directories, and
# check for the presence of certain files in them.
#
# The two failure modes we want to check for are:
# 1. The user has moved atropine.py out of its folder and run it.
# 2. The user has executed atropine.py while it's still in the zip file.
#
# In the case of (1), the py and webroot directories won't be in same place
# as this script. In the case of (2), Windows extracts just this script to a
# new temporary directory and runs it from there. In either case, the py and
# webroot directories won't exist.
#
# There is a third option, which has been seen at least once: the user manages
# to mess up extracting a zip so badly that they somehow extract the empty
# directories py and webroot, but not their contents. So we'll check for files
# that should be in there as well.

for d in [ "py", "webroot" ]:
    path = os.path.join(atropine_home_dir, d)
    if not os.path.exists(path) or not os.path.isdir(path):
        # We're in either case (1) or (2). Doesn't really matter because we
        # aren't going to be able to run anyway, but let's use a little
        # heuristic so that the error message is a bit more helpful...
        if atropine_home_dir.endswith(".zip") or atropine_home_dir.endswith(".zip" + os.path.sep):
            fatal_error("I don't have the " + d + " folder next to me. I " +
                    "think this is because I've been run from inside a zip " +
                    "file. This isn't going to work. " +
                    "You need to extract all contents of the zip file to a " +
                    "new folder first, then run this script from that " +
                    "location.")
        else:
            fatal_error("I'm in " + atropine_home_dir + " but the \"" + d +
                    "\" folder isn't. Where is it? " +
                    "Did you move atropine.py out of the folder containing " +
                    "the \"py\" and \"webroot\" folders? If so, please put it "+
                    "back where you found it and try again.")

# The directories exist, but what about the contents? We won't check every
# file because then we'd have to maintain a manifest of all the files we
# expect, but let's at least check for py/countdowntourney.py and
# webroot/cgi-bin/home.py.
rel_paths = [
        os.path.join("py", "countdowntourney.py"),
        os.path.join("webroot", "cgi-bin", "home.py")
]
for p in rel_paths:
    abs_path = os.path.join(atropine_home_dir, p)
    if not os.path.exists(abs_path):
        fatal_error("Current directory is: " + atropine_home_dir + "\r\n" +
                "Couldn't find file: " + p + "\r\n" +
                "I should be able to see the file " + abs_path +
                " but I can't. Did you extract the entire contents of the zip "+
                "file? (Hint: no.)")

# Add the py and generators directories to Python's path, so we can load
# modules in those directories.
try:
    sys.path.append(os.getcwd())
    sys.path.append(os.path.join(os.getcwd(), "generators"))
    sys.path.append(os.path.join(os.getcwd(), "py"))
except Exception as e:
    fatal_error("Failed to add a necessary directory to Python's list of module paths.", e)

# Set up the path containing the tourney databases.
try:
    if not tourneys_path:
        tourneys_path = os.path.join(os.getcwd(), "tourneys")
    if not os.path.exists(tourneys_path):
        os.mkdir(tourneys_path)
except Exception as e:
    fatal_error("Failed to check or create tourneys folder: " + tourneys_path, e)

# Set environment variables which tell the CGI scripts and everything else
# where to find the fixture generators, the main code (py/) and the tourneys.
try:
    os.environ["GENERATORPATH"] = os.path.join(os.getcwd(), "generators")
    os.environ["CODEPATH"] = os.path.join(os.getcwd(), "py")
    os.environ["TOURNEYSPATH"] = tourneys_path
except Exception as e:
    fatal_error("Failed to set an environment variable GENERATORPATH or CODEPATH. This is... odd.", e)

try:
    import uploader
except Exception as e:
    fatal_error("Failed to import the uploader module. Is there a file uploader..py in the py folder? There should be.", e)

try:
    from countdowntourney import SW_VERSION
except Exception as e:
    fatal_error("Failed to import the countdowntourney module. Is there a file countdowntourney.py in the py folder? There should be.", e)

# Success! If you reach this point then Atropine was installed correctly.

print("*******************************************************************************")
print("* Atropine " + SW_VERSION)
print("* Copyright © 2014-2023 by Graeme Cole.")
print("* Released under the BSD 3-clause licence. See licence.txt.")
print("* Visit https://greem.uk/atropine/ for updates.")
print("* Python version is %d.%d.%d." % tuple(sys.version_info[0:3]))
print("*******************************************************************************")
print()

uploader_service = None

try:
    uploader_service = uploader.TourneyUploaderService(uploader_listen_port)

    os.chdir("webroot");
    server_address = ('', http_listen_port);
    httpd = ThreadedHTTPServer(server_address, http.server.CGIHTTPRequestHandler);
    print("Local web server created. Paste this link into your browser:")
    print()
    print("http://localhost:" + str(http_listen_port) + "/cgi-bin/home.py")
    print()
    httpd.serve_forever();
except socket.error as e:
    err = e.args[0];
    print("Failed to start...")
    if err == errno.EADDRINUSE:
        if uploader_service is None:
            failed_port = uploader_listen_port
        else:
            failed_port = http_listen_port
        print("Address localhost:%d is already in use." % failed_port);
        print();
        print("Perhaps there is another instance of Atropine running?")
        print("If so, close it before attempting to start a new one.")
        print();
    else:
        print(str(e))
    print("Press ENTER to exit...");
    input();
except Exception as e:
    print("Failed to start...")
    print(str(e))
    print("Press ENTER to exit...")
    input()
    sys.exit(1)

sys.exit(0);
