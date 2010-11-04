#!/bin/sh

ssh projects.kde.org "cd /repositories/$1; git remote update; git update-server-info" > /dev/null
