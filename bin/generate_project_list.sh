#!/bin/bash
if [ ! -f /home/git/projects.list ]; then
  exit
fi

/home/git/repo-management/bin/verify_new_projects_list.pl /home/git/projects.list /home/git/projects-list/projects-to-anongit.list

if [ $? -ne 0 ]
then
  echo "Projects list file may have changed too much; not replacing current list" | mail -r "sysadmin-systems@kde.org" -s "ERROR: projects.list problem on git.kde.org" sysadmin-systems@kde.org
  exit 1
fi

chmod 644 /home/git/projects.list
mv /home/git/projects.list /home/git/projects-list/projects-to-anongit.list
