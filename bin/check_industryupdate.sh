#!/bin/sh

if [ "$(pgrep -f industryupdate | wc -l)" -gt 1 ]
then
    echo "Too many industryupdate jobs running:"
    pgrep -lf django-admin.*industryupdate
    pkill -f django-admin.*industryupdate
    sleep 5
    pkill -9 -f django-admin.*industryupdate

    exit 1
fi
