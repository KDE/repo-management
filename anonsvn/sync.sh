#!/bin/bash

export PATH=/bin:/usr/local/bin:/usr/bin
export HOME=$HOME
cd ~


if ! lockfile -1 -r 1 $HOME/svn.lock; then
  if ! kill -s 0 `cat $HOME/svn.pid`  &> /dev/null; then
    echo "Ignoring stale lock file."
    rm -f $HOME/svn.lock
    lockfile -r 1 $HOME/svn.lock
  else
    exit
  fi
fi

bail_out() {
  rm -f $HOME/svn.pid
  rm -f $HOME/svn.lock
  exit 0
}


echo $$ > $HOME/svn.pid

rm -f ~/rev_act
echo -n > ~/rev_act
echo "dav/activities.pag" >> ~/rev_act
echo "db/transactions" >> ~/rev_act
echo "db/current" >> ~/rev_act

rsync -zqa --timeout=600 --files-from=$HOME/rev_act svn.kde.org::svnmirror /home/svn/tmp/
test "$?" -gt 0 && bail_out


oldrev=`cat /media/svn/home/kde/db/current | awk '{print $1;}'`
newrev=`cat /home/svn/tmp/db/current | awk '{print $1;}'`

#test "$oldrev" = "$newrev" && bail_out

# be conservative
oldref=$(($oldrev-1000))

rm -f ~/rev_seq
echo -n > ~/rev_seq
echo "dav/activities.pag" >> ~/rev_seq
echo "db/transactions" >> ~/rev_seq

for i in 1440564 `seq $oldref $newrev`; do
  echo "db/revs/$i" >> ~/rev_seq
  echo "db/revprops/$i" >> ~/rev_seq
done

rsync -zavc --timeout=3600 --files-from=$HOME/rev_seq svn.kde.org::svnmirror /media/svn/home/kde
test "$?" -gt 0 && bail_out

mv -f /home/svn/tmp/db/current /media/svn/home/kde/db/current

bail_out
