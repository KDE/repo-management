#!/bin/sh

# This creates the list of files to rsync down to the anon mirror. These files are metadata living in the various git repository directories.
cd ~git
cp projects.list projects-list/projects-to-anongit.list
chmod 755 projects-list/projects-to-anongit.list
rm anongit-repos-build.tmp
for dir in `cat projects-list/projects-to-anongit.list`
  do
    echo "$dir/cloneurl" >> anongit-repos-build.tmp
    echo "$dir/description" >> anongit-repos-build.tmp
    echo "$dir/git-daemon-export-ok" >> anongit-repos-build.tmp
    echo "$dir/gl-creater" >> anongit-repos-build.tmp
    echo "$dir/gl-owner" >> anongit-repos-build.tmp
    echo "$dir/gl-perms" >> anongit-repos-build.tmp
    echo "$dir/kde-cloned-from" >> anongit-repos-build.tmp
    echo "$dir/kde-repo-nick" >> anongit-repos-build.tmp
    echo "$dir/kde-repo-uid" >> anongit-repos-build.tmp
done
rsync -avz --delete --files-from="/home/git/anongit-repos-build.tmp" /srv/kdegit/repositories /home/git/metadata-tree

