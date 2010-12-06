#!/bin/sh

# This script is used by git.kde.org to push the current projects list down to the anonymous mirror; new
# mirrors can be added by copying the block below with different hostnames
export RSYNC_CONNECT_PROG='ssh -l git %H nc localhost 873'
cd ~git
cp projects.list projects-to-anongit.list
rsync -avz --password-file=/home/git/rsync_push_to_anongit.secret projects-to-anongit.list git-anongit@anongit1.kde.org::projects-list
rsync -avz --password-file=/home/git/rsync_push_to_anongit.secret projects-to-anongit.list git-anongit@anongit2.kde.org::projects-list
rsync -avz --password-file=/home/git/rsync_push_to_anongit.secret projects-to-anongit.list git-anongit@anongit3.kde.org::projects-list
