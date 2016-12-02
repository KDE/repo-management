# Where are the repositories?
repositories=$1

# Update the metadata tree
rsync -az --delete git.kde.org::metadata-tree/ ~/metadata-tree/

# Now we need to sync the metadata
cd ~/metadata-tree
for file in `find -name "description"`; do
    # Does the description equal the default description?
    diff $file ~/repo-management/anongit/default_description > /dev/null
    result=$?
    # If so, make it empty.
    if [ $result -eq 0 ]
      then
        truncate --size=0 $file
    fi
done

# Copy the metadata over to the repositories
rsync -az . $repositories/

# In case we have extra metadata left over, having these directories on disk that don't really exist prevents us from re-syncing the repository again
cd $repositories
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done

cd $repositories/sysadmin
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done

cd $repositories/websites
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done

cd $repositories/scratch
for line in $( find -mindepth 2 -maxdepth 2 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done

cd $repositories/clones
for line in $( find -mindepth 3 -maxdepth 3 -type d -name "*.git" ); do if [ ! -e $line/HEAD ]; then rm -rf $line; fi; done