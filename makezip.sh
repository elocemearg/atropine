#!/bin/bash

rm atropine.zip 2>/dev/null
zip -r atropine.zip background.jpg countdown.jpg docs generators py licence.txt teleost.py tourneys atropine.py webroot -x \*.db

exit $?
