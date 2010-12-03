#!/usr/bin/perl

require warnings; import warnings;
use strict;

sub loadfileconfig;
sub getfilename;

use Net::DNS;

######################################################################
# Configuration section.

# Git path.
my $gitbin = "/usr/bin/git";

# Since the path to git depends upon the local installation
# preferences, check that the required program exists to insure that
# the administrator has set up the script properly.
{
  my $ok = 1;
  foreach my $program ($gitbin)
    {
      if (-e $program)
        {
          unless (-x $program)
            {
              warn "$0: required program `$program' is not executable, ",
                   "edit $0.\n";
              $ok = 0;
            }
        }
      else
        {
          warn "$0: required program `$program' does not exist, edit $0.\n";
          $ok = 0;
        }
    }
  exit 1 unless $ok;
}

######################################################################
# Initial setup/command-line handling.

&usage unless @ARGV == 2;

my $commitid = shift;
my $auditcfg = shift;

######################################################################
# Harvest data using git...

## Rely on Gitolite to have set the username properly
my $author = $ENV{'GL_USER'};

## WARNING: Allowing people to bypass this hook means no EOL, File Name or Commit Author Validity checks are done on any push by them!!
# Make scripty commits faster
if ($author =~ m/scripty/) {
  exit 0;
}

# Data about the commit
my $commitname = "";
my $commitmail = "";

# Did we fail?
my $auditfail = 0;
my @eolfailed = ();
my @namefailed = ();
my $detailfailed = 0;
my $internalerror = 0;

# Get configuration for file name restrictions....
my @restrictednames;
loadfileconfig();

# Check for things we have to exclude
my $excludeeol = ( -e "$auditcfg/skip-eol" );
my $excludemail = ( -e "$auditcfg/skip-author" );
my $excludefname = ( -e "$auditcfg/skip-filename" );

# Temporary vars
my $violationdetect = 0;
my $currentfile = "";

# Do we even need to do any checking at all?
if( $excludeeol && $excludemail && $excludefname ) {
  exit 0;
}
   
# Gather all the information
open(IN, "-|") || exec( $gitbin, 'show', $commitid ) or $internalerror = 1;
while(<IN>) {

    # Search for the file name....
    if (/^diff --git a\/(\S+) b\/(\S+)$/) {
        $currentfile = $2;
        checkfilename( $2 );
        next;
    }

    # Search for committer name + email
    if (/^Author: (.+) <(\S+)>$/) {
        $commitname = $1;
        $commitmail = $2;
        next;
    }

    # Are we excluded?
    next if $excludeeol;

    # Don't complain about the same file twice...
    if ( $violationdetect == 1 ) {
        next;
    }

    # Unless they added it, ignore it
    next if ($_ !~ /^\+/);

    if (/(?:\r\n|\n\r|\r)$/) {
        # Failure has been found... handle it
        $auditfail = $violationdetect = 1;

        # Note the breach for complaining later....
        push(@eolfailed, $currentfile);
    }
}
close(IN);

# Audit the name + email
if( $commitmail =~ /^(\S+)@(\S+)$/ && !$excludemail )
{
    # Seperate the email domain out, and disallow localhost
    my $emaildomain = $2;
    if( $emaildomain eq "localhost" || $emaildomain eq "localhost.localdomain" || $emaildomain eq "(none)" ) { $detailfailed = 1; }

    # Check if the domain exists...
    my $resolver  = Net::DNS::Resolver->new;
    my $query = $resolver->query($emaildomain, "MX");
    if( !$query ) {
      $query = $resolver->query($emaildomain, "A");
    }

    # Fail if it doesn't exist
    $detailfailed = 1 unless $query;

    # Update failure status
    if( $detailfailed == 1 ) { $auditfail = 1; }
} elsif( !$excludemail ) {
    # Reg-Exp doesn't match, something is wrong
    $detailfailed = 1;
    $auditfail = 1;
}

# Did we have any internal errors?
$auditfail = 1 unless $internalerror == 0;

# Time to make any complaints...
if( $auditfail != 0 )
{
    print STDERR "****\n";
    print STDERR "** Commit audit failure: $commitid\n";
}

foreach my $filename( @eolfailed )
{
    print STDERR "** End Of Line Style - $filename\n";
}

foreach my $filename( @namefailed )
{
    print STDERR "** File Name - $filename\n";
}

if( $detailfailed != 0 )
{
    print STDERR "** Commit Author - invalid name or email\n";
}

if( $internalerror != 0 )
{
    print STDERR "** Internal Validation Error - please contact sysadmin\@kde.org\n";
}

if( $auditfail != 0 )
{
    print STDERR "****\n";
}

# Cleanup, and prepare to exit

my $result = $?;
my $exit   = $result >> 8;
my $signal = $result & 127;
my $cd     = $result & 128 ? "with core dump" : "";
if ($signal or $cd)
{
    warn "$0: pipe from `@_' failed $cd: exit=$exit signal=$signal\n";
}

exit $auditfail;

sub usage
{
  warn "@_\n" if @_;
  die "usage: $0 commit configdir\n";
}

sub loadfileconfig
{
    my $managementdir = $ENV{'mgmtdir'};
    open(CFG, "$managementdir/config/blockedfiles.cfg") or $internalerror = 1;
    while( <CFG> ) 
    {
        # Read in the next line
        my $line = "";
        if( /(\S+)/ ) {
            $line = $1;
        }

        # Skip comments and blank lines
        if( $line =~ m/#/ || $line eq "" ) {
            next;
        }

        # To help users that automatically write regular expressions
        # that match the beginning of absolute paths using ^/,
        # remove the / character because subversion paths, while
        # they start at the root level, do not begin with a /.
        $line =~ s#^\^/#^#;

        my $match_re;
        eval { $match_re = qr/$line/ };

        # Check to make sure the regexp is good
        if ($@)
        {
            next;
        }
        else
        {
            push( @restrictednames, $match_re );
        }

    }
    close( CFG );
}

sub checkfilename
{
    # Prepare to check
    my $filename = shift;

    # Skip if needed....
    return if $excludefname;

    # Run the file name regexp's...
    foreach my $check ( @restrictednames )
    {
        # Run the check
        if( $filename =~ $check ) {
            push(@namefailed, $filename);
            $auditfail = 1;
            return;
        }
    }
}
