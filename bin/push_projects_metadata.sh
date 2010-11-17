#!/bin/sh

# This creates the list of files to rsync down to the anon mirror. These files are metadata living in the various git repository directories.
cd ~git
rm anongit-repos-build.tmp
for dir in `cat projects-to-anongit.list`
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
export RSYNC_CONNECT_PROG='ssh -l git %H nc6 localhost 873'
# This should go to ~git/metadata-tree
rsync -avz --password-file=/home/git/rsync_push_to_anongit.secret --files-from="/home/git/anongit-repos-build.tmp" /srv/kdegit/repositories git-anongit@anongit1.kde.org::metadata-tree
rsync -avz --password-file=/home/git/rsync_push_to_anongit.secret --files-from="/home/git/anongit-repos-build.tmp" /srv/kdegit/repositories git-anongit@anongit2.kde.org::metadata-tree
rsync -avz --password-file=/home/git/rsync_push_to_anongit.secret --files-from="/home/git/anongit-repos-build.tmp" /srv/kdegit/repositories git-anongit@anongit3.kde.org::metadata-tree
