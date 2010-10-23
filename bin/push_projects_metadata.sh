#!/bin/sh

export RSYNC_CONNECT_PROG='ssh -l git projects.kde.org nc6 localhost 873'
cd ~git
rm projects-repos-build.tmp
for dir in `cat projects-to-projects.list`
  do
    echo "$dir/git-daemon-export-ok" >> projects-repos-build.tmp
    echo "$dir/description" >> projects-repos-build.tmp
    echo "$dir/kde-cloned-from" >> projects-repos-build.tmp
    echo "$dir/kde-repo-uid" >> projects-repos-build.tmp
    echo "$dir/kde-repo-nick" >> projects-repos-build.tmp
    echo "$dir/gl-creater" >> projects-repos-build.tmp
    echo "$dir/gl-owner" >> projects-repos-build.tmp
    echo "$dir/gl-perms" >> projects-repos-build.tmp
done
rsync -avz --password-file=/home/git/rsync_push_to_projects.secret --files-from="/home/git/projects-repos-build.tmp" /srv/kdegit/repositories git-projects@localhost::metadata-tree
