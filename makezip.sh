#!/bin/bash

rm atropine.zip 2>/dev/null
zip -r atropine.zip background.jpg docs generators py licence.txt tourneys atropine.py webroot -x \*.db \*.pyc

exit $?
