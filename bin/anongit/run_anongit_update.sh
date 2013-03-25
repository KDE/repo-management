#!/bin/bash

grep `cat /home/git/thisanongithost` /home/git/repo-management/config/enabled_anongits.cfg >/dev/null || exit 1

rsync -az git.kde.org::projects-list/projects-to-anongit.list /home/git/projects-to-anongit.list.new
chmod 755 /home/git/projects-to-anongit.list.new

rsync -az --delete git.kde.org::metadata-tree/ /home/git/metadata-tree/

cd /home/git/repo-management; git pull

bin/anongit/update_repo_mirrors.sh

if [ $? -ne 0 ]
  then
    echo "Mirror updating failed, not continuing"
fi
bin/anongit/update_repo_pointers.sh

