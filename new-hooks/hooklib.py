#!/usr/bin/python

import os
import re
import subprocess
import dns.resolver
import smtplib
import email.mime.text

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
        self.commits = dict()
        
        # Find our configuration directory....
        if os.getenv('REPO_MGMT'):
            self.management_directory = os.getenv('REPO_MGMT')
        else:
            self.management_directory = os.getenv('HOME') + "/repo-management"
        
        # Set path and id....
        path_match = re.match("^/home/ben/sysadmin/(.+).git$", os.getenv('GIT_DIR'))
        self.path = path_match.group(1)
        self.uid = self.__get_repo_id()
        self.__write_metadata()

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
             ('D'  , ('%at%n', '(?P<date>.+)\n')),
             ('CN' , ('%cn%n', '(?P<committer_name>.+)\n')),
             ('CE' , ('%ce%n', '(?P<committer_email>.+)\n')),
             ('MSG', ('%B%xff','(?P<message>(.|\n)+)\xff(?P<files_changed>(.|\n)*)'))
            )
        pretty_format = ''.join([': '.join((i,j[0])) for i,j in l])
        re_format = '^' + ''.join([': '.join((i,j[1])) for i,j in l]) + '$'

        # Get the data we are going to be parsing....
        log_arguments = "--name-only --reverse -z --pretty=format:'{0}'".format(pretty_format)
        command = "git log {0}..{1} {2}".format(self.old_sha1, self.new_sha1, log_arguments) # For debugging...
        #command = "git rev-parse --not --all | grep -v {0} | git log --stdin --no-walk {1} {2}".format(self.old_sha1, log_arguments, revision_span)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.stdout.read()
        
        # If nothing was output -> no commits to parse
        if output == "":
            return
        
        # Parse time!
        for commit_data in output.split("\x00\x00"):
            match = re.match(re_format, commit_data, re.MULTILINE)
            commit = Commit(self)
            commit.__dict__.update(match.groupdict())
            self.commits[ commit.sha1 ] = commit
            
        # Cleanup files_changed....
        for (sha1, commit) in self.commits.iteritems():
            clean_list = commit.files_changed.split("\x00")
            commit.files_changed = [filename.strip() for filename in clean_list]
            
    def __write_metadata(self):
        metadata = file(os.getenv('GIT_DIR') + "/cloneurl", "w")
        metadata.write( "Pull (read-only): git://anongit.kde.org/" + self.path + "\n" )
        metadata.write( "Pull (read-only): http://anongit.kde.org/" + self.path + "\n" )
        metadata.write( "Pull+Push (read+write): git@git.kde.org:" + self.path + "\n" )
        metadata.close()

    def __get_repo_id(self):
        base = os.getenv('GIT_DIR')
        # Look for kde-repo-nick, then kde-repo-uid and finally generate one if we find neither....
        if not os.path.exists(base + "/kde-repo-uid"):
            repo_uid = read_command( "echo $GIT_DIR | sha1sum | cut -c -8" )
            uid_file = file(base + "/kde-repo-uid", "w")
            uid_file.write(repo_uid + "\n")
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
            
class CommitAuditor:
    "Performs all audits on commits"
    def __init__(self, repository):
        self.repository = repository
        self.failures = dict()
        self.__setup_filenames()
            
    def __log_failure(self, commit, message):
        if not self.failures.has_key( commit ):
            self.failures[ commit ] = []
            
        self.failures[ commit ].append( message )
        
    def __setup_filenames(self):
        self.filename_limits = []
        configuration = open(self.repository.management_directory + "/config/blockedfiles.cfg")
        for line in configuration:
            regex = line.strip()

            # Skip comments and blank lines
            if regex.startswith("#") or len(regex) == 0:
                continue
            
            restriction = re.compile(regex)
            if restriction:
                self.filename_limits.append( restriction )

        configuration.close()
        
    def audit_eol(self):
        # Regex's....
        re_commit = re.compile("^\x00(.+)\x00$")
        re_filename = re.compile("^diff --git a\/(\S+) b\/(\S+)$")
        blocked_eol = re.compile(r"(?:\r\n|\n\r|\r)$")
        
        # Get the full diff for all commits...
        commit_list = ' '.join( self.repository.commits.keys() )
        command = "git log -p --reverse --pretty=format:%x00%H%x00 --stdin"
        process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for sha1 in self.repository.commits.keys():
            process.stdin.write(sha1 + "\n")
        process.stdin.close()
        
        # Do EOL audit!
        for line in process.stdout:
            commit_change = re.match( re_commit, line )
            if commit_change:
                commit = commit_change.group(1)
                continue

            file_change = re.match( re_filename, line )
            if file_change:
                filename = file_change.group(2)
                violation = False
                continue

            # Don't complain about the same file twice...
            if violation:
                continue

            # Unless they added it, ignore it
            if not line.startswith("+"):
                continue

            if re.search( blocked_eol, line ):
                # Failure has been found... handle it
                violation = True
                self.__log_failure(commit, "End Of Line Style - " + filename);
                
    def audit_filename(self):
        for commit in self.repository.commits.values():
            for filename in commit.files_changed:
                for restriction in self.filename_limits:
                    if re.search(restriction, filename):
                        self.__log_failure(commit.sha1, "File Name - " + filename)
                        
    def audit_metadata(self):
        # Iterate over commits....
        disallowed_domains = ["localhost", "localhost.localdomain", "(none)"]
        for commit in self.repository.commits.values():
            for email_address in [ commit.committer_email, commit.author_email ]:
                # Extract the email address, and reject them if extraction fails....
                extraction = re.match("^(\S+)@(\S+)$", email_address)
                if not extraction:
                    self.__log_failure(commit.sha1, "Email Address - " + email_address)
                
                # Don't allow domains which are disallowed...
                domain = extraction.group(2)
                if domain in disallowed_domains:
                    self.__log_failure(commit.sha1, "Email Address - " + email_address)

                # Ensure they have a valid MX/A entry in DNS....
                try:
                    mx_results = dns.resolver.query(domain, 'MX')
                    a_results  = dns.resolver.query(domain, 'A')
                except dns.resolver.NXDOMAIN:
                    self.__log_failure(commit.sha1, "Email Address - " + email_address)

class CiaNotifier:
    "Notifies CIA of changes to a repository"
     template = """<message>
  <generator>
    <name>KDE CIA Python client</name>
    <version>1.00</version>
    <url>http://projects.kde.org/repo-management</url>
  </generator>
  <source>
    <project>KDE</project>
    <module>{0}</module>
    <branch>{1}</branch>
  </source>
  <timestamp>{2}</timestamp>
  <body>
    <commit>
      <author>{3}</author>
      <revision>{4}</revision>
      <files>
        {5}
      </files>
      <log>
        {6}
      </log>
      <url>{7}</url>
    </commit>
  </body>
</message>"""

    def __init__(self, repository):
        self.repository = repository
        self.smtp = smtplib.SMTP()
        
    def __del__(self):
        self.smtp.quit()
        
    def notify(self):
        # Do we need to sleep at all?
        if len(self.repository.commits) > 10:
            big_sleep = True
            
        # Iterate and send....
        for commit in self.repository.commits.values():
            self.__send_cia(commit)
            if big_sleep:
                sleep(0.5)
                
    def __send_cia(self, commit):
        # Build the <files> section for the template...
        files_list = []
        for filename in commit.files_changed:
            files_list.append( "<file>{0}</file>".format(filename) )
        file_output = '\n'.join(files_list)
                
        # Fill in the template...
        commit_xml = template
        commit_xml.format( self.repository.path, "", commit.date, commit.author_name, commit.sha1, file_output, commit.message, commit.url() )
        
        # Craft the email....
        message = MIMEText( commit_xml )
        message['Subject'] = "DeliverXML"
        message['From'] = "sysadmin@kde.org"
        message['To'] = "cia@cia.vc"
        message['Content-Type'] = "text/xml; charset=UTF-8"
        message['Content-Transfer-Encoding'] = "8bit"
        
        # Send email...
        self.smtp.sendmail("sysadmin@kde.org", ["cia@cia.vc"], message.as_string())

class Commit:
    "Represents a git commit"
    def __init__(self, repository):
        self.repository = repository

    def __repr__(self):
        return str(self.__dict__)
        
    def url(self):
        return "http://commits.kde.org/{0}/{1}".format( self.repository.uid, self.sha1 )

def read_command( command ):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process.stdout.readline().strip()
