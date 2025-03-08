#!/bin/bash

# makezip.sh
# Package up Atropine into a zip file suitable for distribution.

if [ "$1" = "-b" ]; then
    # Include buildscripts directory
    buildscripts=buildscripts
    shift
else
    buildscripts=""
fi

ATROPINE_VERSION=$1
if [ -z "$ATROPINE_VERSION" ]; then
    # Display help
    echo "Usage: makezip.sh [-b] <version>"
    echo "<version> is in the form x.y.z[-extrastuff]"
    exit 1
fi

# Validate version number format.
echo "$ATROPINE_VERSION" | egrep "^[0-9]+\.[0-9]+\.[0-9]+" > /dev/null
RESULT=$?
if [ $RESULT -ne 0 ]; then
    echo "Version number must be of the form x.y.z where x, y and z are integers."
    echo "It may optionally be followed by additional cruft."
    exit 1
fi

# The zip file will contain a directory with this version in its name, so make
# sure it doesn't contain any characters problematic for Windows.
echo "$ATROPINE_VERSION" | egrep "[/<>\\\\:\"|?*[:cntrl:]]" >/dev/null
RESULT=$?
if [ $RESULT -eq 0 ]; then
    echo "Version number may not contain any characters which would be illegal in a"
    echo "Windows filename. These include the control characters and the following:"
    echo "\\ / < > : \" ? | *"
    exit 1
fi

# Windows filenames may not end with a space or a dot.
echo "$ATROPINE_VERSION" | egrep '\.$| $' >/dev/null
RESULT=$?
if [ $RESULT -eq 0 ]; then
    echo "Version number may not end with a space or a dot."
    exit 1
fi

# START_DIR: our current working directory, which contains all the Atropine
# source files.
START_DIR=$(pwd)

# TEMP_DIR: a temporary directory in which we'll package up the zip
TEMP_DIR=$(mktemp -d --tmpdir)

# VER_DIR: the top-level directory of the zip file, which contains all the
# files. We have this directory so that when someone says "extract to my
# desktop" they don't get all of Atropine's innards smeared over their desktop,
# they get all of Atropine's innards neatly packaged inside a new folder.
VER_DIR="atropine-$ATROPINE_VERSION"
mkdir "$TEMP_DIR/$VER_DIR" || exit 1

# Copy all the files we need to $TEMP_DIR/$VER_DIR, and change to $TEMP_DIR
cp -a generators py webroot $buildscripts licence.txt atropine.py "$TEMP_DIR/$VER_DIR/" || exit 1

cd "$TEMP_DIR" || exit 1

ZIP_FILE_NAME="atropine-$ATROPINE_VERSION.zip"

# Create an empty tourneys directory. Atropine now stores tourneys in
# $HOME/.atropine/tourneys on Linux and %APPDATA%\Atropine\tourneys on
# Windows, but a tourneys directory in the installation itself is still
# required to give Atropine a fighting chance of running on a Mac.
mkdir "$VER_DIR/tourneys"

# Zip up the contents of $VER_DIR into our new zip file, excluding cruft
# we don't need.
zip -r "$ZIP_FILE_NAME" "$VER_DIR" -x \*.db \*.pyc \*.swp || exit 1

# We now have our zip file, but it's in $TEMP_DIR and we're about to delete
# that, so put the zip file in the directory we started in.
cp "$ZIP_FILE_NAME" "$START_DIR/" || exit 1

# Report success and go back to our starting directory
echo "Created $START_DIR/$ZIP_FILE_NAME"
cd "$START_DIR"

# Clean up the temporary directory and everything in it.
rm -rf "$TEMP_DIR"

exit 0
