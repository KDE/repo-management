#!/usr/bin/env ruby
require 'digest/sha1'

# Define a recursive function that will traverse the directory tree
def printAndDescend(pattern, directory=nil)
  if not directory
    directory = '*'
  end
  
  # We keep track of the directories, to be used in the second, recursive part of this function
  directories=[]
  gitDirectoryRoot = ARGV[0]
  tarballDirectoryRoot = ARGV[1]

  Dir[directory].sort.each do |name|
    fullPath = File.expand_path(name)
    if File.directory?(name) and name[pattern] and not fullPath["#{gitDirectoryRoot}/scratch"] and not fullPath["#{gitDirectoryRoot}/clones"] and not fullPath["#{gitDirectoryRoot}/sysadmin"]
      buildTarball(name, gitDirectoryRoot, tarballDirectoryRoot)
    elsif File.directory?(name)
      directories << name
    end
  end

  directories.each do |name|
    #don't descend into . or .. on linux
    Dir.chdir(name){printAndDescend(pattern)} if !Dir.pwd[File.expand_path(name)]
  end
end

# Function to build a tarball of a git repository
def buildTarball(repository, gitDirectoryRoot, tarballDirectoryRoot)
    # Make sure we are allowed to build a tarball for this repo
    fullRepoPath = File.expand_path(repository)
    return if not File.exists?("#{fullRepoPath}/git-daemon-export-ok")
    
    # Get a cleaned name suitable for use
    repoPath = fullRepoPath.gsub(/#{gitDirectoryRoot}/, '')
    repoPath.gsub!(/\.git/, '')
    repoName = File.basename(repoPath)
    if repoPath.nil?
        puts "Encountered error while processing repository #{repository}\n"
        return
    end
    
    # Start the processing for this repository
    tarballPath = "#{tarballDirectoryRoot}/#{repoPath}"
    puts "Ready to build tarball for repository #{repository}"
    puts "Tarball to be built into #{tarballPath}/#{repoName}-latest.tar.gz"

    # TODO: I'm not actually sure the gc is needed; do fresh checkouts take after the server, or will they be
    # compact automatically since they're a fresh write of the refs to the local repo?
    Dir.chdir(fullRepoPath) {
        %x[git gc --auto]
        %x[git prune]
    }
    
    # Ensure the working area exists...
    %x[mkdir -p  #{tarballPath}]
    
    # Clone the repository, then remove all the files in the checkout except for the .git/ directory
    Dir.chdir(tarballPath) {
        %x[git clone -l #{fullRepoPath} #{repoName}] 
        %x[rm -rf .git]
        %x[mv #{repoName}/.git .]
        %x[rm -rf #{repoName}]
        %x[mkdir #{repoName}]
        %x[mv .git #{repoName}] 
    }
    
    # Alter the git repository configuration to use anongit.kde.org, and add the initrepo.sh script
    Dir.chdir("#{tarballPath}/#{repoName}") { 
        %x[sed -i -e "s/\\/srv\\/git\\/repositories/http\\:\\/\\/anongit.kde.org/g" .git/config]
        %x[echo "#!/bin/sh\n\nrm initrepo.sh\n\ngit reset --hard HEAD" > initrepo.sh; chmod +x initrepo.sh]
    }

    # Remove the old tarball, and generate the new one
    Dir.chdir(tarballPath) { 
        %x[rm -rf *.tar.gz] 
        %x[tar -czf #{repoName}-latest-stage.tar.gz #{repoName}; rm -rf #{repoName}]
    }

    # Get a timestamp, and hash the file, then setup the final tarball name + symlink
    timestring = Time.now.strftime("%Y%m%d%H%M%S")
    digest = Digest::SHA1.file("#{tarballPath}/#{repoName}-latest-stage.tar.gz").hexdigest  
    Dir.chdir(tarballPath) {
        %x[ln -s #{repoName}_#{timestring}_sha1-#{digest}.tar.gz #{repoName}-latest.tar.gz]
        %x[mv #{repoName}-latest-stage.tar.gz #{repoName}_#{timestring}_sha1-#{digest}.tar.gz] 
    }
end

if not ARGV[0] or not ARGV[1]
  puts "Need to pass in the git directory root and tarball directory root -- do not pass in symlinks!"
  exit 1
end

printAndDescend(/.git$/, ARGV[0])
