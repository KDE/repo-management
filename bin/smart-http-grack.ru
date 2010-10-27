$LOAD_PATH.unshift File.expand_path(File.dirname(__FILE__) + '/lib')

use Rack::ShowExceptions

require 'lib/git_http'

config = {
  :project_root => "/repositories",
  :git_path => '/usr/libexec/git-core/git',
  :upload_pack => true,
  :receive_pack => false,
}

run GitHttp::App.new(config)