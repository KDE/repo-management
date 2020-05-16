#!/bin/bash

# Grab our input
urlpath="$1"

# Before we can proceed, is this a blacklisted repository?
# We blacklist them as these repositories are used by all builds, and Jenkins is incapable of ignoring a repository for polling (bug in Jenkins)
if [[ "$urlpath" = "sysadmin/ci-tooling" ]] || [[ "$urlpath" = "sysadmin/repo-metadata" ]] || [[ "$urlpath" = "sysadmin/kde-build-metadata" ]] || [[ "$urlpath" = "frameworks/kapidox" ]] || [[ "$urlpath" = "sdk/kde-dev-scripts" ]]; then
    exit 0
fi

# Now we wait 10 seconds to let systems settle
sleep 10s

# Tell the KDE CI system
curl --connect-timeout 10 --max-time 10 "https://build.kde.org/git/notifyCommit?url=https://invent.kde.org/$urlpath" &> /dev/null
# Also tell the Binary Factory
curl --connect-timeout 10 --max-time 10 "https://binary-factory.kde.org/git/notifyCommit?url=https://invent.kde.org/$urlpath" &> /dev/null
