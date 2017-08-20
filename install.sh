#! /bin/bash

INST_DIR=/usr/local/eSEAT
MKDIR="/bin/mkdir -p "
CP="/bin/cp "
FILES="*.py seatml.xsd rtc.conf"
DIRS="bs4 html libs 3rd_party examples"

[ -d $INST_DIR ] || $MKDIR $INST_DIR

for f in $FILES; do
  $CP $f $INST_DIR
done

for d in $DIRS; do
  $CP -r $d $INST_DIR
done
