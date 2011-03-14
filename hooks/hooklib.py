#!/usr/bin/python

import itertools
import logging
import os
import re
import time
import subprocess
import dns.resolver
import smtplib
from datetime import datetime
from collections import defaultdict
from itertools import takewhile
from email.mime.text import MIMEText
from email.header import Header
from email import Charset

import lxml.etree as etree
from lxml.builder import E

class RepoType(object):
    "Enum type - Indicates the type of repository"
    Normal = 1
    Sysadmin = 2
    Website = 3
    Scratch = 4
    Clone = 5

class ChangeType(object):
    "Enum type - indicates the type of change to a ref"
    Update = 1
    Create = 2
    Delete = 3
    Forced = 4

class RefType(object):
    "Enum type - indicates the type of ref in the repository"
    Branch = "branch"
    Tag = "tag"
    Backup = "backup"
    Notes = "notes"
    Unknown = 0

class Repository(object):
    "Represents a repository, and changes made to it"
    EmptyRef = "0000000000000000000000000000000000000000"

    RepoManagementName = "repo-management"
    BaseDir = "/srv/kdegit/repositories/"
    PullBaseUrlHttp = "http://anongit.kde.org/"
    PullBaseUrlGit = "git://anongit.kde.org/"
    PushBaseUrl = "git@git.kde.org:"

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
            self.management_directory = os.getenv('HOME') + "/" + Repository.RepoManagementName

        # Set path and id....
        path_match = re.match("^"+Repository.BaseDir+"(.+).git$", os.getcwd())
        self.path = path_match.group(1)
        self.uid = self.__get_repo_id()
        self.__write_metadata()

        # Determine types....
        self.repo_type = self.__get_repo_type()
        self.ref_type = self.__get_ref_type()
        self.change_type = self.__get_change_type()
        ref_name_match = re.match("^refs/(.+?)/(.+)$", self.ref)
        self.ref_name = ref_name_match.group(2)

        # Final initialisation
        self.__build_commits()

        # Ensure emails get done using the charset encoding method we want, not what Python thinks is best....
        Charset.add_charset("utf-8", Charset.QP, Charset.QP)

    def backup_ref(self):

        """Backup the git refs."""

        # Back ourselves up!
        command = "git update-ref refs/backups/{0}-{1}-{2} {3}".format(
            self.ref_type, self.ref_name, int( time.time() ), self.old_sha1 )
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    def __build_commits(self):
        # Build the revision span git will use to help build the revision list...
        if self.change_type == ChangeType.Delete:
            return
        elif self.change_type == ChangeType.Create:
            revision_span = self.new_sha1
        else:
            merge_base = read_command( 'git merge-base {0} {1}'.format(
                self.new_sha1, self.old_sha1) )
            revision_span = "{0}..{1}".format(merge_base, self.new_sha1)

        # Get the list of revisions
        command = "git rev-parse --not --all | grep -v {0} | git rev-list --reverse --stdin {1}"
        command = command.format(self.old_sha1, revision_span)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        revisions = process.stdout.readlines()

        # If we have no revisions... don't continue
        if not revisions:
            return
            
        # Build the git pretty format + regex.
        l = (
             ('CH' , ('%H%n',  '(?P<sha1>.+)\n')),
             ('AN' , ('%an%n', '(?P<author_name>.+)\n')),
             ('AE' , ('%ae%n', '(?P<author_email>.+)\n')),
             ('D'  , ('%at%n', '(?P<date>.+)\n')),
             ('CN' , ('%cn%n', '(?P<committer_name>.+)\n')),
             ('CE' , ('%ce%n', '(?P<committer_email>.+)\n')),
             ('MSG', ('%B%xff','(?P<message>(.|\n)+)\xff(\n*)(\x00*)(?P<files_changed>(.|\n)*)'))
            )

        pretty_format_data = (': '.join((outer, inner[0])) for outer, inner in l)
        pretty_format = '%xfe%xfa%xfc' + ''.join(pretty_format_data)

        re_format_data = (': '.join((outer, inner[1])) for outer, inner in l)
        re_format = '^' + ''.join(re_format_data) + '$'

        # Extract information about commits....
        command = "git show --stdin --name-status -z --pretty=format:'{0}'".format(pretty_format)
        process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Pass on the commits for it to show, and read in all information
        for sha1 in revisions:
            process.stdin.write(sha1)
        process.stdin.close()
        output = process.stdout.read()

        # Parse time!
        split_out = output.split("\xfe\xfa\xfc")
        split_out.remove("")
        for commit_data in split_out:
            match = re.match(re_format, commit_data, re.MULTILINE)
            commit = Commit(self, match.groupdict())
            self.commits[ commit.sha1 ] = commit

        # Extract the commit descriptions....
        command = "xargs git describe --always"
        process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(''.join(revisions))
        descriptions = stdout.split('\n')
        for rev,desc in itertools.izip(revisions, descriptions):
            self.commits[ rev.strip() ].description = desc.strip()

    def __write_metadata(self):

        """Write repository metatdata."""

        clone_url = os.path.join(os.getenv('GIT_DIR'), 'cloneurl')

        with open(clone_url, "w") as metadata:

            metadata.write( "Pull (read-only): " + Repository.PullBaseUrlGit + self.path + "\n" )
            metadata.write( "Pull (read-only): " + Repository.PullBaseUrlHttp + self.path + "\n" )
            metadata.write( "Pull+Push (read+write): " + Repository.PushBaseUrl + self.path + "\n" )

    def __get_repo_id(self):
        base = os.getenv('GIT_DIR')
        # Look for kde-repo-nick, then kde-repo-uid and finally generate one if we find neither....
        if not os.path.exists(base + "/kde-repo-uid"):
            repo_uid = read_command( "echo \"$GIT_DIR `date -R`\" | sha1sum | cut -c -8" )

            with open(base + "/kde-repo-uid", "w") as uid_file:
                uid_file.write(repo_uid + "\n")

        if not os.path.exists(base + "/kde-repo-nick"):
            with open(base + "/kde-repo-nick", "w") as uid_file:
                uid_file.write(self.path + "\n")

        if os.path.exists(base + "/kde-repo-nick"):
            repo_id_file = base + "/kde-repo-nick"
        else:
            repo_id_file = base + "/kde-repo-uid"

        with open(repo_id_file, "r") as repo_id:
            rid = repo_id.readline().strip()

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

class CommitAuditor(object):

    "Performs all audits on commits"

    def __init__(self, repository):

        self.repository = repository

        self.__failed = False

        self.__logger = logging.getLogger("auditor")
        self.__logger.setLevel(logging.ERROR)

        formatter = logging.Formatter("Audit failure - %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.__logger.addHandler(handler)

        self.__setup_filenames()

    def __log_failure(self, commit, message):

        log_message = "Commit {0} - {1}".format(commit, message)
        self.__logger.critical(log_message)
        self.__failed = True

    def __setup_filenames(self):
        self.filename_limits = []

        configuration_file = os.path.join(self.repository.management_directory,
                                          "config/blockedfiles.cfg")

        with open(configuration_file) as configuration:

            for line in configuration:
                regex = line.strip()

                # Skip comments and blank lines
                if regex.startswith("#") or not regex:
                    continue

                restriction = re.compile(regex)
                if restriction:
                    self.filename_limits.append( restriction )

    @property
    def audit_failed(self):

        """Whether the audit failed (True) or passed (False)."""

        return self.__failed

    def audit_eol(self):

        """Audit the commit for proper end-of-line characters.

        The UNIX type EOL is the only allowed EOL character."""

        # Regex's....
        re_commit = re.compile("^\x00(.+)\x00$")
        re_filename = re.compile("^diff --(cc |git a\/.+ b\/)(.+)$")
        blocked_eol = re.compile(r"(?:\r\n|\n\r|\r)$")

        # Do EOL audit!
        process = get_change_diff( self.repository, "-C -p" )
        for line in process.stdout:
            commit_change = re.match( re_commit, line )
            if commit_change:
                commit = commit_change.group(1)
                continue

            file_change = re.match( re_filename, line )
            if file_change:
                filename = file_change.group(2)
                eol_violation = False
                continue

            # Unless they added it, ignore it
            if not line.startswith("+"):
                continue

            if re.search( blocked_eol, line ) and not eol_violation:
                # Failure has been found... handle it
                eol_violation = True
                self.__log_failure(commit, "End Of Line Style - " + filename);

    def audit_filename(self):

        """Audit the file names in the commit."""

        for commit in self.repository.commits.values():
            for filename in commit.files_changed:
                for restriction in self.filename_limits:
                    if re.search(restriction, filename):
                        self.__log_failure(commit.sha1, "File Name - " + filename)

    def audit_metadata(self):

        """Audit commit metadata.

        Invalid hostnames such as localhost or (none) will be caught by this
        auditor. This will ensure that invalid email addresses or users will not
        show up in commits."""

        # Iterate over commits....
        disallowed_domains = ["localhost", "localhost.localdomain", "(none)"]
        for commit in self.repository.commits.values():
            for email_address in [ commit.committer_email, commit.author_email ]:
                # Extract the email address, and reject them if extraction fails....
                extraction = re.match("^(\S+)@(\S+)$", email_address)
                if not extraction:
                    self.__log_failure(commit.sha1, "Email Address - " + email_address)
                    continue

                # Don't allow domains which are disallowed...
                domain = extraction.group(2)
                if domain in disallowed_domains:
                    self.__log_failure(commit.sha1, "Email Address - " + email_address)
                    continue

                # Ensure they have a valid MX/A entry in DNS....
                try:
                    dns.resolver.query(domain, "MX")
                except (dns.resolver.NoAnswer, dns.exception.Timeout, dns.name.EmptyLabel):
                    try:
                        dns.resolver.query(domain, "A")
                    except (dns.resolver.NoAnswer, dns.exception.Timeout, dns.name.EmptyLabel):
                        self.__log_failure(commit.sha1, "Email Address - " + email_address)
                except dns.resolver.NXDOMAIN:
                    self.__log_failure(commit.sha1, "Email Address - " + email_address)

class CiaNotifier(object):
    "Notifies CIA of changes to a repository"

    MESSAGE = E.message
    GENERATOR = E.generator
    SOURCE = E.source
    TIMESTAMP = E.timestamp
    BODY = E.body
    COMMIT = E.commit

    def __init__(self, repository):

        # Attributes needed for XML generation

        self._generator = self._create_generator_tree()

        self.repository = repository
        self.smtp = smtplib.SMTP()
        self.smtp.connect()

    def __del__(self):
        self.smtp.quit()

    def _create_generator_tree(self):

        """Generate the non-variant part of the XML message sent to CIA."""

        name = E.name("KDE CIA Python client")
        version = E.version("1.00")
        url = E.url("http://projects.kde.org/repo-management")

        generator = self.GENERATOR(name, version, url)

        return generator

    def notify(self):

        """Send a notification to CIA."""

        # Iterate and send....
        for commit in self.repository.commits.values():
            self.__send_cia(commit)

    def __send_cia(self, commit):

        """Send the commmit notification to CIA.

        The message is created incrementally using lxml's "E" builder.

        """

        # Build the <files> section for the template...
        files = E.files()

        commit_msg = commit.message.strip()
        commit_msg = re.sub(r'[\x00-\x09\x0B-\x1f\x7f-\xff]', '', commit_msg)

        for filename in commit.files_changed:

            file_element = E.file(filename)
            files.append(file_element)

        # Build the message
        cia_message = self.MESSAGE()
        cia_message.append(self._generator)

        source = self.SOURCE(E.project("KDE"))
        source.append(E.module(self.repository.path))
        source.append(E.branch(self.repository.ref_name))

        cia_message.append(source)
        cia_message.append(self.TIMESTAMP(commit.date))

        body = self.BODY()

        commit_data = self.COMMIT()
        commit_data.append(E.author(commit.author_name))
        commit_data.append(E.revision(commit.description))
        commit_data.append(files)
        commit_data.append(E.log(commit_msg))
        commit_data.append(E.url(commit.url))

        body.append(commit_data)
        cia_message.append(body)

        # Convert to a string
        commit_xml = etree.tostring(cia_message)

        # Craft the email....
        message = MIMEText( commit_xml, 'xml' )
        message['Subject'] = "DeliverXML"
        message['From'] = "sysadmin@kde.org"
        message['To'] = "cia@cia.vc"

        # Send email...
        self.smtp.sendmail("sysadmin@kde.org", ["cia@cia.vc"],
                           message.as_string())

class EmailNotifier(object):
    "Notifies a specified email address of changes to a repository"

    def __init__(self, repository):

        self.repository = repository

        svnpath = repository.management_directory + "/repo-configs/email/" + repository.path + ".git/svnpath"
        with open(svnpath, "r") as svnpath_file:
            self.directory_prefix = svnpath_file.readline().strip()

        # Add trailing path separator if needed.
        if not self.directory_prefix.endswith(os.path.sep):
            self.directory_prefix += os.path.sep

        self.smtp = smtplib.SMTP()
        self.smtp.connect()

    def __del__(self):
        self.smtp.quit()

    @property
    def notification_address(self):

        """The notification address mails should be sent to."""

        if self.repository.repo_type == RepoType.Sysadmin:
            return "sysadmin-svn@kde.org"
        else:
            return "kde-commits@kde.org"

    def notify(self):

        """Send an email notification of the commit."""

        # Retrieve diff-stats...
        diffinfo = defaultdict(list)
        process = get_change_diff( self.repository, "--numstat" )
        for line in process.stdout:
            commit_change = re.match( "^\x00(.+)\x00$", line)
            if commit_change:
                commit = commit_change.group(1)
                continue

            diff_line = re.match("(-|[0-9]+)\W+(-|[0-9]+)\W+(.+)$", line)
            if diff_line:
                file_info = (diff_line.group(3), diff_line.group(1),
                             diff_line.group(2))
                diffinfo[commit].append( file_info )

        # We will incrementally send the mails as we gather up the diffs....
        process = get_change_diff( self.repository, "-p" )
        diff = list()
        for line in process.stdout:
            commit_change = re.match( "^\x00(.+)\x00$", line )
            if commit_change and diff:
                self.__send_email(self.repository.commits[commit], diff,
                                  diffinfo[commit])
                commit = ""
                diff = list()

            if commit_change:
                commit = commit_change.group(1)
                continue

            diff.append( unicode(line, "utf-8", 'replace') )

        if commit:
            self.__send_email(self.repository.commits[commit], diff,
                              diffinfo[commit])

    def __send_email(self, commit, diff, diffinfo):

        """Send an email of the commit."""

        # Check for problems in this commit
        checker = CommitChecker(commit, diff)
        checker.check_commit_problems()

        # Build keywords
        keyword_info = self.__parse_keywords(commit)

        # Build list for X-Commit-Directories...
        commit_directories = [os.path.dirname(filename) for filename in commit.files_changed]

        # Remove all duplicates...
        commit_directories = list( set(commit_directories) )
        full_commit_dirs = [self.directory_prefix + cdir for cdir in commit_directories]

        # Build a list of addresses to Cc,
        cc_addresses = keyword_info['email_cc'] + keyword_info['email_cc2']

        # Add the committer to the Cc in case problems have been found
        if checker.license_problem or checker.commit_problem:
            cc_addresses.append(commit.committer_email)

        if keyword_info['email_gui']:
            cc_addresses.append( 'kde-doc-english@kde.org' )

        # Build the subject....
        if len(commit_directories) == 1:
            lowest_common_path = commit_directories[0]
        else:
            # This works on path segments rather than char-by-char as os.path.commonprefix does
            # and hence avoids problems when multiple directories at the same level start with
            # the same sequence of characters.
            by_levels = zip( *[p.split(os.path.sep) for p in commit_directories] )
            equal = lambda name: all( n == name[0] for n in name[1:] )
            lowest_common_path = os.path.sep.join(x[0] for x in takewhile( equal, by_levels ))

        if not lowest_common_path:
            lowest_common_path = '/'

        repo_path = self.repository.path
        if self.repository.ref_name != "master":
            repo_path += "/" + self.repository.ref_name
        short_msg = commit.message.splitlines()[0]
        subject = unicode("[{0}] {1}: {2}").format(repo_path, lowest_common_path, short_msg)

        if keyword_info['silent']:
            subject += unicode(' (silent)')

        if keyword_info['notes']:
            subject += unicode(' (silent,notes)')

        # Build up the body of the message...
        firstline = unicode("Git commit {0} by {1}.").format( commit.sha1,
                                                   commit.committer_name )
        if commit.author_name != commit.committer_name:
            firstline += " on behalf of " + commit.author_name

        committed_on = commit.datetime.strftime("Committed on %d/%m/%Y at %H:%M.")

        pushed_by = "Pushed by {0} into {1} '{2}'.".format(
            self.repository.push_user, self.repository.ref_type,
            self.repository.ref_name)

        summary = [firstline, committed_on, pushed_by, '', commit.message.strip(), '']
        for info in diffinfo:
            filename, added, removed = info
            notes = ' '.join(checker.commit_notes[filename])
            file_change = commit.files_changed.get(filename, None)

            if file_change is None:
                file_change = "I"

            data = "{0:<2} +{1:<4} -{2:<4} {3}     {4}".format( file_change,
                added, removed, filename, notes )
            summary.append( data )
        if checker.license_problem:
            summary.append( "\nThe files marked with a * at the end have a non valid "
                "license. Please read: http://techbase.kde.org/Policies/Licensing_Policy "
                "and use the headers which are listed at that page.\n")
        if checker.commit_problem:
            summary.append( "\nThe files marked with ** at the end have a problem. "
                "either the file contains a trailing space or the file contains a call to "
                "a potentially dangerous code. Please read: "
                "http://community.kde.org/Sysadmin/CommitHooks#Email_notifications "
                "Either fix the trailing space or review the dangerous code.\n");
        summary.append( "\n" + commit.url + "\n" )

        body = '\n'.join( summary )
        if diff and len(diff) < 8000:
            body += "\n" + unicode('', "utf-8").join(diff)

        # Build from address as Python gets it wrong....
        from_name = Header( commit.committer_name ).encode()

        # Handle the normal mailing list mails....
        message = MIMEText( body.encode("utf-8"), 'plain', 'utf-8' )
        message['Subject'] = Header( subject.encode("utf-8"), 'utf-8', 76, 'Subject' )
        message['From']    = unicode("{0} <{1}>").format(
                from_name, commit.committer_email )
        message['To']      = Header( self.notification_address )
        if cc_addresses:
            message['Cc']      = Header( ','.join(cc_addresses) )
        message['X-Commit-Ref']         = Header( self.repository.ref_name )
        message['X-Commit-Project']     = Header( self.repository.path )
        message['X-Commit-Folders']     = Header( ' '.join(commit_directories) )
        message['X-Commit-Directories'] = Header( "(0) " + ' '.join(full_commit_dirs) )

        # Send email...
        to_addresses = cc_addresses + [self.notification_address]
        self.smtp.sendmail(commit.committer_email, to_addresses, message.as_string())

        # Handle bugzilla....
        bugs_changed = keyword_info['bug_fixed'] + keyword_info['bug_cc']
        for bug in bugs_changed:
            bug_body = list()
            bug_body.append( "@bug_id = " + bug )
            if bug in keyword_info['bug_fixed']:
                bug_body.append( "@bug_status = RESOLVED" )
                bug_body.append( "@resolution = FIXED" )
                if keyword_info['fixed_in']:
                    bug_body.append("@cf_versionfixedin = " + keyword_info['fixed_in'][0])
            bug_body.append( '' )
            bug_body.append( '\n'.join( summary ) )

            body = unicode('\n', "utf-8").join( bug_body )
            message = MIMEText( body.encode("utf-8"), 'plain', 'utf-8' )
            message['Subject'] = Header( subject.encode("utf-8"), 'utf-8', 76, 'Subject' )
            message['From']    = unicode("{0} <{1}>").format(
                from_name, commit.committer_email )
            message['To']      = Header( "bug-control@bugs.kde.org" )
            self.smtp.sendmail(commit.committer_email, ["bug-control@bugs.kde.org"],
                               message.as_string())

        # Handle reviewboard
        for review in keyword_info['review']:
            # Call the helper program
            cmdline = self.repository.management_directory + "/hooks/update_review.py {0} {1} '{2}'"
            cmdline = unicode(cmdline, "utf-8")
            cmdline = cmdline.format(review, commit.sha1, commit.author_name)
            # Fork into the background - we don't want it to block the hook
            subprocess.Popen(cmdline, shell=True)

    def __parse_keywords(self, commit):

        """Parse special keywords in commits to determine further post-commit
        actions."""

        split = dict()
        split['bug_fixed'] = re.compile("^\s*(?:BUGS?|FEATURE)[:=]\s*(\d{4,10})")
        split['bug_cc']    = re.compile("^\s*CCBUGS?[:=]\s*(\d{4,10})")
        split['email_cc']  = re.compile("^\s*CC[-_]?MAIL[:=]\s*(.*)")
        split['email_cc2'] = re.compile("^\s*C[Cc][:=]\s*(.*)")
        split['fixed_in']  = re.compile("^\s*FIXED[-_]?IN[:=]\s*(\d[\d\.-]*)")
        split['review']    = re.compile("^\s*REVIEWS?[:=]\s*(\d{1,10})")

        presence = dict()
        presence['email_gui'] = re.compile("^\s*GUI:")
        presence['silent']    = re.compile("(?:CVS|SVN|GIT|SCM).?SILENT")
        presence['notes']     = re.compile("(?:Notes added by 'git notes add'|Notes removed by 'git notes remove')")

        results = defaultdict(list)
        for line in commit.message.split("\n"):
            for (name, regex) in split.iteritems():
                match = re.match( regex, line )
                if match:
                    results[name] += [result.strip() for result in match.group(1).split(",")]

            for (name, regex) in presence.iteritems():
                if re.match( regex, line ):
                    results[name] = True

        return results

class Commit(object):

    "Represents a git commit"

    UrlPattern = "http://commits.kde.org/{0}/{1}"

    def __init__(self, repository, commit_data):
        self.repository = repository
        self._commit_data = commit_data
        self._raw_properties = ["files_changed", "datetime"]

        # Convert the date into something usable...
        self._commit_data["datetime"] = datetime.fromtimestamp( float(self._commit_data["date"]) )

        # Create file changed list and replace the original value
        clean_list = re.split("\x00", self._commit_data["files_changed"])
        files = clean_list[1::2]
        changes = clean_list[::2]
        self._commit_data["files_changed"] = dict(itertools.izip(files,changes))
        if "" in self.files_changed:
            del self.files_changed[""]

    def __getattr__(self, key):

        if key not in self._commit_data:
            raise AttributeError
        if key in self._raw_properties:
            return self._commit_data[key]

        value = self._commit_data[key]
        return unicode(value, "utf-8")

    def __repr__(self):
        return str(self._commit_data)

    @property
    def url(self):

        """The URL of the commit at commits.kde.org."""

        return Commit.UrlPattern.format( self.repository.uid, self.sha1 )


class CommitChecker(object):

    """Checker class for commit information such as licenses, or potentially
    unsafe practices."""

    def __init__(self, commit, diff):

        self.commit = commit
        self.diff = diff
        self._license_problem = False
        self._commit_problem = False
        self._commit_notes = defaultdict(list)

    @property
    def license_problem(self):
        return self._license_problem

    @property
    def commit_problem(self):
        return self._commit_problem

    @property
    def commit_notes(self):
        return self._commit_notes

    def check_commit_license(self, filename, text):

        problemfile = False
        gl = qte = license = wrong = ""
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
            self._license_problem = True
            problemfile = True

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
        if re.search("MERCHANTABILITY( AND|| or) FITNESS FOR A PARTICULAR PURPOSE", text) and not re.search("GPL", license):
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
            self._license_problem = True
            problemfile = True

        # Don't bother with trivial files.
        if not license and len(text) < 128:
            license = "Trivial file"

        # About every license has this clause; but we've failed to detect which type it is.
        if not license and re.search("This (software|package)( is free software and)? is provided ",
                                     text, re.IGNORECASE):
            license = "Unknown license"
            self._license_problem = True
            problemfile = True

        # Either a missing or an unsupported license
        if not license:
            license = "UNKNOWN"
            self._license_problem = True
            problemfile = True

        license = license.strip()

        if license:
                self._commit_notes[filename].append( (" "*4) + "[License: " + license + "]")
        if license and problemfile:
                self._commit_notes[filename].append( " *")

    def check_commit_problems(self):

        """Check for potential problems in a commit."""

        # Unsafe regex checks...
        unsafe_matches = list()
        unsafe_matches.append( "\b(KRun::runCommand|K3?ShellProcess|setUseShell|setShellCommand)\b\s*[\(\r\n]" )
        unsafe_matches.append( "\b(system|popen|mktemp|mkstemp|tmpnam|gets|syslog|strptime)\b\s*[\(\r\n]" )
        unsafe_matches.append( "(scanf)\b\s*[\(\r\n]" )

        # Retrieve the diff and do the problem checks...
        filename = ""
        filediff = list()
        for line in self.diff:
            file_change = re.match( "^diff --(cc |git a\/.+ b\/)(.+)$", line )
            if file_change:
                # Are we changing file? If so, we have the full diff, so do a license check....
                if filename != "" and self.commit.files_changed[ filename ] == 'A':
                    self.check_commit_license(filename, ''.join(filediff))

                filediff = list()
                filename = file_change.group(2)
                continue

            # Diff headers are bogus
            if re.match("@@ -\d+,\d+ \+\d+ @@", line):
                filediff = list()
                continue

            # Do an incremental check for *.desktop syntax errors....
            if re.search("\.desktop$", filename) and re.search("[^=]+=.*[ \t]$", line) and not re.match("^#", line):
                self._commit_notes[filename].append( "[TRAILING SPACE] **" )
                self._commit_problem = True

            # Check for things which are unsafe...
            safety_check = line

            #TODO: The following regexps need to be ported to a Python syntax
            #$current =~ s/\"[^\"]*\"//g;
            #$current =~ s/\/\*.*\*\///g;
            #$current =~ s,//.*,,g;
            for safety_match in unsafe_matches:
                match = re.match(safety_match, safety_check)
                if match:
                    self._commit_notes[filename].append( "[POSSIBLY UNSAFE: "
                                                        + match.group(1) + "] **")
                    self._commit_problem = True

            # Store the diff....
            filediff.append(line)

        if filename != "" and self.commit.files_changed[ filename ] == 'A':
            self.check_commit_license(filename, ''.join(filediff))

def read_command( command ):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return process.stdout.readline().strip()

def get_change_diff( repository, log_arguments ):
    # Prepare to run....
    command = "git show --pretty=format:%x00%H%x00 --stdin " + log_arguments
    process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Pass on the commits for it to show...
    for sha1 in repository.commits:
        process.stdin.write(sha1 + "\n")
    process.stdin.close()
    return process
