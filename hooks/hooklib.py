#!/usr/bin/python

import itertools
import logging
import os
import re
import io
import time
import yaml
import subprocess
import dns.resolver
import smtplib
import scandir
import operator
from datetime import datetime
from collections import defaultdict
from itertools import takewhile
from email.mime.text import MIMEText
from email.header import Header
from email import Charset

import mimetypes
from ordereddict import OrderedDict
import lxml.etree as etree
from lxml.builder import E

class RepoType(object):
    "Enum type - Indicates the type of repository"
    Normal = 1
    Sysadmin = 2
    Website = 3
    Scratch = 4
    Clone = 5
    Others = 6

class ChangeType(object):
    "Enum type - indicates the type of change to a ref"
    Update = 1
    Create = 2
    Delete = 3
    Forced = 4

class RefType(object):
    "Enum type - indicates the type of ref in the repository"
    Branch = "branch"
    WorkBranch = "work-branch"
    Tag = "tag"
    Backup = "backup"
    Notes = "notes"
    MergeRequest = "merge-requests"
    Internal = "internal"
    Unknown = 0

class Repository(object):
    "Represents a repository, and changes made to it"
    EmptyRef = "0000000000000000000000000000000000000000"

    RepoManagementName = "repo-management"
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
        self.commits = OrderedDict()

        # Find our configuration directory....
        if os.getenv('REPO_MGMT'):
            self.management_directory = os.getenv('REPO_MGMT')
        else:
            self.management_directory = os.getenv('HOME') + "/" + Repository.RepoManagementName

        # Set the repository path...
        path_match = re.match("^"+Repository.BaseDir+"(.+).git$", os.getcwd())
        self.path = self.virtual_path = path_match.group(1)

        # Determine if this repository uses Gitlab hashed storage
        # If it is, then some adjustment to the above is required
        if '@hashed/' in self.path:
            # Retrieve the human usable path from Gitlab
            command = ["git", "config", "--local", '--get', 'gitlab.fullpath']
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            self.path = self.virtual_path = process.stdout.readline().strip()

        # Determine types....
        self.repo_type = self.__get_repo_type()
        self.ref_type = self.__get_ref_type()
        self.change_type = self.__get_change_type()
        ref_name_match = re.match("^refs/(.+?)/(.+)$", self.ref)
        self.ref_name = ref_name_match.group(2)

        # Determine commit type for the top most commit
        if self.change_type == ChangeType.Delete:
            self.commit_type = "commit"
        else:
            command = ["git", "cat-file", "-t", self.new_sha1]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            self.commit_type = process.stdout.readline().strip()

        # Final initialisation
        self.__build_commits()

        # Ensure emails get done using the charset encoding method we want, not what Python thinks is best....
        Charset.add_charset("utf-8", Charset.QP, Charset.QP)

    def backup_ref(self):

        """Backup the git refs."""

        # Back ourselves up!
        backup_ref="refs/backups/{0}-{1}-{2}".format(self.ref_type, self.ref_name, int( time.time() ))
        command = ("git", "update-ref", backup_ref, self.old_sha1)
        process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

    def __build_commits(self):
        # Build the revision span git will use to help build the revision list...
        if self.change_type == ChangeType.Delete:
            return
        elif self.change_type == ChangeType.Create:
            revision_span = self.new_sha1
        else:
            merge_base = read_command(('git', 'merge-base', self.new_sha1, self.old_sha1))
            revision_span = "{0}..{1}".format(merge_base, self.new_sha1)

        # Determine what command we need to use to fetch the list of revisions
        #
        # To start, the merge request refs, along with the keep-around refs used by Gitlab for it's operations are both ignored and not considered to be already in the repository
        # We also ignore work branches, as these are subject to force pushes and are considered to be a work in progress and not yet part of a release
        #
        # This is necessary to ensure hooks fire when these changes are merged into the repository and become part of a release branch
        revisionsCommand = "git for-each-ref --format='%(refname) ^%(objectname)' | grep -v -E '^refs/(merge-requests|keep-around)/' | grep -v '^refs/heads/work/' | cut -d ' ' -f 2 | sort -u | grep -v {0} | git rev-list --reverse --stdin {1}"

        # Now we have the command, actually get the list of revisions we are to be working on!
        command = revisionsCommand.format(self.old_sha1, revision_span)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        revisions = process.stdout.readlines()

        # If we have no revisions... don't continue
        if not revisions:
            return

        # Build the git pretty format + regex.
        l = (
             ('CH' , ('%H%n',  '(?P<sha1>.+)\n')),
             ('CP' , ('%P%n',  '(?P<parents>.*)\n')),
             ('AN' , ('%an%n', '(?P<author_name>.*)\n')),
             ('AE' , ('%ae%n', '(?P<author_email>.*)\n')),
             ('D'  , ('%ct%n', '(?P<date>.+)\n')),
             ('CN' , ('%cn%n', '(?P<committer_name>.*)\n')),
             ('CE' , ('%ce%n', '(?P<committer_email>.*)\n')),
             ('MSG', ('%B%xff','(?P<message>(.|\n)*)\xff(\n*)(\x00*)(?P<files_changed>(.|\n)*)'))
            )

        pretty_format_data = (': '.join((outer, inner[0])) for outer, inner in l)
        pretty_format = '%xfe%xfa%xfc' + ''.join(pretty_format_data)

        re_format_data = (': '.join((outer, inner[1])) for outer, inner in l)
        re_format = '^' + ''.join(re_format_data) + '$'

        # Extract information about commits....
        command = "git show --stdin --name-status -z -C --pretty=format:'{0}'".format(pretty_format)
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
        command = ("xargs", "git", "describe", "--always")
        process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(''.join(revisions))
        descriptions = stdout.split('\n')
        for rev,desc in itertools.izip(revisions, descriptions):
            self.commits[ rev.strip() ].description = desc.strip()

        # Retrieve number of changed lines, and merge in the type of change
        process = get_change_diff( self, ["--numstat", "-z"] )
        output = process.stdout.read()
        for sha1, information in re.findall("\xff([0-9a-f]+)\xff(?:\n|\x00|)([^\xff]*)(?:\x00|)", output):
            stats = defaultdict(dict)
            file_stats = re.findall("([0-9]+|-)\t([0-9]+|-)\t(?:(?=\x00)\x00([^\x00]+)\x00|)([^\x00]+)", information)
            for added, removed, source_file, changed_file in file_stats:
                if source_file:
                    stats[changed_file]["source"] = unicode(source_file, "utf-8", "replace")
                stats[changed_file]["added"] = added
                stats[changed_file]["removed"] = removed

            # Parse the way files changed
            status = re.findall("\x00?(A|C|D|M|R|T|U|X)(?:(?<=C|R)([0-9]+)\x00([^\x00]+)|)\x00([^\x00]+)?", self.commits[sha1].files_changed)
            for change, similarity, source_file, changed_file in status:
                stats[changed_file]["change"] = change
                if source_file:
                    stats[changed_file]["similarity"] = similarity

            for filename, data in stats.iteritems():
                if "source" in data.keys() and "similarity" not in data.keys():
                    del data["source"]

            # Remove items with invalid data (ie. number of changed lines but no status)
            data = OrderedDict((unicode(filename, "utf-8", "replace"), data) for filename, data in sorted(stats.items(), key=operator.itemgetter(0)) if "change" in data and "added" in data)
            self.commits[sha1].files_changed = data

    def __get_repo_type(self):
        sysadmin_repos = ["gitolite-admin"]

        # What type of repo have we got???
        if self.path in sysadmin_repos:
            return RepoType.Sysadmin
        elif re.match("^websites/(.+)$", self.path):
            return RepoType.Website
        elif re.match("^scratch/(.+)$", self.path):
            return RepoType.Scratch
        elif re.match("^clones/(.+)$", self.path):
            return RepoType.Clone
        elif re.match("^others/(.+)$", self.path):
            return RepoType.Others
        else:
            return RepoType.Normal

    def __get_ref_type(self):
        # What type is the ref being changed?
        if re.match("^refs/heads/work/(.+)$", self.ref):
            return RefType.WorkBranch
        if re.match("^refs/heads/(.+)$", self.ref):
            return RefType.Branch
        elif re.match("^refs/tags/(.+)$", self.ref):
            return RefType.Tag
        elif re.match("^refs/backups/(.+)$", self.ref):
            return RefType.Backup
        elif re.match("^refs/notes/(.+)$", self.ref):
            return RefType.Notes
        elif re.match("^refs/merge-requests/(.+)$", self.ref):
            return RefType.MergeRequest
        elif re.match("^refs/keep-around/(.+)$", self.ref):
            return RefType.Internal
        else:
            return RefType.Unknown

    def __get_change_type(self):
        # Determine the merge base, to detect if we are experiencing a force or normal push....
        if( self.old_sha1 != self.EmptyRef and self.new_sha1 != self.EmptyRef ):
            merge_base = read_command(('git', 'merge-base', self.old_sha1, self.new_sha1))

        # What type of change is happening here?
        if self.old_sha1 == self.EmptyRef and self.new_sha1 != self.EmptyRef:
            return ChangeType.Create
        elif self.new_sha1 == self.EmptyRef:
            return ChangeType.Delete
        elif self.old_sha1 != merge_base:
            return ChangeType.Forced
        else:
            return ChangeType.Update

class RepositoryMetadataLoader(object):
    # Store of repositories we know about
    KnownRepos = {}

    # Load the projects from the YAML file
    def loadProjectsFromTree( self, directoryPath ):
        # Get a listing of everything in this directory
        filesPresent = scandir.scandir(directoryPath)
        # We will recurse into directories beneath this one
        # If there is a metadata.yaml file present, we will parse it to determine if this is a repository we need to register
        for entry in filesPresent:
            # Is it a symlink? We always ignore these
            if entry.is_symlink():
                continue

            # Is it a directory we need to recurse into?
            if entry.is_dir():
                self.loadProjectsFromTree(entry.path)
                continue

            # If the filename isn't metadata.yaml, ignore it
            if entry.name != 'metadata.yaml':
                continue

            # Load the metadata.yaml file and create a project from it
            projectMetadataFile = io.open(entry.path, 'r', encoding='utf-8')
            # Parse the YAML file
            projectMetadata = yaml.load(projectMetadataFile)
            # Is it a repository - ie. something we need to know about?
            if not projectMetadata['hasrepo'] or not projectMetadata['repoactive']:
                continue

            # Split the repository name out
            splitPath = projectMetadata['projectpath'].split('/')
            projectName = splitPath[-1]

            # Now that we have everything we need add it to our list of repos
            self.KnownRepos[ projectName ] = projectMetadata

class CommitAuditor(object):

    """Performs all audits on commits"""

    ALLOWED_EOL_MIMETYPES = set(("text/vcard", "text/x-vcard", "text/directory", "image/svg", "image/x-portable-graymap"))
    ALLOWED_EOL_EXTENSIONS = set(("vcf", "vcf.ref", "svg", "pdf", "pgm", "fits"))
 
    "Whitelist of names which will always be accepted"
    FullNameWhitelist = [
        'Chaitanya'
    ]
    """
    List of repositories that use web merging on GitHub pull requests
    and cause 'GitHub' usernames
    """
    GitHubPRWhitelist = [
        'websites/inqlude',
        'websites/inqlude-data',
        'heaptrack'
    ]

    def __init__(self, repository):
        self.repository = repository
        self.__failed = False

        self.__logger = logging.getLogger("auditor")
        self.__logger.setLevel(logging.WARNING)

        formatter = logging.Formatter("%(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.__logger.addHandler(handler)

        self.__setup_filenames()

    def __log_failure(self, commit, message):
        log_message = unicode("Audit failure - Commit {0} - {1}", "utf-8").format(commit, message)
        self.__logger.critical(log_message)
        self.__failed = True

    def __log_warning(self, commit, message):
        log_message = unicode("Audit warning - Commit {0} - {1}", "utf-8").format(commit, message)
        self.__logger.warning(log_message)

    def __setup_filenames(self):
        self.filename_limits = []

        configuration_file = os.path.join(self.repository.management_directory,
                                          "hooks", "blockedfiles.cfg")

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
        re_commit = re.compile("^\xff(.+)\xff$")
        re_filename = re.compile("^diff --(cc |git a\/.+ b\/)(.+)$")
        blocked_eol = re.compile(r"(?:\r\n|\n\r|\r)$")

        # Bool to allow special files such as vcards to bypass the check
        eol_allowed = False


        # Do EOL audit!
        process = get_change_diff( self.repository, ["-p"] )
        for line in process.stdout:
            commit_change = re.match( re_commit, line )
            if commit_change:
                commit = commit_change.group(1)
                continue

            file_change = re.match( re_filename, line )
            if file_change:
                filename = file_change.group(2)
                eol_violation = False
                eol_allowed = False

                # Check if it's an allowed mimetype
                # First - check with the mimetypes system, to see if it can tell
                guessed_type, _ = mimetypes.guess_type(filename)
                if guessed_type in self.ALLOWED_EOL_MIMETYPES:
                    eol_allowed = True
                    continue

                # Second check: by file extension
                # NOTE: This uses the FIRST dot as extension
                splitted_filename = filename.split(os.extsep)
                # Check if there's an extension or not
                # NOTE This assumes that files use dots for extensions only!
                if len(splitted_filename) > 1:
                    extension = splitted_filename[1]
                    if extension in self.ALLOWED_EOL_EXTENSIONS:
                        eol_allowed = True

                continue

            # Unless they added it, ignore it
            if not line.startswith("+"):
                continue

            if re.search( blocked_eol, line ) and not eol_violation:
                # Is this an allowed filename?
                if eol_allowed:
                    continue

                # Failure has been found... handle it
                eol_violation = True
                self.__log_failure(commit, "End of Line Style (non-Unix): " + filename);

    def audit_filename(self):

        """Audit the file names in the commit."""

        for commit in self.repository.commits.values():
            for filename in commit.files_changed:
                if commit.files_changed[ filename ]["change"] not in ["A","R","C"]:
                    continue
                for restriction in self.filename_limits:
                    if re.search(restriction, filename):
                        self.__log_failure(commit.sha1, "Invalid filename: " + filename)

    def audit_names_in_metadata(self):

        """Audit names in commit metadata.

        Names which do not have a first name and a surname are extremely uncommon
        and when present are therefore generally invalid. As we want people to 
        use their actual name when committing we do some checks to make sure
        that what looks like an actual name is present."""

        # Iterate over commits....
        for commit in self.repository.commits.values():
            for name in [ commit.committer_name, commit.author_name ]:
                # Is the name whitelisted?
                if name in self.FullNameWhitelist:
                    continue

                # As a special case, allow the name 'GitHub' for certain repositories
                if name == 'GitHub' and self.repository.path in self.GitHubPRWhitelist:
                    self.__log_warning(commit.sha1, "Commit has username 'GitHub' (web merge of PR); allowing anyway")
                    continue

                # Check to see if the name contains spaces - if not - it is probably misconfigured....
                if " " not in name.strip():
                    self.__log_failure(commit.sha1, "Non-full name: " + name)
                    continue

    def audit_emails_in_metadata(self):

        """Audit commit metadata.

        Invalid hostnames such as localhost or (none) will be caught by this
        auditor. This will ensure that invalid email addresses or users will not
        show up in commits."""

        # Iterate over commits....
        disallowed_domains = ["localhost", "localhost.localdomain", "(none)", "bombardier.com", "rail.bombardier.com"]
        for commit in self.repository.commits.values():
            for email_address in [ commit.committer_email, commit.author_email ]:
                # Extract the email address, and reject them if extraction fails....
                extraction = re.match("^(\S+)@(\S+)$", email_address)
                if not extraction:
                    self.__log_failure(commit.sha1, "Seemingly invalid email address: " + email_address)
                    continue

                # Don't allow domains which are disallowed...
                domain = extraction.group(2)
                if domain in disallowed_domains:
                    self.__log_failure(commit.sha1, "Email address using a blocked domain: " + email_address)
                    continue

                # Ensure they have a valid MX/A entry in DNS....
                try:
                    dns.resolver.query(domain, "MX")
                except (dns.resolver.NoAnswer, dns.exception.Timeout, dns.name.EmptyLabel):
                    try:
                        dns.resolver.query(domain, "A")
                    except (dns.resolver.NoAnswer, dns.exception.Timeout, dns.name.EmptyLabel, dns.resolver.NXDOMAIN):
                        self.__log_failure(commit.sha1, "Email address has an invalid domain : " + email_address)
                except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
                    self.__log_failure(commit.sha1, "Email address has an invalid domain : " + email_address)

    def audit_hashes(self, blocked_list):
        with open(blocked_list, "r") as blockedfile:
            blocked = blockedfile.readlines()

        for sha1 in blocked:
            sha1 = sha1.strip()
            if sha1 in self.repository.commits:
                self.__log_failure(sha1, "Administratively blocked commit: contact sysadmin@kde.org")

class CommitNotifier(object):
    "Contains items needed to send notifications for commits"

    def __init__(self):
        self.smtp = smtplib.SMTP()
        self.smtp.connect()

    def __del__(self):
        self.smtp.quit()

    def notify_email(self, builder, notification_address, diff ):
        # Build list for X-Commit-Directories...
        full_commit_dirs = [cdir for cdir in builder.commit_directories]

        # Build a list of addresses to Cc,
        cc_addresses = builder.keywords['email_cc'] + builder.keywords['email_cc2']
        bcc_addresses = []

        # Add the committer to the Cc in case problems have been found
        if builder.checker and (builder.checker.license_problem or builder.checker.commit_problem):
            cc_addresses.append( builder.commit.committer_email )

        if builder.keywords['email_gui']:
            cc_addresses.append( 'kde-doc-english@kde.org' )

        if builder.repository.repo_type == RepoType.Website:
            bcc_addresses.append( 'scmupdate@olios.kde.org' )

        if builder.repository.path == "websites/ev-kde-org":
            cc_addresses.append( 'kde-ev-board@kde.org' )

        i18nInfraChange = re.compile("(.*)Messages.sh$")
        if any(i18nInfraChange.match(filename) for filename in builder.commit.files_changed):
            cc_addresses.append( 'i18n-infrastructure@kde.org' )

        docbookChange = re.compile("(.*)\.docbook$")
        if any(docbookChange.match(filename) for filename in builder.commit.files_changed):
            cc_addresses.append( 'kde-doc-english@kde.org' )

        body = builder.body
        if diff and len(diff) < 8000:
            body += "\n" + unicode('', "utf-8", 'replace').join(diff)

        # Handle the normal mailing list mails....
        message = MIMEText( body.encode("utf-8"), 'plain', 'utf-8' )
        message['Subject']  = Header( builder.subject, 'utf-8', 76, 'Subject' )
        message['From']     = builder.address_header( builder.commit.committer_name, "null@kde.org" )
        message['To']       = Header( notification_address )
        message['Reply-To'] = builder.address_header( builder.commit.committer_name, builder.commit.committer_email )
        if cc_addresses:
            message['Cc']   = Header( ','.join(cc_addresses) )
        message['X-Commit-Ref']         = Header( builder.repository.ref_name )
        message['X-Commit-Project']     = Header( builder.repository.path )
        message['X-Commit-Folders']     = Header( ' '.join(builder.commit_directories) )
        message['X-Commit-Directories'] = Header( "(0) " + ' '.join(full_commit_dirs) )
        message['X-Commit-ProjectPath'] = Header( builder.repository.virtual_path )

        # Send email...
        to_addresses = cc_addresses + bcc_addresses + [notification_address]
        self.smtp.sendmail("null@kde.org", to_addresses, message.as_string())

    def notify_bugzilla(self, builder):
        commit_regex = re.compile("^\s*((CC)?BUGS?|FEATURE)[:=](.+)\n", re.MULTILINE)
        bugs_changed = builder.keywords['bug_fixed'] + builder.keywords['bug_cc']
        for bug in bugs_changed:
            # Prepare the customised Bugzilla comment
            related_bugs = ["bug " + entry for entry in bugs_changed if entry != bug]
            commit_msg = builder.body
            if related_bugs:
                commit_msg = re.sub(commit_regex, "Related: " + ', '.join(related_bugs) + "\n", commit_msg, 1)
            commit_msg = re.sub(commit_regex, "", commit_msg)

            # Prepare the Bugzilla specific message body portion...
            bug_body = list()
            bug_body.append( "@bug_id = " + bug )
            if bug in builder.keywords['bug_fixed']:
                bug_body.append( "@bug_status = RESOLVED" )
                bug_body.append( "@resolution = FIXED" )
                bug_body.append( "@cf_commitlink = " + builder.commit.url )
                if builder.keywords['fixed_in']:
                    bug_body.append("@cf_versionfixedin = " + builder.keywords['fixed_in'][0])
            bug_body.append( '' )
            bug_body.append( commit_msg )

            body = unicode('\n', "utf-8").join( bug_body )
            message = MIMEText( body.encode("utf-8"), 'plain', 'utf-8' )
            message['Subject'] = Header( builder.subject, 'utf-8', 76, 'Subject' )
            message['From']    = Header( builder.commit.committer_email )
            message['To']      = Header( "bug-control@bugs.kde.org" )
            self.smtp.sendmail(builder.commit.committer_email, ["bug-control@bugs.kde.org"],
                               message.as_string())

            if bug in builder.keywords['bug_fixed']:
                print "Closing bug " + bug
            else:
                print "Posting comment to bug " + bug

    def handler(self, repository):
        # If there are no commits -> nothing to notify on :)
        if len(repository.commits) == 0:
            return

        # We will incrementally notify as we gather up the diffs....
        process = get_change_diff( repository, ["-p"] )
        diff = list()
        for line in process.stdout:
            commit_change = re.match( "^\xff(.+)\xff$", line )
            if commit_change and diff:
                yield(repository.commits[commit], diff)
                commit = ""
                diff = list()

            if commit_change:
                commit = commit_change.group(1)
                continue

            diff.append( unicode(line, "utf-8", 'replace') )

        if commit:
            yield(repository.commits[commit], diff)

class MessageBuilder(object):
    """Creates the components needed to send emails and other notifications"""

    def __init__(self, repository, commit, checker = None, include_url = True):
        self.repository = repository
        self.commit = commit
        self.checker = checker
        self.keywords = defaultdict(list)
        self.include_url = include_url

        # Generate directories affected by the commit
        commit_directories = [os.path.dirname(filename) for filename in commit.files_changed]
        self.commit_directories = list( set(commit_directories) )

    def address_header(self, name, email):
        """Helper function to construct an address header for emails - as Python stuffs it up"""
        fixed_name = Header( name ).encode()
        return unicode("{0} <{1}>").format(fixed_name, email)

    @property
    def subject(self):
        if len(self.commit_directories) == 1:
            lowest_common_path = self.commit_directories[0]
        else:
            # This works on path segments rather than char-by-char as os.path.commonprefix does
            # and hence avoids problems when multiple directories at the same level start with
            # the same sequence of characters.
            by_levels = zip( *[p.split(os.path.sep) for p in self.commit_directories] )
            equal = lambda name: all( n == name[0] for n in name[1:] )
            lowest_common_path = os.path.sep.join(x[0] for x in takewhile( equal, by_levels ))

        if not lowest_common_path:
            lowest_common_path = '/'

        repo_path = self.repository.path
        if self.repository.ref_name != "master":
            repo_path += "/" + self.repository.ref_name
        short_msg = self.commit.message.splitlines()[0]
        subject = unicode("[{0}] {1}: {2}").format(repo_path, lowest_common_path, short_msg)

        if self.keywords['silent']:
            subject += ' (silent)'

        if self.keywords['notes']:
            subject += ' (silent,notes)'
        return subject

    @property
    def body(self):
        commit = self.commit
        firstline = unicode("Git commit {0} by {1}").format( commit.sha1, commit.committer_name )
        if commit.author_name != commit.committer_name:
            firstline += ", on behalf of " + commit.author_name
        firstline += "."

        committed_on = commit.datetime.strftime("Committed on %d/%m/%Y at %H:%M.")

        pushed_by = "Pushed by {0} into {1} '{2}'.".format(
            self.repository.push_user, self.repository.ref_type,
            self.repository.ref_name)

        summary = [firstline, committed_on, pushed_by, '', commit.message.strip(), '']
        for filename, info in commit.files_changed.iteritems():
            temporary = "{0:<2} +{1:<4} -{2:<4}".format(info["change"], info["added"], info["removed"])
            data = [temporary, filename]
            if "source" in info.keys():
                temporary = unicode("[from: {0} - {1}% similarity]").format(info["source"], info["similarity"])
                data.append( temporary )
            if self.checker:
                data.extend( self.checker.commit_notes[filename] )
            summary.append( ' '.join(data) )

        if self.checker and self.checker.license_problem:
            summary.append( "\nThe files marked with a * at the end have a non valid "
                "license. Please read: https://community.kde.org/Policies/Licensing_Policy "
                "and use the headers which are listed at that page.\n")
        if self.checker and self.checker.commit_problem:
            summary.append( "\nThe files marked with ** at the end have a problem. "
                "either the file contains a trailing space or the file contains a call to "
                "a potentially dangerous code. Please read: "
                "http://community.kde.org/Sysadmin/CommitHooks#Email_notifications "
                "Either fix the trailing space or review the dangerous code.\n")
        if self.include_url:
            summary.append( "\n" + commit.url )
        return '\n'.join( summary ) + '\n'

    def determine_keywords(self):
        """Parse special keywords in commits to determine further post-commit
        actions."""

        split = dict()
        split['email_cc']  = re.compile("^\s*CC[-_]?MAIL[:=]\s*(.*)")
        split['email_cc2'] = re.compile("^\s*C[Cc][:=]\s*(.*)")
        split['fixed_in']  = re.compile("^\s*FIXED[-_]?IN[:=]\s*(.*)")

        numeric = dict()
        numeric['bug_fixed'] = re.compile("^\s*(?:BUGS?|FEATURE)[:=]\s*(.+)")
        numeric['bug_cc']    = re.compile("^\s*CCBUGS?[:=]\s*(.+)")

        presence = dict()
        presence['email_gui'] = re.compile("^\s*GUI:")
        presence['silent']    = re.compile("(?:CVS|SVN|GIT|SCM).?SILENT")
        presence['notes']     = re.compile("(?:Notes added by 'git notes add'|Notes removed by 'git notes remove')")

        results = defaultdict(list)
        for line in self.commit.message.split("\n"):
            # If our line starts with Summary: (as it does when using Arcanist's default template) then strip this off
            # This allows for people to fill keywords in the Differential Summary and have this work smoothly for them
            line = re.sub("^Summary: (.+)", "\g<1>", line)

            # Start processing our keywords...
            for (name, regex) in split.iteritems():
                match = re.match( regex, line )
                if match:
                    results[name] += [result.strip() for result in match.group(1).split(",")]

            for (name, regex) in numeric.iteritems():
                match = re.match( regex, line )
                if match:
                    results[name] += re.findall("(\d{1,10})", match.group(1))

            for (name, regex) in presence.iteritems():
                if re.match( regex, line ):
                    results[name] = True

        self.keywords = results

class CiaNotifier(object):
    "Notifies CIA of changes to a repository"

    MESSAGE = E.message
    GENERATOR = E.generator
    SOURCE = E.source
    TIMESTAMP = E.timestamp
    BODY = E.body
    COMMIT = E.commit

    def __init__(self, repository):

        # Generate the non-variant part of the XML message sent to CIA.
        name = E.name("KDE CIA Python client")
        version = E.version("1.00")
        url = E.url("http://projects.kde.org/repo-management")
        self._generator = self.GENERATOR(name, version, url)

        self.repository = repository
        self.smtp = smtplib.SMTP()
        self.smtp.connect()

    def __del__(self):
        self.smtp.quit()

    def notify(self, builder):

        """Send the commmit notification to CIA.

        The message is created incrementally using lxml's "E" builder."""

        # Build the <files> section for the template...
        commit = builder.commit
        files = E.files()

        commit_msg = commit.message.strip()
        commit_msg = re.sub(r'[\x00-\x09\x0B-\x1f\x7f-\xff]', '', commit_msg)

        for filename in commit.files_changed:
            safe_filename = re.sub(r'[\x00-\x09\x0B-\x1f\x7f-\xff]', '', filename)
            file_element = E.file(safe_filename)
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
        message = MIMEText( commit_xml, 'xml', 'utf-8' )
        message['Subject'] = "DeliverXML"
        message['From'] = "sysadmin@kde.org"
        message['To'] = "commits@platna.kde.org"

        # Send email...
        self.smtp.sendmail("sysadmin@kde.org", ["commits@platna.kde.org"],
                           message.as_string())

class Commit(object):

    """Represents a git commit"""

    UrlPattern = "https://commits.kde.org/{0}/{1}"

    def __init__(self, repository, commit_data):
        self.repository = repository
        self._commit_data = commit_data
        self._raw_properties = ["files_changed", "datetime"]
        self.url = Commit.UrlPattern.format( repository.path, self.sha1 )

        # Convert the date into something usable...
        self._commit_data["datetime"] = datetime.fromtimestamp( float(self._commit_data["date"]) )

    def __getattr__(self, key):
        if key not in self._commit_data:
            raise AttributeError
        if key in self._raw_properties:
            return self._commit_data[key]

        value = self._commit_data[key]
        return unicode(value, "utf-8", 'replace')

    def __setattr__(self, key, value):
        if key not in ['_commit_data', '_raw_properties', 'repository']:
            self._commit_data[key] = value
        else:
            self.__dict__[key] = value

    def __repr__(self):
        return str(self._commit_data)

class CommitChecker(object):

    """Checker class for commit information such as licenses, or potentially
    unsafe practices."""

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

        # traditional license header LGPL or GPL
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

        # SPDX based LGPL or GPL
        # TODO first version for SPDX based license hooks: this only detects simple statements, shall be extended for full SPDX expressions
        if re.search("SPDX-License-Identifier: LGPL-2.0-only", text):
            license = "LGPL(v2.0) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: LGPL-2.0-or-later", text):
            license = "LGPL(v2.0+) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: LGPL-2.1-only", text):
            license = "LGPL(v2.1) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: LGPL-2.1-or-later", text):
            license = "LGPL(v2.1+) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: LGPL-3.0-only", text):
            license = "LGPL(v3.0) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: LGPL-3.0-or-later", text):
            license = "LGPL(v3.0+) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: LGPL-2.0-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL", text):
            license = "LGPL(v2.0/3+eV) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL", text):
            license = "LGPL(v2.1/3+eV) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: GPL-2.0-only", text):
            license = "GPL(v2.0) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: GPL-2.0-or-later", text):
            license = "GPL(v2.0+) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: GPL-3.0-only", text):
            license = "GPL(v3.0) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only", text):
            license = "GPL(v2/3) " + wrong + " " + license
        if re.search("SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL", text):
            license = "GPL(v2/3+eV) " + wrong + " " + license

        # QPL
        if re.search("may be distributed under the terms of the Q Public License as defined by Trolltech AS", text):
            license = "QPL " + license

        # X11, BSD-like
        if re.search("Permission is hereby granted free of charge to any person obtaining a copy of this software and associated documentation files", text):
            license = "X11 (BSD like) " + license

        # MIT license
        if re.search("Permission to use copy modify (and )?distribute(and sell)? this software and its documentation for any purpose", text):
            license = "MIT " + license
        if re.search("SPDX-License-Identifier: MIT", text):
            license = "MIT " + wrong + " " + license

        # BSD
        if re.search("MERCHANTABILITY( AND|| or) FITNESS FOR A PARTICULAR PURPOSE", text) and not re.search("GPL", license):
            license = "BSD " + license
        if re.search("SPDX-License-Identifier: BSD-2-Clause", text) or re.search("SPDX-License-Identifier: BSD-3-Clause", text):
            license = "BSD " + wrong + " " + license

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

    def check_commit_problems(self, commit, diff):

        """Check for potential problems in a commit."""

        # Initialise
        self._license_problem = False
        self._commit_problem = False
        self._commit_notes = defaultdict(list)

        # Unsafe regex checks...
        unsafe_matches = list()
        unsafe_matches.append( r"\b(KRun::runCommand|K3?ShellProcess|setUseShell|setShellCommand)\b\s*[\(\r\n]" )
        unsafe_matches.append( r"\b(system|popen|mktemp|mkstemp|tmpnam|gets|syslog|strptime)\b\s*[\(\r\n]" )
        unsafe_matches.append( r"(scanf)\b\s*[\(\r\n]" )
        valid_filename_regex = r"\.(cpp|cc|cxx|C|c\+\+|c|l|y||h|H|hh|hxx|hpp|h\+\+|qml)$"

        # Retrieve the diff and do the problem checks...
        filename = unicode("")
        filediff = list()
        for line in diff:
            file_change = re.match( "^diff --(cc |git a\/.+ b\/)(.+)$", line )
            if file_change:
                # Are we changing file? If so, we have the full diff, so do a license check....
                if filename != "" and commit.files_changed[ filename ]["change"] in ['A'] and re.search(valid_filename_regex, filename):
                    self.check_commit_license(filename, ''.join(filediff))

                filediff = list()
                filename = file_change.group(2)
                continue

            # Diff headers are bogus
            if re.match("@@ -\d+,\d+ \+\d+ @@", line):
                filediff = list()
                continue

            # Do an incremental check for *.desktop syntax errors....
            if re.search("\.desktop$", filename) and re.search("[^=]+=.*[ \t]$", line) and line.startswith("+") and not re.match("^\+#", line):
                self._commit_notes[filename].append( "[TRAILING SPACE] **" )
                self._commit_problem = True

            # Check for things which are unsafe...
            for safety_match in unsafe_matches:
                match = re.match(safety_match, line)
                if match:
                    note = "[POSSIBLY UNSAFE: {0}] **".format( match.group(1) )
                    self._commit_notes[filename].append(note)
                    self._commit_problem = True

            # Store the diff....
            filediff.append(line)

        if filename != "" and commit.files_changed[ filename ]["change"] in ['A'] and re.search(valid_filename_regex, filename):
            self.check_commit_license(filename, ''.join(filediff))

def read_command( command, shell=False ):
    process = subprocess.Popen(command, shell=shell, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return process.stdout.readline().strip()

def get_change_diff( repository, log_arguments ):
    # Prepare to run....
    command = ["git", "show", "--pretty=format:%xff%H%xff", "--stdin", "-C"]
    command.extend(log_arguments)
    process = subprocess.Popen(command, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Pass on the commits for it to show...
    for sha1 in repository.commits:
        process.stdin.write(sha1 + "\n")
    process.stdin.close()
    return process
