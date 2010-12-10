#/bin/sh

# First, see if there are any repos that are gone and should be removed. This gets a list of just
# the items that have been removed from the projects-to-anongit.list file which was put into /etc/kdegit
# by rsync from git.kde.org
diff ~/projects-to-anongit.list /etc/kdegit/projects-to-anongit.list | grep "<" | cut -c 3- > ~/diffout

# Is it not empty?
if [ -s ~/diffout ]
  then
    cd /repositories
    # Remove each of the specified repos
    for line in `cat ~/diffout`; do
        echo "Removing repository $line"
        rm -rf $line
    done
    rm ~/diffout
fi

# Now, update this to our local copy in ~git
cp /etc/kdegit/projects-to-anongit.list ~/projects-to-anongit.list

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
        git remote update
        git update-server-info
      else
        rm -rf $bname
        git clone --mirror git://git.kde.org/$line $bname
        cd $bname
        git update-server-info
    fi
done

# Now we need to sync the metadata
cd /home/git/metadata-tree
for file in `find -name "description"`; do
    # Does the description equal the default description?
    diff $file /home/git/repo-management/bin/anongit/default-description > /dev/null
    result=$?
    # If so, make it empty.
    if [ $result -eq 0 ]
      then
        truncate --size=0 $file
    fi
done

# Copy the metadata over to the repositories
rsync -avz . /repositories/
