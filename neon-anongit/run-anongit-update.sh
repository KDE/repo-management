#!/bin/bash

# Is this anongit enabled?
grep `cat ~/thisanongithost` ~/repo-management/neon-anongit/enabled_anongits.cfg >/dev/null || exit 1

# Update our projects list
rsync -az git.neon.kde.org::neon-projects-list/projects.list ~/projects-to-anongit.list.new
chmod 755 ~/projects-to-anongit.list.new

# Update our copy of repo-management, just to be sure
cd ~/repo-management; git pull

# Begin the update of the repositories
neon-anongit/update-repo-mirrors.sh

# Handle failure of the repository updates
if [ $? -ne 0 ]
  then
    echo "Mirror updating failed, not continuing"
    exit 1
fi
