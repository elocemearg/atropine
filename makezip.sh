#!/bin/bash

rm atropine.zip 2>/dev/null
zip -r atropine.zip generators py licence.txt tourneys atropine.py webroot -x \*.db \*.pyc

exit $?
