#!/bin/sh

# Makes gitweb update immediately so there are no 404s because it hasn't updated yet.
ssh projects.kde.org "cd /repositories/$1; git remote update; git update-server-info" 1>/dev/null 2>/dev/null
