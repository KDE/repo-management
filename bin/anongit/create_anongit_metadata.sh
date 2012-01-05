#!/bin/bash

# This creates the list of files to rsync down to the anon mirror. These files are metadata living in the various git repository directories.

# First, clean out what's there
cd ~git/metadata-tree
for file in $( find -type f ); do if [ ! -e /srv/kdegit/repositories/$file ]; then rm $file; fi; done
for dir in $( find -type d ); do if [ -z "$(ls -A $dir)" ]; then rmdir $dir; fi; done

# Now actually do the list
cd ~git
cp projects.list projects-list/projects-to-anongit.list
chmod 755 projects-list/projects-to-anongit.list
rm anongit-repos-build.tmp
for dir in $(cat projects-list/projects-to-anongit.list)
  do
    [ -e /srv/kdegit/repositories/$dir/cloneurl ] && echo "$dir/cloneurl" >> anongit-repos-build.tmp
    [ -e /srv/kdegit/repositories/$dir/description ] && echo "$dir/description" >> anongit-repos-build.tmp
    [ -e /srv/kdegit/repositories/$dir/git-daemon-export-ok ] && echo "$dir/git-daemon-export-ok" >> anongit-repos-build.tmp
    [ -e /srv/kdegit/repositories/$dir/gl-creater ] && echo "$dir/gl-creater" >> anongit-repos-build.tmp
    [ -e /srv/kdegit/repositories/$dir/gl-conf ] && echo "$dir/gl-conf" >> anongit-repos-build.tmp
    [ -e /srv/kdegit/repositories/$dir/gl-owner ] && echo "$dir/gl-owner" >> anongit-repos-build.tmp
    [ -e /srv/kdegit/repositories/$dir/gl-perms ] && echo "$dir/gl-perms" >> anongit-repos-build.tmp
    [ -e /srv/kdegit/repositories/$dir/kde-cloned-from ] && echo "$dir/kde-cloned-from" >> anongit-repos-build.tmp
    [ -e /srv/kdegit/repositories/$dir/kde-repo-nick ] && echo "$dir/kde-repo-nick" >> anongit-repos-build.tmp
    [ -e /srv/kdegit/repositories/$dir/kde-repo-uid ] && echo "$dir/kde-repo-uid" >> anongit-repos-build.tmp
done
rsync -avz --delete --files-from="/home/git/anongit-repos-build.tmp" /srv/kdegit/repositories /home/git/metadata-tree

