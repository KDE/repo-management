#/bin/sh
diff ~/projects-to-projects.list /etc/kdegit/projects-to-projects.list | grep "<" | cut -c 3- > ~/diffout
if [ -s ~/diffout ]
  then
    cd /repositories
    for line in `cat ~/diffout`; do
        echo "Removing repository $line"
        rm -rf $line
    done
    rm ~/diffout
fi
cp /etc/kdegit/projects-to-projects.list ~/projects-to-projects.list
for line in `cat ~/projects-to-projects.list`; do
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
cd /home/git/metadata-tree
for file in `find -name "description"`; do
    diff $file /home/git/default-description > /dev/null
    result=$?
    if [ $result -eq 0 ]
      then
        truncate --size=0 $file
    fi
done
rsync -avz . /repositories/
