#!/usr/bin/env perl

my $prevlines = $ARGV[0];
my $candidatelines = $ARGV[1];

my $wcprevlines = `wc -l $prevlines`;
my $wccandidatelines = `wc -l $candidatelines`;
my $difflines = `diff --suppress-common-lines $prevlines $candidatelines | wc -l`;

my $wcdiff = abs(($wccandidatelines - $wcprevlines) / (1.0 * $wcprevlines)) * 100;

my $diffprev = abs($difflines * 1.0 / $wcprevlines);
my $diffcandidate = abs($difflines * 1.0 / $wccandidatelines);

if ($wcdiff > 1.0) {
  exit(1);
}

# Higher tolerance on these checks since diff outputs diff output

if ($diffprev > 0.02) {
  exit(2);
}

if ($diffcandidate > 0.02) {
  exit(3);
}

exit(0);
