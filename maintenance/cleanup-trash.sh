#!/bin/sh

# This script cleans the trash.
# As you might expect.

cutoff=`date -I -d '28 days ago'`
find $1 -type d -name "${cutoff}_*" | while read r
do
    rm -rf $r
done
