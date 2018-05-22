#!/bin/bash

# Grab our input
urlpath="$1"

# Before we can proceed, is this a blacklisted repository?
if [[ "$urlpath" = "sysadmin/ci-tooling.git" ]] || [[ "$urlpath" = "sysadmin/repo-metadata.git" ]] || [[ "$urlpath" = "kde-build-metadata.git" ]] || [[ "$urlpath" = "kapidox.git" ]] || [[ "$urlpath" = "kde-dev-scripts.git" ]]; then
    exit
fi

# Now we wait 10 seconds - this allows the anongit network to sync
sleep 10s

# Tell the KDE CI system
curl --connect-timeout 10 --max-time 10 "https://build.kde.org/git/notifyCommit?url=git://anongit.kde.org/$urlpath" &> /dev/null

# If it is a website then we should tell the Binary Factory as well
if [[ "$urlpath" = "websites/"* ]]; then
    curl --connect-timeout 10 --max-time 10 "https://binary-factory.kde.org/git/notifyCommit?url=https://anongit.kde.org/$urlpath" &> /dev/null
fi

# Trigger an external build system (contact santa_)
curl --connect-timeout 10 --max-time 10 "http://gpul.grupos.udc.es:8080/git/notifyCommit?url=git://anongit.kde.org/$urlpath" &> /dev/null

