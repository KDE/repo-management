#/bin/bash

# Is an update in progress?
if [ -e /tmp/update_repo.txt ]; then
  echo "Lock exists"
  exit 1;
else
  touch /tmp/update_repo.txt
fi

# Grab our hostname
hostname=$(cat ~/thisanongithost)

# Is the projects list usable?
~/repo-management/helpers/validate-projects-list.pl ~/projects-to-anongit.list ~/projects-to-anongit.list.new
if [ $? -ne 0 ]
then
  echo "Projects list file may have changed too much; not replacing current list and not continuing" | mail -r "sysadmin-systems@kde.org" -s "ERROR: projects.list problem on $hostname" sysadmin-systems@kde.org
  rm /tmp/update_repo.txt
  exit 1
fi

# First, see if there are any repos that are gone and should be removed. This gets a list of just
# the items that have been removed from the projects-to-anongit.list file which was put into projects-to-anongit.list.new
diff ~/projects-to-anongit.list ~/projects-to-anongit.list.new | grep "<" | cut -c 3- > ~/diffout

# Is it not empty?
if [ -s ~/diffout ]
  then
    cd /repositories
    # Remove each of the specified repos
    for line in `cat ~/diffout`; do
        echo "Removing repository $line"
        suffix=$(mktemp -u XXXXXXX)
        newpath="/deleted-repos/$(date +%Y-%m-%d)_$(basename $line)_$suffix"
        mv $line $newpath
        echo "Repository $line moved to $newpath on $hostname" | mail -r "sysadmin-systems@kde.org" -s "REPO DELETION: $line" sysadmin-systems@kde.org
    done
fi
rm ~/diffout

# Now, update this to our local copy in ~git
cp ~/projects-to-anongit.list.new ~/projects-to-anongit.list

# Go through each line and if the repo exists and isn't an empty folder,
# do an update. Otherwise do a clone.
for line in `cat ~/projects-to-anongit.list`; do
    # Change into the repository
    cd /repositories
    dname=`dirname $line`
    gitname=".git"
    bname=`basename $line`
    mkdir -p $dname
    cd $dname

    # Is the repository already populated?
    if [ -e $bname -a -e $bname/HEAD ]
      then
        # It exists - refresh it appropriately
        cd $bname
        git config transfer.fsckObjects true
        git remote update -p
        git update-server-info
      else
        # It doesn't exist, remove it and reclone
        rm -rf $bname
        git clone --mirror git://git.kde.org/$line $bname
        cd $bname
        git fsck
        git config transfer.fsckObjects true
        if [ $? -ne 0 ]
          then
            echo "Fresh mirror clone of git://git.kde.org/$line failed git fsck, not following through with rest of update" | mail -r "sysadmin-systems@kde.org" -s "WARNING: git fsck problem on $hostname" sysadmin-systems@kde.org
            rm /tmp/update_repo.txt
            exit 1
        fi
        git update-server-info
    fi
done

# Update the repository metadata
~/repo-management/anongit/update-repo-metadata.sh /repositories/

# Unlock the process
rm /tmp/update_repo.txt

