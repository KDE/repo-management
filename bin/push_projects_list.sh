#!/bin/sh

# This script is used by git.kde.org to push the current projects list down to the anonymous mirror; new
# mirrors can be added by copying the block below with different hostnames
export RSYNC_CONNECT_PROG='ssh -l git anongit.kde.org nc6 localhost 873'
cd ~git
cp projects.list projects-to-anongit.list
rsync -avz --password-file=/home/git/rsync_push_to_anongit.secret projects-to-anongit.list git-anongit@anongit.kde.org::projects-list
