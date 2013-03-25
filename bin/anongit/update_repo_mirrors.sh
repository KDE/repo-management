#/bin/bash

if [ -e /tmp/update_repo.txt ]; then
  echo "Lock exists"
  exit 1;
else
  touch /tmp/update_repo.txt
fi

~/repo-management/bin/verify_new_projects_list.pl ~/projects-to-anongit.list ~/projects-to-anongit.list.new
if [ $? -ne 0 ]
then
  echo "Projects list file may have changed too much; not replacing current list and not continuing" | mail -r "sysadmin@kde.org" -s "WARNING: projects.list problem on $HOSTNAME" sysadmin@kde.org
  exit 1
fi

# First, see if there are any repos that are gone and should be removed. This gets a list of just
# the items that have been removed from the projects-to-anongit.list file which was put into projects-to-anongit.list.new
diff ~/projects-to-anongit.list /home/git/projects-to-anongit.list.new | grep "<" | cut -c 3- > ~/diffout

# Is it not empty?
if [ -s ~/diffout ]
  then
    cd /repositories
    # Remove each of the specified repos
    for line in `cat ~/diffout`; do
        echo "Removing repository $line"
        mv $line /deleted-repos/$(date +%Y-%m-%d)_$(basename $line)
    done
fi
rm ~/diffout

# Now, update this to our local copy in ~git
cp /home/git/projects-to-anongit.list.new ~/projects-to-anongit.list

# Go through each line and if the repo exists and isn't an empty folder,
# do an update. Otherwise do a clone.
for line in `cat ~/projects-to-anongit.list`; do
    cd /repositories
    dname=`dirname $line`
    gitname=".git"
    bname=`basename $line`
    mkdir -p $dname
    cd $dname
    if [ -e $bname -a -e $bname/HEAD ]
      then
        cd $bname
        git remote update -p
        git update-server-info
      else
        rm -rf $bname
        git clone --mirror git://git.kde.org/$line $bname
        cd $bname
        git fsck
        if [ $? -ne 0 ]
          then
            echo "Fresh mirror clone of git://git.kde.org/$line failed git fsck, not following through with rest of update" | mail -r "sysadmin@kde.org" -s "WARNING: git fsck problem on $HOSTNAME" sysadmin@kde.org
            exit 1
        fi
        git update-server-info
    fi
done

# Now we need to sync the metadata
cd /home/git/metadata-tree
for file in `find -name "description"`; do
    # Does the description equal the default description?
    diff $file /home/git/repo-management/bin/anongit/default_description > /dev/null
    result=$?
    # If so, make it empty.
    if [ $result -eq 0 ]
      then
        truncate --size=0 $file
    fi
done

# Copy the metadata over to the repositories
rsync -az . /repositories/

# In case we have extra metadata left over, having these directories on disk that don't really exist prevents us from re-syncing the repository again
cd /repositories
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done

cd /repositories/sysadmin
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done

cd /repositories/websites
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done

cd /repositories/scratch
for line in $( find -mindepth 2 -maxdepth 2 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done

cd /repositories/clones
for line in $( find -mindepth 3 -maxdepth 3 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done

# Unlock the process
rm /tmp/update_repo.txt

