#!/usr/bin/python

import os
import re
import subprocess

class RepoType:
    "Enum type - Indicates the type of repository"
    Normal = 1
    Sysadmin = 2
    Website = 3
    Scratch = 4
    Clone = 5
    
class ChangeType:
    "Enum type - indicates the type of change to a ref"
    Update = 1
    Create = 2
    Delete = 3
    Forced = 4
    
class RefType:
    "Enum type - indicates the type of ref in the repository"
    Branch = 1
    Tag = 2
    Backup = 3
    Unknown = 4

class Repository:
    "Represents a repository, and changes made to it"
    EmptyRef = "0000000000000000000000000000000000000000"
    
    def __init__(self, ref, old_sha1, new_sha1, push_user):
        "Create a Repository object"
        
        # Save configuration
        self.ref = ref
        self.old_sha1 = old_sha1
        self.new_sha1 = new_sha1
        self.push_user = push_user
        self.commits = []
        
        # Set path and id....
        path_match = re.match("^/home/ben/sysadmin/(.+).git$", os.getenv('GIT_DIR'))
        self.path = path_match.group(1)
        self.uid = self.__get_repo_id()

        # Determine types....
        self.repo_type = self.__get_repo_type()
        self.ref_type = self.__get_ref_type()
        self.change_type = self.__get_change_type()
        
        # Final initialisation
        self.__build_commits()

    def __build_commits(self):
        # Build the revision span git will use to help build the revision list...
        if self.change_type == ChangeType.Delete:
            return
        elif self.change_type == ChangeType.Create:
            revision_span = self.new_sha1
        else:
            merge_base = read_command( 'git merge-base {0} {1}'.format(self.new_sha1, self.old_sha1) )
            revision_span = "{0}..{1}".format(merge_base, self.new_sha1)
            
        # Build the git pretty format + regex.
        l = (
             ('CH' , ('%H%n',  '(?P<sha1>.+)\n')),
             ('AN' , ('%an%n', '(?P<author_name>.+)\n')),
             ('AE' , ('%ae%n', '(?P<author_email>.+)\n')),
             ('D'  , ('%aD%n', '(?P<date>.+)\n')),
             ('CN' , ('%cn%n', '(?P<committer_name>.+)\n')),
             ('CE' , ('%ce%n', '(?P<committer_email>.+)\n')),
             ('MSG', ('%B%xff','(?P<message>(.|\n)+)\xff(?P<diff_stat>(.|\n)*)'))
            )
        pretty_format = ''.join([': '.join((i,j[0])) for i,j in l])
        re_format = '^' + ''.join([': '.join((i,j[1])) for i,j in l]) + '$'

        # Get the data we are going to be parsing....
        log_arguments = "--stat --reverse -z --pretty=format:'{0}'".format(pretty_format)
        command = "git log {0}..{1} {2}".format(self.old_sha1, self.new_sha1, log_arguments) # For debugging...
        #command = "git rev-parse --not --all | grep -v {0} | git log --stdin --no-walk {1} {2}".format(self.old_sha1, log_arguments, revision_span)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.stdout.read()
        
        # If nothing was output -> no commits to parse
        if output == "":
            return
        
        # Parse time!
        for commit_data in output.split("\x00"):
            match = re.match(re_format, commit_data, re.MULTILINE)
            commit = Commit()
            commit.__dict__.update(match.groupdict())
            self.commits.append( commit )

    def __get_repo_id(self):
        base = os.getenv('GIT_DIR')
        # Look for kde-repo-nick, then kde-repo-uid and finally generate one if we find neither....
        if not os.path.exists(base + "/kde-repo-uid"):
            repo_uid = read_command( "echo $GIT_DIR | sha1sum | cut -c -8" )
            uid_file = file(base + "/kde-repo-uid", "w")
            uid_file.write(repo_uid)
            uid_file.close()
        
        if os.path.exists(base + "/kde-repo-nick"):
            repo_id = file(base + "/kde-repo-nick", "r")
        else:
            repo_id = file(base + "/kde-repo-uid", "r")
        
        rid = repo_id.readline().strip()
        repo_id.close()
        return rid

    def __get_repo_type(self):
        sysadmin_repos = ["gitolite-admin", "repo-management"]
        
        # What type of repo have we got???
        if self.path in sysadmin_repos:
            return RepoType.Sysadmin
        elif re.match("^sysadmin/(.+)$", self.path):
            return RepoType.Sysadmin
        elif re.match("^websites/(.+)$", self.path):
            return RepoType.Website
        elif re.match("^scratch/(.+)$", self.path):
            return RepoType.Scratch
        elif re.match("^clones/(.+)$", self.path):
            return RepoType.Clone
        else:
            return RepoType.Normal
            
    def __get_ref_type(self):
        # What type is the ref being changed?
        if re.match("^refs/heads/(.+)$", self.ref):
            return RefType.Branch
        elif re.match("^refs/tags/(.+)$", self.ref):
            return RefType.Tag
        elif re.match("^refs/backups/(.+)$", self.ref):
            return RefType.Backup
        else:
            return RefType.Unknown
            
    def __get_change_type(self):
        # Determine the merge base, to detect if we are experiencing a force or normal push....
        if( self.old_sha1 != self.EmptyRef and self.new_sha1 != self.EmptyRef ):
            merge_base = read_command('git merge-base ' + self.old_sha1 + ' ' + self.new_sha1)

        # What type of change is happening here?
        if self.old_sha1 == self.EmptyRef:
            return ChangeType.Create
        elif self.new_sha1 == self.EmptyRef:
            return ChangeType.Delete
        elif self.old_sha1 != merge_base:
            return ChangeType.Forced
        else:
            return ChangeType.Update

class Commit:
    "Represents a git commit"
    def __init__(self):
        pass

    def __repr__(self):
        return str(self.__dict__)

def read_command( command ):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process.stdout.readline().strip()
