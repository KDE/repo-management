#!/bin/bash
/home/git/bin/gitolite trigger POST_COMPILE
/home/git/repo-management/bin/verify_new_projects_list.pl /home/git/projects.list.candidate /home/git/projects.list

if [ $? -ne 0 ]
then
  echo "Projects list file may have changed too much; not replacing current list" | mail -r "sysadmin@kde.org" -s "ERROR: projects.list problem on git.kde.org" sysadmin@kde.org
  exit 1
fi

mv /home/git/projects.list.candidate /home/git/projects.list
