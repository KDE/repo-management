"""
Base MimeType class
"""

import os

class BaseMime(object):
	DEFAULT_TEXT = "text/plain"
	DEFAULT_BINARY = "application/octet-stream"
	SCHEME_FORMAT = "x-scheme-handler/%s"
	ZERO_SIZE = "application/x-zerosize"

	def __init__(self, mime):
		self.__name = mime
		self._aliases = []
		self._comment = {}

	def __eq__(self, other):
		if isinstance(other, BaseMime):
			return self.name() == other.name()
		return self.name() == other

	def __str__(self):
		return self.name()

	def __repr__(self):
		return "<MimeType: %s>" % (self.name())

	@classmethod
	def fromInode(cls, name):
		import stat
		try:
			mode = os.stat(name).st_mode
		except IOError:
			return

		# Test for mount point before testing for inode/directory
		if os.path.ismount(name):
			return cls("inode/mount-point")

		if stat.S_ISBLK(mode):
			return cls("inode/blockdevice")

		if stat.S_ISCHR(mode):
			return cls("inode/chardevice")

		if stat.S_ISDIR(mode):
			return cls("inode/directory")

		if stat.S_ISFIFO(mode):
			return cls("inode/fifo")

		if stat.S_ISLNK(mode):
			return cls("inode/symlink")

		if stat.S_ISSOCK(mode):
			return cls("inode/socket")

	@classmethod
	def fromScheme(cls, uri):
		try:
			from urllib.parse import urlparse
		except ImportError:
			from urlparse import urlparse

		scheme = urlparse(uri).scheme
		if not scheme:
			raise ValueError("%r does not have a scheme or is not a valid URI" % (scheme))

		return cls(cls.SCHEME_FORMAT % (scheme))

	def genericIcon(self):
		return self.genericMime().name().replace("/", "-")

	def genericMime(self):
		return self.__class__("%s/x-generic" % (self.type()))

	def icon(self):
		return self.name().replace("/", "-")

	def isDefault(self):
		name = self.name()
		return name == DEFAULT_BINARY or name == DEFAULT_TEXT

	def isInstance(self, other):
		return self == other or other in self.subClassOf()

	def name(self):
		return self.__name

	def subtype(self):
		return self.name().split("/")[1]

	def type(self):
		return self.name().split("/")[0]
