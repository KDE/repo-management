#!/usr/bin/perl -w
use warnings;

package GitHookLib;
use Exporter;
@ISA = qw(Exporter);

# Perl best practice can go to Antarctica as far as I care....
our @EXPORT = qw( GIT_EMPTY_REF
                  REPO_SYSADMIN REPO_WEBSITE REPO_SCRATCH REPO_CLONE REPO_NORMAL
                  REF_BRANCH REF_TAG REF_BACKUP REF_UNKNOWN
                  CHANGE_UPDATE CHANGE_CREATE CHANGE_DELETE CHANGE_FORCED
                  read_git read_git_oneline commit_changed_files commit_metadata commit_diffstat
                  audit_diff audit_filenames audit_metadata audit_load_filename_cfg
                );

# Specify some constants
use constant {
    GIT_EMPTY_REF  => "0000000000000000000000000000000000000000"
};

# Types of repositories....
use constant {
    REPO_SYSADMIN  => "sysadmin",
    REPO_WEBSITE   => "website",
    REPO_SCRATCH   => "scratch",
    REPO_CLONE     => "clone",
    REPO_NORMAL    => "normal"
};

# Types of refs....
use constant {
    REF_BRANCH     => "branch",
    REF_TAG        => "tag",
    REF_BACKUP     => "backup",
    REF_UNKNOWN    => "unknown"
};

# Changes to refs...
use constant {
    CHANGE_UPDATE => "update",
    CHANGE_CREATE => "create",
    CHANGE_DELETE => "delete",
    CHANGE_FORCED => "forced update"
};

# Perl modules we require...
use Net::DNS;

# Executes git with the given arguments, then reads in all output from git, and returns it in an list
# Each item in the list represents one line of output from git
sub read_git
{
    # Check for input....
    if( !@_ ) {
        die "Arguments not provided...\n";
    }

    # Prepare to gather our data...
    my @output;

    # Run git, and read the data in...
    open(GIT_IN, '-|') || exec('git', @_) or die "Failed to execute Git...\n";
    while(<GIT_IN>) {
        chomp;
        push(@output, $_) if $_ ne "";
    }
    close(GIT_IN);

    # Check to see if we had issues running git....
    my $result = $?;
    my $exit   = $result >> 8;
    my $signal = $result & 127;
    die "'git @_' died with signal: $signal\n" if $signal;
    die "'git @_' exited with non-zero code $exit\n" if $exit;

    # Return data
    return @output;
}

# Executes read_git with the given arguments, then extracts the first line of output and returns that
# All other lines of output are discarded. A empty string will be returned if the returned output is invalid
sub read_git_oneline
{
    my @data = read_git(@_);
    return "" if !@data;
    return shift(@data);
}

# Returns a list of files changed in the specified commit
sub commit_changed_files
{
    my $commit = shift;
    return read_git( 'show', '--pretty=format:', '--name-only', $commit );
}

# Returns the metadata of the specified commit ( in a list, ordered author name, author email, date, commit message )
sub commit_metadata
{
    # Retrieve information....
    my $commit = shift;
    my ($author_name, $author_email, $date, $message);

    # Read some commit metadata...
    my @data = read_git( 'log', '--encoding=UTF-8', '--pretty=format:%an%n%ae%n%aD%n%B', '-n1',  $commit );
    $author_name = shift( @data );
    $author_email = shift( @data );
    $date = shift( @data );
    $message = @data;

    return ( $author_name, $author_email, $date, $message );
}

# Return the diff stat
sub commit_diffstat
{
    my $commit = shift;
    return read_git( 'log', '--encoding=UTF-8', '--stat', '--pretty=format:', '-n1',  $commit );
}

# Auditing Part 1
# Audits the specified commits diff, checking for incorrect EOL and conflict markers
sub audit_diff
{
    # Initialisation....
    my $commit = shift;
    my $errors = shift;
    my @gitcmd = ('git', 'show', '--pretty=format:', '--unified=0', $commit);

    # State tracking...
    my $violationdetect = 0;
    my $currentfile = "";

    # We have to do this the manual way, as bringing the whole diff into memory is too dangerous....
    open(IN, "-|") || exec( @gitcmd ) or die "Error - Failed to invoke git to extract diff\n";
    while(<IN>) {
        # Search for the file name....
        if(/^diff --git a\/(\S+) b\/(\S+)$/) {
            $currentfile = $2;
            $violationdetect = 0;
            next;
        }

        # Don't complain about the same file twice...
        next if $violationdetect;

        # Unless they added it, ignore it
        next if ($_ !~ /^\+/);

        if (/(?:\r\n|\n\r|\r)$/) {
            # Failure has been found... handle it
            $violationdetect = 1;
            push(@$errors, "End Of Line Style - $currentfile");
        }
    }
    close(IN);
}

# Auditing Part 2
# Audits a specified commit's list of files changed, checking to see if any effected files are not allowed
sub audit_filenames
{
    # Prepare to check
    my $commit = shift;
    my $errors = shift;
    my $deny_filenames = shift;

    # Check for validity....
    if( !@$deny_filenames ) {
        die "Error - Insufficient input to execute filename audit\n";
    }

    # Get a list of filenames...
    my @files = commit_changed_files( $commit );

    # Run the file name regexp's...
    foreach $filename ( @files ) {
        foreach $check( @$deny_filenames ) {
            # Run the check
            push(@$errors, "File Name - $filename") if $filename =~ $check;
        }
    }
}

# Auditing Part 3
# Audits a specified commit's metadata, ensuring the email address of the author and committer are both valid
sub audit_metadata
{
    # Preperations....
    my $commit = shift;
    my $errors = shift;
    my ($authorname, $authormail, $date, $message) = commit_metadata( $commit );

    if( $authormail =~ /^(\S+)@(\S+)$/ )
    {
        # Seperate the email domain out, and disallow localhost
        my $emaildomain = $2;
        if( $emaildomain eq "localhost" || $emaildomain eq "localhost.localdomain" || $emaildomain eq "(none)" ) { 
            push(@$errors, "Author Email");
            return;
        }

        # Check if the domain exists...
        my $resolver  = Net::DNS::Resolver->new;
        my $query = $resolver->query($emaildomain, "MX");

        # If the MX doesn't exist, perhaps A will...
        $query = $resolver->query($emaildomain, "A") if !$query;

        # Fail if it doesn't exist
        push(@$errors, "Author Email") if !$query;
        return;
    }

    # Parse failure, so reject them....
    push(@$errors, "Author Email");
}

# Auditing initialisation
# Loads the regexp's which block certain filenames from being added to KDE SCM repositories
sub audit_load_filename_cfg
{
    # Initialisation....
    my $managementdir = shift;
    my @restrictednames;

    # Read in the configuration....
    open(CFG, "$managementdir/config/blockedfiles.cfg") or die "Error - Failed to locate blockedfiles.cfg for auditing setup\n";
    while( my $line = <CFG> ) 
    {
        chomp($line);

        # Skip comments and blank lines
        if( $line =~ m/#/ || $line eq "" ) {
            next;
        }

        # To help users that automatically write regular expressions that match the beginning of absolute paths using ^/,
        # remove the / character because subversion/git paths, while they start at the root level, do not begin with a /.
        $line =~ s#^\^/#^#;

        my $match_re;
        eval { $match_re = qr/$line/ };

        # Check to make sure the regexp is good
        if ($@) {
            next;
        }

        push( @restrictednames, $match_re );
    }
    close( CFG );

    return @restrictednames;
}

return 1;
