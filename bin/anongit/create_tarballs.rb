#!/usr/bin/env ruby

require 'digest/sha1'

# A so far quick and dirty hack to do the tarball generation
# It uses Ruby to make some things easier and shells out for most of it
# Found the printAndDescent code on rosettacode and adopted it

#define a recursive function that will traverse the directory tree
def printAndDescend(pattern, directory=nil)
  #we keep track of the directories, to be used in the second, recursive part of this function
  if not directory
    directory = '*'
  end
  directories=[]
  Dir[directory].sort.each do |name|
    if File.directory?(name) and name[pattern] and not File.expand_path(name)["#{ARGV[0]}/scratch"] and not File.expand_path(name)["#{ARGV[0]}/clones"] and not File.expand_path(name)["#{ARGV[0]}/sysadmin"]
      # do magic here
      # first, garbage collect the repo so that we have the smallest tarball
      path = File.expand_path(name)
      newpath = path.gsub(/#{ARGV[0]}/, '')
      newpath.gsub!(/\.git/, '')
      if newpath.nil?
        puts "BAILING!"
        Process.exit!(1) 
      end
      puts "Working on repository in #{path}"
      basename = File.basename(newpath)
      puts "Will build tarball into #{ARGV[1]}#{newpath}/#{basename}-latest.tar.gz"
      # TODO: I'm not actually sure the gc is needed; do fresh checkouts take after the server, or will they be
      # compact automatically since they're a fresh write of the refs to the local repo?
      # Need to investigate but since everything right now is already
      # garbage collected I can't at the moment...  :-)
      next if not File.exists?("#{File.expand_path(name)}/git-daemon-export-ok")
      Dir.chdir(File.expand_path(name)){ %x[git gc --auto] }
      Dir.chdir(File.expand_path(name)){ %x[git prune] }
      Dir.chdir("#{ARGV[1]}/"){ %x[mkdir -p  #{ARGV[1]}#{newpath}] }
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[git clone -l #{ARGV[0]}#{newpath}.git #{basename}] }
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[rm -rf .git] }
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[mv #{basename}/.git .] }
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[rm -rf #{basename}] }
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[mkdir #{basename}] }
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[mv .git #{basename}] }
      Dir.chdir("#{ARGV[1]}/#{newpath}/#{basename}") { %x[sed -i -e "s/\\/srv\\/kdegit\\/repositories/http\\:\\/\\/anongit.kde.org/g" .git/config] }
      Dir.chdir("#{ARGV[1]}/#{newpath}/#{basename}") { %x[echo "#!/bin/bash\n\nrm initrepo.sh\n\ngit reset --hard HEAD" > initrepo.sh; chmod +x initrepo.sh] }
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[rm -rf *.tar.gz] }
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[tar -czf #{basename}-latest-stage.tar.gz #{basename}; rm -rf #{basename}] }
      time = Time.now
      timestring = time.strftime("%Y%m%d%H%M%S")
      digest = Digest::SHA1.file("#{ARGV[1]}/#{newpath}/#{basename}-latest-stage.tar.gz").hexdigest
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[ln -s #{basename}_#{timestring}_sha1-#{digest}.tar.gz #{basename}-latest.tar.gz] }
      Dir.chdir("#{ARGV[1]}/#{newpath}") { %x[mv #{basename}-latest-stage.tar.gz #{basename}_#{timestring}_sha1-#{digest}.tar.gz] }
    elsif File.directory?(name)
      directories << name
    end
  end
  directories.each do |name|
    #don't descend into . or .. on linux
    Dir.chdir(name){printAndDescend(pattern)} if !Dir.pwd[File.expand_path(name)]
  end
end

if not ARGV[0] or not ARGV[1]
  puts "Need to pass in the git directory root and tarball directory root -- do not pass in symlinks!"
  exit 1
end

printAndDescend(/.git$/, ARGV[0])
