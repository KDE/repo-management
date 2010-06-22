#!/usr/bin/perl

require warnings; import warnings;
use strict;

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

&usage unless @ARGV == 3;

my $ref          = shift;
my $oldsha       = shift;
my $newsha       = shift;
my $cfg_filename = "/home/git/repo-management/blockedfiles.cfg";

######################################################################
# Import the configuration...

my @restrictions;
open(CFG, $cfg_filename);
while( <CFG> ) {

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
        push( @restrictions, $match_re );
    }

}
close( CFG );

######################################################################
# Harvest data using git...

# Special git sha
my $empty = '4b825dc642cb6eb9a060e54bf8d69288fbee4904';

# Get a list of changed commits
my $denied     = 0;
my $currentsha = "";
my $oldtree    = $oldsha eq '0' x 40 ? $empty : $oldsha;
my $newtree    = $newsha eq '0' x 40 ? $empty : $newsha;
open(IN, "-|") || exec $gitbin, 'diff', '--name-only', $oldtree, $newtree;

while( <IN>) {

    my $filename = "";
    if( /(\S+)/ ) {
        $filename = $1;
    }

    if( $filename eq "" ) {
        next;
    }

    my $filematched = 0;
    foreach my $check ( @restrictions )
    {
        if( $filematched == 1 ) {
            next;
        }

        if( $filename =~ $check ) {
            print STDERR "===\n";
            print STDERR "= File $filename\n";
            print STDERR "= Access Denied: file name is invalid\n";

            $denied = 1;
        }
    }
}
close(IN);

my $result = $?;
my $exit   = $result >> 8;
my $signal = $result & 127;
my $cd     = $result & 128 ? "with core dump" : "";
if ($signal or $cd)
{
    warn "$0: pipe from `@_' failed $cd: exit=$exit signal=$signal\n";
}

if( $denied == 0 )
{
    print STDERR "File name check passed\n";
}

exit $denied;

sub usage
{
  warn "@_\n" if @_;
  die "usage: $0 ref oldsha newsha\n";
}
