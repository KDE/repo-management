import sys

if sys.platform == "win32":
	from .windows.mime import MimeType
else:
	from .xdg.mime import MimeType
