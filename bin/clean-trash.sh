#!/bin/sh

# This script cleans the trash.
# As you might expect.

TRASH_CAN="/srv/kdegit/trash"
cutoff=`date -I -d '28 days ago'`
find $TRASH_CAN -type d -name "20??-??-??_*" | while read r
do
    rm -rf $r
done
