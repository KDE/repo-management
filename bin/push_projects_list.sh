#!/bin/sh

export RSYNC_CONNECT_PROG='ssh -l git projects.kde.org nc6 localhost 873'
cd ~git
rsync -avz --password-file=/home/git/rsync_push_to_projects.secret projects.list git-projects@projects.kde.org::projects-list
