#!/bin/bash

# Grab our input
localrepository="$1"

# If the repository is a kde/* repository then we need to map it to a equivalent git.kde.org path
# This is done by removing the kde/ component
# For websites and sysadmin repositories nothing special is needed, as the namespace for those is identical
remoterepository=${localrepository#kde/}

# Build the remote URL up
remoteurl="git@git.kde.org:$remoterepository"

# Now we push it up there
cd "/srv/gitlab/repositories/$localrepository"
git push --mirror "$remoteurl"
