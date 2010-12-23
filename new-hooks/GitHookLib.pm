#!/usr/bin/perl -w
use warnings;

package GitHookLib;
use Exporter;
@ISA = qw(Exporter);

# Perl best practice can go to Antarctica as far as I care....
our @EXPORT = qw( GIT_EMPTY_REF
                  REF_BRANCH REF_TAG REF_BACKUP REF_UNKNOWN
                  CHANGE_UPDATE CHANGE_CREATE CHANGE_DELETE CHANGE_FORCED
                  read_git read_git_oneline commit_changed_files commit_metadata commit_diffstat
                );

# Specify some constants
use constant {
    GIT_EMPTY_REF  => "0000000000000000000000000000000000000000"
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
        push(@output, $_);
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

sub commit_changed_files
{
    my $commit = shift;
    return read_git( 'show', '--pretty="format:"', '--name-only', $commit );
}

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

    return { 'author_name' => $author_name, 'author_email' => $author_email, 'date' => $date, 'message' => $message };
}

sub commit_diffstat
{
    my $commit = shift;
    return read_git( 'log', '--encoding=UTF-8', '--pretty=format:%an%n%ae%n%aD%n%B', '-n1',  $commit );
}

return 1;
