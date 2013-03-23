#!/usr/bin/env perl

my $prevlines=`wc $ENV{HOME}/projects.list`;
my $candidatelines=`wc $ENV{HOME}/projects.list.candidate`;

my $diff = abs(($candidatelines - $prevlines) / (1.0 * $prevlines)) * 100;

if ($diff > 1.0) {
	exit(1);
}

exit(0);
