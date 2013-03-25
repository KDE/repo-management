#!/bin/sh

# This script cleans the trash.
# As you might expect.

cutoff=`date -I -d '28 days ago'`
find $0 -type d -name "20??-??-??_*" | while read r
do
    rm -rf $r
done
