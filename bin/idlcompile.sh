#!/bin/bash

if [ y"$1" = "y" ]; then
  echo "Usage $0 <idl_file>"
else
  if [ ! -e rtm ]; then
    /bin/mkdir rtm
  fi
  if [ -d rtm ]; then
    /usr/bin/omniidl -bpython -Crtm $1
  else
    echo "rtm is not directory, please remove rtm"
  fi
fi
