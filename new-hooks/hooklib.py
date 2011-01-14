#!/usr/bin/python

import os
import re
import time
import subprocess
import dns.resolver
import smtplib
from email.mime.text import MIMEText
from emai.header import Header

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
    Branch = "branch"
    Tag = "tag"
    Backup = "backup"
    Notes = "notes"
    Unknown = 0

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
        path_match = re.match("^/home/ben/sysadmin/(.+).git$", os.getcwd())
        self.path = path_match.group(1)
        self.uid = self.__get_repo_id()
        self.__write_metadata()

        # Determine types....
        self.repo_type = self.__get_repo_type()
        self.ref_type = self.__get_ref_type()
        self.change_type = self.__get_change_type()
        ref_name_match = re.match("^refs/(.+)/(.+)$", self.ref)
        self.ref_name = ref_name_match.group(2)

        # Final initialisation
        self.__build_commits()
        
    def backup_ref(self):
        # Back ourselves up!
        command = "git update-ref refs/backup/{0}-{1}-{2} {3}".format( self.ref_type, self.ref_name, int( time.time() ), self.old_sha1 )
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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
             ('MSG', ('%B%xff','(?P<message>(.|\n)+)\xff\n(?P<files_changed>(.|\n)*)'))
            )
        pretty_format = ''.join([': '.join((i,j[0])) for i,j in l])
        re_format = '^' + ''.join([': '.join((i,j[1])) for i,j in l]) + '$'

        # Get the data we are going to be parsing....
        log_arguments = "--name-status -z --pretty=format:'{0}'".format(pretty_format)
        command = "git rev-parse --not --all | grep -v {0} | git rev-list --reverse --stdin {2} | git log --stdin --no-walk {1}"
        command = command.format(self.old_sha1, log_arguments, revision_span)
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
            clean_list = re.split("\x00", commit.files_changed)
            files = clean_list[1::2]
            changes = clean_list[::2]
            commit.files_changed = dict( zip(files, changes) )
            
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
        elif re.match("^refs/notes/(.+)$", self.ref):
            return RefType.Notes
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
        
        # Do EOL audit!
        process = get_change_diff( self.repository, "-p" )
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
        self.smtp.connect()
        
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
                time.sleep(0.5)
                
    def __send_cia(self, commit):
        # Build the <files> section for the template...
        files_list = []
        for filename in commit.files_changed:
            files_list.append( "<file>{0}</file>".format(filename) )
        file_output = '\n        '.join(files_list)
                
        # Fill in the template...
        commit_xml = self.template.format( self.repository.path, self.repository.ref_name, commit.date, commit.author_name, commit.sha1, file_output, commit.message.strip(), commit.url() )
        
        # Craft the email....
        message = MIMEText( commit_xml )
        message['Subject'] = "DeliverXML"
        message['From'] = "sysadmin@kde.org"
        message['To'] = "cia@cia.vc"
        message['Content-Type'] = "text/xml; charset=UTF-8"
        message['Content-Transfer-Encoding'] = "8bit"
        
        # Send email...
        self.smtp.sendmail("sysadmin@kde.org", ["cia@cia.vc"], message.as_string())

class EmailNotifier:
    "Notifies a specified email address of changes to a repository"

    def __init__(self, repository):
        self.repository = repository
        self.smtp = smtplib.SMTP()
        self.smtp.connect()
        
    def __del__(self):
        self.smtp.quit()
        
    def notification_address(self):
        if self.repository.repo_type == RepoType.Sysadmin:
            return "sysadmin-svn@kde.org"
        else:
            return "kde-commits@kde.org"
        
    def notify(self):
        # Get diff-stats if needed, and perform content checks...
        diffs, diffstats = self.__retrieve_diffs()
        self.__check_problems()
        
        # Send out the mails...
        for (sha1, commit) in self.repository.commits.iteritems():
            self.__send_email(commit, diffs[sha1], diffstats[sha1])
            
    def __retrieve_diffs(self):
        # Build our diffs....
        diffs = defaultdict(list)
        process = get_change_diff( self.repository, "-p" )
        for line in process.stdout:
            commit_change = re.match( "^\x00(.+)\x00$", line )
            if commit_change:
                commit = commit_change.group(1)
                continue

            if len(diffs[commit]) < 8000:
                diffs[commit].append(line)
            else:
                diffs[commit] = None
                
        # Build our diff stats...
        diffstats = dict()
        process = get_change_diff( self.repository, "--stat" )
        data = process.stdout.read()
        for line in data.split('\x00\x00'):
            commit_change = re.match( "^(.+)\x00(.|\n)+$", line, re.MULTILINE )
            commit = commit_change.group(1)
            diffstats[commit] = commit_change.group(2)
                
        return (diffs, diffstats)
        
    def __check_problems(self):
        # Initialisation
        self.file_notes = defaultdict( defaultdict(list) )
        self.forced_cc  = list()

        # Retrieve the diff and do the problem checks...
        process = get_change_diff( self.repository, "-p" )
        for line in process.stdout:
            commit_change = re.match( "^\x00(.+)\x00$", line )
            if commit_change:
                commit = commit_change.group(1)
                continue
            
            file_change = re.match( "^diff --git a\/(\S+) b\/(\S+)$", line )
            if file_change:
                # Are we changing file? If so, we have the full diff, so do a license check....
                if filename and self.repository.commits[ commit ].files_changed[ filename ] == 'A':
                    self.__check_license( commit, filename, diff.join(' ') )

                diff = list()
                filename = file_change.group(2)
                continue
            
            # Do an incremental check for *.desktop syntax errors....
            if re.search("\.desktop$", filename) and re.search("[^=]+=.*[ \t]$", line) and not re.match("^#", line):
                self.file_notes[ commit ][ filename ].append( "[TRAILING SPACE]" )
                self.forced_cc.append( commit )
                
            # Look for things which aren't safe....
            unsafe_matches = list()
            unsafe_matches.append( "\b(KRun::runCommand|K3?ShellProcess|setUseShell|setShellCommand)\b\s*[\(\r\n]" )
            unsafe_matches.append( "\b(system|popen|mktemp|mkstemp|tmpnam|gets|syslog|strptime)\b\s*[\(\r\n]" )
            unsafe_matches.append( "(scanf)\b\s*[\(\r\n]" )

            safety_check = line
            unsafe = None
            #$current =~ s/\"[^\"]*\"//g;
            #$current =~ s/\/\*.*\*\///g;
            #$current =~ s,//.*,,g;
            for safety_match in unsafe_matches:
                match = re.match(safety_match, safety_check)
                if match:
                    self.file_notes[ commit ][ filename ].append("[POSSIBLY UNSAFE: " + match.group(1) + "]")
                    self.forced_cc.append( commit )
            
            # Store the diff....
            diff.append(line)

    def __check_license(self, text):
        gl = qte = license = ""
        text = re.sub("^\#", "", text)
        text = re.sub("\t\n\r", "   ", text)
        text = re.sub("[^ A-Za-z.@0-9]", "", text)
        text = re.sub("\s+", " ", text)

        if re.search("version 2(?:\.0)? .{0,40}as published by the Free Software Foundation", text):
            gl = " (v2)"

        if re.search("version 2(?:\.0)? of the License", text):
            gl = " (v2)"
  
        if re.search("version 3(?:\.0)? .{0,40}as published by the Free Software Foundation", text):
            gl = " (v3)"
   
        if re.search("either version 2(?: of the License)? or at your option any later version", text):
            gl = " (v2+)"

        if re.search("version 2(?: of the License)? or at your option version 3", text):
            gl = " (v2/3)"
                
        if re.search("version 2(?: of the License)? or at your option version 3 or at the discretion of KDE e.V.{10,60}any later version", text):
            gl = " (v2/3+eV)"

        if re.search("either version 3(?: of the License)? or at your option any later version", text):
            gl = " (v3+)"
                
        if re.search("version 2\.1 as published by the Free Software Foundation", text):
            gl = " (v2.1)"
                
        if re.search("2\.1 available at: http:\/\/www.fsf.org\/copyleft\/lesser.html", text):
            gl = " (v2.1)"

        if re.search("either version 2\.1 of the License or at your option any later version", text):
            gl = " (v2.1+)"

        if re.search("([Pp]ermission is given|[pP]ermission is also granted|[pP]ermission) to link (the code of )?this program with (any edition of )?(Qt|the Qt library)", text):
            qte = " (+Qt exception)"

        # Check for an old FSF address
        # MIT licenses will trigger the check too, as "675 Mass Ave" is MIT's address
        if re.search("(?:675 Mass Ave|59 Temple Place|Suite 330|51 Franklin Steet|02139|02111-1307)", text, re.IGNORECASE):
            # "51 Franklin Street, Fifth Floor, Boston, MA 02110-1301" is the right FSF address
            wrong = " (wrong address)"
            license_problem = True

        # LGPL or GPL
        if re.search("under (the (terms|conditions) of )?the GNU (Library|Lesser) General Public License", text):
            license = "LGPL" + gl + wrong + " " + license
                
        if re.search("under (the (terms|conditions) of )?the (Library|Lesser) GNU General Public License", text):
            license = "LGPL" + gl + wrong + " " + license
                
        if re.search("under (the (terms|conditions) of )?the (GNU )?LGPL", text):
            license = "LGPL" + gl + wrong + " " + license
                
        if re.search("[Tt]he LGPL as published by the Free Software Foundation", text):
            license = "LGPL" + gl + wrong + " " + license
                
        if re.search("LGPL with the following explicit clarification", text):
            license = "LGPL" + gl + wrong + " " + license

        if re.search("under (the terms of )?(version 2 of )?the GNU (General Public License|GENERAL PUBLIC LICENSE)", text):
            license = "GPL" + gl + qte + wrong + " " + license

        # QPL
        if re.search("may be distributed under the terms of the Q Public License as defined by Trolltech AS", text):
            license = "QPL " + license

        # X11, BSD-like
        if re.search("Permission is hereby granted free of charge to any person obtaining a copy of this software and associated documentation files", text):
            license = "X11 (BSD like) " + license

        # MIT license
        if re.search("Permission to use copy modify (and )?distribute(and sell)? this software and its documentation for any purpose", text):
            license = "MIT " + license

        # BSD
        if re.search("MERCHANTABILITY( AND|| or) FITNESS FOR A PARTICULAR PURPOSE", text) and re.search("GPL", license):
            license = "BSD " + license

        # MPL
        if re.search("subject to the Mozilla Public License Version 1.1", text):
            license = "MPL 1.1 " + license
                
        if re.search("Mozilla Public License Version 1\.0/", text):
            license = "MPL 1.0 " + license

        # Artistic license
        if re.search("under the Artistic License", text):
            license = "Artistic " + license

        # Public domain
        if re.search("Public Domain", text, re.IGNORECASE) or re.search(" disclaims [Cc]opyright", text):
            license = "Public Domain " + license

        # Auto-generated
        if re.search("(All changes made in this file will be lost|This file is automatically generated|DO NOT EDIT|DO NOT delete this file|[Gg]enerated by|uicgenerated|produced by gperf)", text):
            license = "GENERATED FILE"
            license_problem = True

        # Don't bother with trivial files.
        if len(license) == 0 and len(text) < 128:
            license = "Trivial file"

        # About every license has this clause; but we've failed to detect which type it is.
        if len(license) == 0 and re.search("This (software|package)( is free software and)? is provided ", text, re.IGNORECASE):
            license = "Unknown license"
            license_problem = True

        # Either a missing or an unsupported license
        if len(license) == 0:
            license = "UNKNOWN"
            license_problem = True

        license = license.strip()
        if len(license):
            self.file_notes[ commit ][ filename ].append( "[License: " + license + "]" )

        if license_problem:
            self.forced_cc.append( commit )
                
    def __send_email(self, commit, diff, diffstat):    
        # Build list for X-Commit-Directories...
        commit_directories = dict()
        for filename in commit.files_changed:
            # Seperate out the directory...
            match = re.match("^(.+)/(.+)$", filename)
            commit_directories.append( match.group(1) )
            
        # Check for keywords...
        keyword_info = self.__parse_keywords(commit)
        
        # Build up the needed parts of the message....
        firstline = "Git commit {0} by {1}".format( commit.sha1, commit.committer_name )
        if commit.author_name != commit.committer_name:
            firstline = firstline + " on behalf of " + commit.author_name

        summary = list(firstline, "\n")
        for line in diffstat.split('\n'):
            match = re.match("^(.+) |", line)
            filename = match.group(1)
            notes = self.file_notes[commit.sha1][filename].join(" ")
            summary.append( line + " | " + notes )
            
        # Build a list of addresses to Cc,
        cc_addresses = keyword_info['email_cc'] + keyword_info['email_cc2']
        if commit.sha1 in self.forced_cc:
            cc_addresses.append( commit.committer_email )
            
        if keyword_info['email_gui']:
            cc_addresses.append( 'kde-doc-english@kde.org' )
            
        # Build the subject
        lowest_common_path = os.path.commonprefix( commit_directories )
        subject = "[{0}] {1}".format(self.repository.path, lowest_common_path)
            
        # Handle the normal mailing list mails....
        message = MIMEText( summary.join('\n') )
        message['Subject'] = Header( subject )
        message['From'] = Header( "{0} <{1}>".format( commit.committer_name, commit.committer_email ) )
        message['To'] = Header( self.notification_address() )
        message['Cc'] = Header( cc_addresses.join(', ') )
        message['X-Commit-Ref'] = Header( self.repository.ref_name )
        message['X-Commit-Project'] = Header( self.repository.path )
        message['X-Commit-Directories'] = Header( "(0)" + commit_directories.join('\n') )

        message['Content-Type'] = "text/plain; charset=UTF-8"
        message['Content-Transfer-Encoding'] = "8bit"
                
        # Send email...
        to_addresses = cc_addresses + [self.notification_address()]
        self.smtp.sendmail(commit.committer_email, to_addresses, message.as_string())         
            
    def __parse_keywords(self, commit):
        split = dict()
        split['bug_fixed'] = re.compile("^\s*(?:BUGS?|FEATURE)[:=]\s*(\d{4,10})")
        split['bug_cc']    = re.compile("^\s*CCBUGS?[:=]\s*(\d{4,10})")
        split['email_cc']  = re.compile("^\s*CC[-_]?MAIL[:=]\s*(.*)")
        split['email_cc2'] = re.compile("^\s*C[Cc][:=]\s*(.*)")
        split['fixed_in']  = re.compile("^\s*FIXED[-_]?IN[:=]\s*(\d[\d\.-]*)/")

        presence = dict()
        presence['email_gui'] = re.compile("^\s*GUI:")
        presence['silent']    = re.compile("(?:CVS|SVN|GIT|SCM).?SILENT")
        
        results = defaultdict(list)
        for line in commit.message.split("\n"):
            for (name, regex) in split.iteritems():
                match = re.match( regex, line )
                if match:
                    results[name].append( match.group(1).split(",") )
                    
            for (name, regex) in split.iteritems(): 
                if re.match( regex, line ):
                    results[name] = True
                    
        return results        

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

def get_change_diff( repository, log_arguments ):
    # Prepare to run....
    command = "git show -C --pretty=format:%x00%H%x00 --stdin " + log_arguments
    process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Pass on the commits for it to show...
    for sha1 in repository.commits.keys():
        process.stdin.write(sha1 + "\n")
    process.stdin.close()
    return process
