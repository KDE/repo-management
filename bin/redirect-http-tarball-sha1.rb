#!/usr/bin/env ruby
=begin
/****************************************************************************************
 * Copyright (c) 2010 Jeff Mitchell <mitchell@kde.org>                                  *
 *                                                                                      *
 * This program is free software; you can redistribute it and/or modify it under        *
 * the terms of the GNU General Public License as published by the Free Software        *
 * Foundation; either version 2 of the License, or (at your option) any later           *
 * version.                                                                             *
 *                                                                                      *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY      *
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A      *
 * PARTICULAR PURPOSE. See the GNU General Public License for more details.             *
 *                                                                                      *
 * You should have received a copy of the GNU General Public License along with         *
 * this program.  If not, see <http://www.gnu.org/licenses/>.                           *
 ****************************************************************************************/

=end
require 'sinatra'

get %r{(.*)/([a-zA-Z0-9][a-zA-Z0-9_\.\-]+[a-zA-Z0-9])-latest\.tar\.gz} do |dir, name|
  begin
    path = "#{dir}/#{name}-latest.tar.gz"
    newbasename = File.readlink("/repository-tarballs#{path}")
    redirect "#{dir}/#{newbasename}"
  rescue Exception
    status 404
    "Rescuing: Not found"
  end
end

get '*' do
  status 404
  "Not found"
end