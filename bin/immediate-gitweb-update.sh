#!/bin/sh

# Makes gitweb update immediately so there are no 404s on the commit URLs because of the repo not being updated yet.
ssh anongit1.kde.org "cd /repositories/$1; git remote update; git update-server-info" 1>/dev/null 2>/dev/null
#ssh anongit2.kde.org "cd /repositories/$1; git remote update; git update-server-info" 1>/dev/null 2>/dev/null
#ssh anongit3.kde.org "cd /repositories/$1; git remote update; git update-server-info" 1>/dev/null 2>/dev/null
exit 0
