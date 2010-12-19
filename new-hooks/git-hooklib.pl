#!/usr/bin/perl -w

sub get_revision_list
{
    # Initialisation....
    my $oldsha1 = shift;
    my $newsha1 = shift;
    my @revision_list = ( );
    my $revision_span = "";

    # Build the revision span git will use to help build the revision list...
    if( $change_type eq "create" ) {
        $revision_span = "$newsha1";
    } else {
        $revision_span = `git merge-base $newsha1 $oldsha1` . "..$newsha1"
    }

    # Read in the revision list...
    open(GITIN, "-|") || exec( "git rev-parse --not --all | grep -v $oldsha1 | git rev-list --reverse --stdin $revision_span" );
    while(<GITIN>) {
        push( @revision_list, $_ );
    }
    close(GITIN);

    return @revision_list;
}

sub get_commit_diffstat
{
    # Retrieve information....
    my $commit = shift;
    my $diffstat = ();

    # Read some commit metadata...
    open(GITIN, "-|") || exec( 'git', 'log', '--encoding=UTF-8', '--pretty=format:%an%n%ae%n%aD%n%B', '-n1',  $commit );
    while(<GITIN>) {
        next if $_ eq "";
        push(@diffstat, $_);
    }
    close(GITIN);

    return $diffstat
}

sub get_commit_details
{
    # Retrieve information....
    my $commit = shift;
    my ($author_name, $author_email, $date, $message);

    # Read some commit metadata...
    open(GITIN, "-|") || exec( 'git', 'log', '--encoding=UTF-8', '--pretty=format:%an%n%ae%n%aD%n%B', '-n1',  $commit );
    $author_name = <GITIN>;
    $author_email = <GITIN>;
    $date = <GITIN>;
    while(<GITIN>) {
        push(@message, $_);
    }
    close(GITIN);

    return { 'author_name' => $author_name, 'author_email' => $author_email, 'date' => $date, 'message' => $message };
}

sub get_commit_changed_files
{
    # Initialise and retrieve info...
    my $commit = shift;
    my $files = ();

    # A question of do or don't here.... read into memory or piece by piece??
    open(GITIN, "-|") || exec( 'git', 'show', '--pretty="format:"', '--name-only', $commit );
    while(<GITIN>) {
        next if $_ eq "";
        push(@files, $_);
    }
    close(GITIN);

    return $files;
}

sub initialise_audit
{
}

sub audit_eol
{
    # Check to see if we need to run on this repository....
    if( -e "$auditcfg/skip-eol" ) {
        return;
    }
}

sub audit_filename
{
    # Check to see if we need to run on this repository....
    if( -e "$auditcfg/skip-author" ) {
        return;
    }
}

sub audit_author
{
    # Check to see if we need to run on this repository....
    if( -e "$auditcfg/skip-filename" ) {
        return;
    }
}

return 1;
