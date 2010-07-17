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

&usage unless @ARGV == 1;

my $commitid = shift;

######################################################################
# Harvest data using git...

## Rely on Gitolite to have set the username properly
my $author = $ENV{GL_USER};

# Make scripty commits faster
if ($author =~ m/scripty/) {
  exit 0;
}

# Prepare to search for violations
my $last_filename = "";
my $violationdetect = 0;
my $eolerror = 0;
    
# Get the diff of this commit...
open(IN, "-|") || exec $gitbin, 'show', $commitid;
while(<IN>) {
    if (/^\+\+\+ b(\S+)/) {
        $last_filename = $1;
        $violationdetect = 0;
        next;
    }

    # Don't complain about the same file twice...
    if ( $violationdetect == 1 ) {
        next;
    }

    next if ($_ !~ /^\+/);

    if (/(?:\r\n|\n\r|\r)$/) {
        print STDERR "===\n";
        print STDERR "= Commit $commitid - $last_filename\n";
        print STDERR "= EOL style violation detected.\n";
        print STDERR "= Please ensure you are using unix line endings.\n";

        $violationdetect = 1;
        $eolerror = 1;
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

exit $eolerror;

sub usage
{
  warn "@_\n" if @_;
  die "usage: $0 commit\n";
}
