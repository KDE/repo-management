#/bin/sh
diff ~/projects.list /etc/kdegit/projects.list | grep "<" | cut -c 3- > ~/diffout
if [ -s ~/diffout ]
  then
    cd /repositories
    for line in `cat ~/diffout`; do
        echo "Removing repository $line"
        rm -rf $line
    done
    cp /etc/kdegit/projects.list ~/projects.list
    rm ~/diffout
fi
for line in `cat ~/projects.list`; do
    cd /repositories
    dname=`dirname $line`
    gitname=".git"
    bname=`basename $line`
    bname_nogit=${bname%$gitname}
    mkdir -p $dname
    cd $dname
    if [ -e $bname ]
      then
        cd $bname
        git fetch --all --tags --prune
      else
        git clone --bare git://anongit.kde.org/$line $bname
        cd $bname
        echo "fetch = +refs/heads/*:refs/heads/*" >> config
    fi
done
cd /home/git/metadata-tree
for file in `find -name "description"`; do
    diff $file /home/git/default-description > /dev/null
    result=$?
    if [ $result -eq 0 ]
      then
        rm $file
    fi
done
cd /repositories
rsync -avz /home/git/metadata-tree/* .
