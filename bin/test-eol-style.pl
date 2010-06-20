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

my $ref    = shift;
my $oldsha = shift;
my $newsha = shift;

######################################################################
# Harvest data using git...

## Rely on Gitolite to have set the username properly
my $author = $ENV{GL_USER};

# Make scripty commits faster
if ($author =~ m/scripty/) {
  exit 0;
}

# Set the Git work tree so that Git knows where to begin to look for the repo
$ENV{GIT_WORK_TREE} = $ENV{GL_REPO}

# Get the diff of the commits and start looking
my $last_filename = "";
open(IN, "-|") || exec $gitbin, 'diff', $oldsha, $newsha;
while(<IN>) {
    if (/^\+\+\+ b\/(\S+)/) {
      $last_filename = $1;
      next;
    }

    next if ($_ !~ /^\+/);

    if (/(?:\r\n|\n\r|\r)$/) {
        print STDERR "=== $last_filename\n";
        print STDERR "eol style violation detected.\n";

        exit 1;
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

exit 0;

sub usage
{
  warn "@_\n" if @_;
  die "usage: $0 ref oldsha newsha\n";
}
