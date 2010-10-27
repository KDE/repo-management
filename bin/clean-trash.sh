#!/bin/sh

TRASH_CAN="/srv/kdegit/trash"
cutoff=`date -I -d '28 days ago'`
find $TRASH_CAN -type d -name "20??-??-??_*" | while read r
do
    d=`basename $r`
    [[ $d < $cutoff ]] && rm -rf $r
done
