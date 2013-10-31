#!/bin/sh

if [ "$(pgrep -f industryupdate | wc -l)" -gt 1 ]
then
    echo "Too many industryupdate jobs running:"
    pgrep -lf django-admin.*industryupdate
    pkill -f django-admin.*industryupdate
    sleep 5
    pkill -f9 django-admin.*industryupdate

    exit 1
fi
