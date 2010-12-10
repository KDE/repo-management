#!/bin/bash

grep `cat /home/git/thisanongithost` /home/git/repo-management/config/enabled_anongits.cfg >/dev/null || exit 1

rsync -avz git.kde.org::projects-list/projects-to-anongit.list /etc/kdegit/projects-to-anongit.list
chmod 755 /etc/kdegit/projects-to-anongit.list

rm -rf /home/git/metadata-tree/*
rsync -avz git.kde.org::metadata-tree/ /home/git/metadata-tree/

cd /home/git/repo-management; git pull

bin/anongit/update_repo_mirrors.sh
bin/anongit/update_repo_pointers.sh

[ ! -d /var/lib/redmine/redmine ] && exit 0

cd /var/lib/redmine/redmine; RAILS_ENV=production rake redmine:fetch_changesets

