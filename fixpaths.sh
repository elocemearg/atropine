#!/bin/bash

# Interactive script to automate substituting the #!/usr/bin/python3 line at
# the top of most of Atropine's Python scripts for another #! line containing
# wherever the Python 3 interpreter is located on your system.
#
# Thanks to Jack Hurst for testing this.

INTERACTIVE=1
QUIET=0

fail() {
    echo "$1" 1>&2
    if [ $INTERACTIVE -ne 0 ]; then
        read -p "Press ENTER to exit... "
    fi
    exit 1
}

ask_yes_no() {
    prompt="$1"
    read -p "$prompt" answer
    while [ "$answer" != "Y" -a "$answer" != "y" -a "$answer" != "N" -a "$answer" != "n" ]; do
        echo "Please enter Y or N."
        read -p "$prompt" answer
    done
    if [ "$answer" = "Y" -o "$answer" = "y" ]; then
        return 0
    else
        return 1
    fi
}

SCRIPT_BASENAME=$(basename "$0")

while [ -n "$1" ]; do
    if [ "$1" = "-y" ]; then
        INTERACTIVE=0
    elif [ "$1" = "-q" ]; then
        QUIET=1
    elif [ "$1" = "-p" ]; then
        shift
        OVERRIDE_PYTHON3_PATH="$1"
    elif [ "$1" = "-t" ]; then
        shift
        OVERRIDE_ATROPINE_DIR="$1"
    elif [ "$1" = "-h" ]; then
        echo "Interactive script to modify the #! line at the top of the Python scripts"
        echo "found in an Atropine installation so that they point to the correct location"
        echo "of the Python 3 interpreter."
        echo
        echo "Usage: $SCRIPT_BASENAME [-h] [-p /path/to/python3] [-q] [-t /path/to/atropine] [-y]"
        echo "Options:"
        echo "    -h       Show this help."
        echo "    -p path  Specify path to Python 3 interpreter manually rather than"
        echo "             finding it automatically using \"which\"."
        echo "    -q       Quiet. No output unless something goes wrong."
        echo "    -t path  Target installation path. By default we operate on the directory"
        echo "             containing this script."
        echo "    -y       Don't run interactively, automatically say yes to every prompt."
        exit 0
    else
        echo "Unrecognised option: $1" 1>&2
        exit 1
    fi
    shift
done

if [ -z "$OVERRIDE_PYTHON3_PATH" ]; then
    PYTHON3_PATH=$(which python3)
    RESULT=$?
    if [ $RESULT -ne 0 ]; then
        fail "\"which python3\" failed: python3 is not in your PATH. Make sure you have Python 3 installed."
    fi
    if [ ! -f "$PYTHON3_PATH" ]; then
        fail "Python 3 path appears to be $PYTHON3_PATH but this file does not exist."
    fi
else
    PYTHON3_PATH="$OVERRIDE_PYTHON3_PATH"
    if [ ! -e "$PYTHON3_PATH" ]; then
        echo "Warning: $PYTHON3_PATH doesn't exist." 1>&2
        if [ $INTERACTIVE -ne 0 ]; then
            if ask_yes_no "Proceed anyway? [Y/N] "; then
                true
            else
                fail "Cancelled."
            fi
        fi
    fi
fi

if [ -z "$OVERRIDE_ATROPINE_DIR" ]; then
    ATROPINE_DIR=$(dirname "$0")
    if [ ! -d "$ATROPINE_DIR" ]; then
        fail "This script appears to be in $ATROPINE_DIR but that doesn't exist as a directory."
    fi
    if [ ! -e "$ATROPINE_DIR/atropine.py" ]; then
        fail "This script appears to be in $ATROPINE_DIR but this doesn't appear to be an Atropine installation. Either specify the Atropine installation with -t or put $SCRIPT_BASENAME in the same folder as atropine.py and run it from there."
    fi
else
    ATROPINE_DIR="$OVERRIDE_ATROPINE_DIR"
    if [ ! -d "$ATROPINE_DIR" ]; then
        fail "$ATROPINE_DIR is not a directory."
    fi
fi

if [ "$ATROPINE_DIR" = "." ]; then
    ATROPINE_DIR="$(pwd)"
fi

if [ "$QUIET" -eq 0 -o "$INTERACTIVE" -ne 0 ]; then
    echo "*******************************************************************************"
    echo
    echo "  Welcome to Atropine's Python path fixing script."
    echo "  This script modifies the interpreter line at the top of Atropine's .py files"
    echo "  to point to the correct location of the Python 3 interpreter."
    echo "  You should only need to run this script once."
    echo
    echo "  Your Atropine installation is at: $ATROPINE_DIR"
    echo "  Your Python 3 executable is at:   $PYTHON3_PATH"
    echo
    echo "  I am about to find every .py file in your Atropine installation and change"
    echo "  the interpreter line at the top of the file to:"
    echo
    echo "  #!$PYTHON3_PATH"
    echo ""
    if [ "$INTERACTIVE" -ne 0 ]; then
        echo "  If this looks right, enter Y to perform this operation."
        echo "  To cancel, enter N."
        echo ""
    fi
    echo "*******************************************************************************"
    echo ""
fi

if [ "$INTERACTIVE" -ne 0 ]; then
    if ask_yes_no "OK? [Y/N] "; then
        true
    else
        fail "Cancelled."
    fi

    if [ "$answer" = "N" -o "$answer" = "n" ]; then
        fail "Cancelled."
    fi
fi

# Escape any slashes or backslashes in PYTHON3_PATH, because we're going to put
# it in a sed s/foo/bar/ command...
ESCAPED_PYTHON3_PATH=$(echo "$PYTHON3_PATH" | sed 's/[\/\\]/\\&/g')

# For each file, if the first line starts with #!, replace it with #! followed
# by the correct Python 3 path.
FILES_DONE=0
FILES_FAILED=0
RESULT=0
for pyfile in "$ATROPINE_DIR/webroot/cgi-bin/"*.py "$ATROPINE_DIR/py/"*.py "$ATROPINE_DIR/generators/"*.py "$ATROPINE_DIR/"*.py; do
    sed -i '1s/^#!.*/#!'"$ESCAPED_PYTHON3_PATH/" "$pyfile"
    FILERESULT=$?
    if [ $FILERESULT -ne 0 ]; then
        RESULT=$FILERESULT
        FILES_FAILED=$(($FILES_FAILED + 1))
        echo "Failed to modify $pyfile" 1>&2
    else
        FILES_DONE=$(($FILES_DONE + 1))
    fi
done

if [ "$QUIET" -eq 0 ]; then
    echo
    echo "*******************************************************************************"
    echo
    echo "$FILES_DONE files done."
fi
if [ $RESULT -ne 0 ]; then
    fail "Failed to modify some files. See details above."
else
    if [ "$QUIET" -eq 0 ]; then
        echo "Success. You can try running atropine.py now to start Atropine."
        echo "If that works, you shouldn't need to run this script again on this"
        echo "installation of Atropine."
        echo
    fi
    if [ $INTERACTIVE -ne 0 ]; then
        read -p "Press ENTER to exit... "
    fi
    exit 0
fi
