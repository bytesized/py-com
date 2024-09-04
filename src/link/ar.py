# SPDX-License-Identifier: GPL-3.0-or-later
from collections import namedtuple

from . import parse

# File format sources:
# (1) https://en.wikipedia.org/wiki/Ar_(Unix)
# (2) https://www.unix.com/man-page/opensolaris/3head/ar.h/
# (3) https://web.archive.org/web/20070624034732/https://www.microsoft.com/msj/0498/hood0498.aspx
# (3.1) https://web.archive.org/web/20100629163054/http://www.microsoft.com/msj/0498/hoodtextfigs.htm

class ArchiveReadException(Exception):
  pass

class ArchiveReader:
  """
    This class is designed to pull data out of `.lib` files the would normally be used by a linker
    to compile against a DLL.

    .lib files' top level structure seems to be `ar` archive structure. This structure is described
    by sources (1), (2), and (3). Oddly, this part of the structuring is completely ignored by many
    other sources, which often just say that `.lib` files use COFF format.

    The archive contains several files, also called members. The first two are index files that
    essentially map symbols to the other member containing it. This class only reads the first
    index file since, per sources (3) and (4), they are identical except for the sort order and the
    endian used for the offset.

    The other members are OBJ files in COFF format. This is described in detail in source (4).

    Perusing around, it doesn't really seem like these files ever exceed a few megabytes. So, for
    the time being, this class will not support seeking through the file and pulling out the
    requested bits on demand. We will just load the whole file into memory at once.

    The main interfaces into `ArchiveReader` instances are the `members` and `symbol_member_map`
    dictionary member values. `symbol_member_map` maps symbol names to member filenames. `members`
    maps member filenames to instances of `ArchiveReader.Member`, which provides access to the
    member's data and metadata. Note that the index and filename lookup members are currently not
    included.
  """

  # Describes a member within the library.
  # This very closely mimics `IMAGE_ARCHIVE_MEMBER_HEADER` in `winnt.h` with some light processing.
  # `name` is the name of the file, though this tends to not be particularly relevant to using a
  # `.lib` file. These are parsed as described by the "Windows variant" section of source (1).
  # A `.lib` file generally contains special members named "/" and "//". These names are not
  # processed are left as-is.
  # The numeric datatypes (`date`, `mode`, `size`) are converted to integers rather than being
  # stored as ASCII. `user_id` and `group_id` are not converted to integers largely because that
  # information seems to just be absent in the `.lib` files.
  # `content` is a `parse.BufferStream` of the file content
  Member = namedtuple("Member", ["name", "date", "user_id", "group_id", "mode", "size",
                                 "content"])

  def __init__(self, data = None):
    self.reset()
    if data is not None:
      self.load(data)

  def reset(self):
    self.members = {}
    self.symbol_member_map = {}

  def read_file(self, path):
    with open(path, "rb") as f:
      data = f.read()
    self.load(data)

  def _read_member(self, data_stream, filename_member = None):
    filename = data_stream.read_ascii(16).rstrip(" ")
    if filename not in ("/", "//"):
      # Parse the filename. It should be in one of two formats: A `/` marks the end of the filename
      # or the filename instead beings with a `/` and is followed by an ASCII numeric offset into
      # the filename member that is used to lookup the null terminated filename.
      if filename.endswith("/"):
        filename = filename[:-1]
      elif filename.startswith("/"):
        filename_offset = int(filename[1:])
        if filename_member is None:
          raise ArchiveReadException(
            f"Member's filename ({filename}) references nonexistent filename lookup member"
          )
        filename = filename_member.content.read_cstring(seek = filename_offset)
      else:
        raise ArchiveReadException(f"Filename has unexpected format: \"{filename}\"")

      if filename in self.members:
        raise ArchiveReadException(f"Filename appears in archive twice: \"{filename}\"")

    date = data_stream.read_ascii_integer(12)
    user_id = data_stream.read_ascii(6).rstrip(" ")
    group_id = data_stream.read_ascii(6).rstrip(" ")
    mode = data_stream.read_ascii_integer(8)
    size = data_stream.read_ascii_integer(10)
    endHeader = data_stream.read_bytes(2)

    if endHeader[0] != 0x60 or endHeader[1] != 0x0A:
      print(f"Warning: End of header is {repr(endHeader)} instead of 0x600A", file = sys.stderr)

    # Per source (2), `ar.h`:
    # Each  archive  file  member begins on an even byte boundary; a newline is inserted between
    # files if necessary. Nevertheless, the size given reflects the actual size of the file
    # exclusive of padding.
    if data_stream.cursor % 2 != 0:
      padding = data_stream.read_bytes(1)
      assert len(padding) == 1
      if padding[0] != ord("\n"):
        print(f"Warning: Padding is {repr(padding)} instead of a newline char", file = sys.stderr)

    content = data_stream.read_sub_stream(size)

    file = ArchiveReader.Member(
      name = filename,
      date = date,
      user_id = user_id,
      group_id = group_id,
      mode = mode,
      size = size,
      content = content
    )

    return file

  def load(self, data):
    data_stream = parse.BufferStream(data)

    magic = data_stream.read_bytes(8)
    if magic != b"!<arch>\n":
      raise ArchiveReadException(f"Bad magic number: {repr(magic)}")

    index_member = self._read_member(data_stream)
    if index_member.name != "/":
      raise ArchiveReadException(f"First member is unexpectedly named {index_member.name}")

    # Step 1: Catalog all the members in the library
    is_first_member_after_index = True
    member_name_by_offset = {}
    filename_member = None
    while data_stream.more_to_read():
      file_offset = data_stream.cursor
      member = self._read_member(data_stream, filename_member)

      if is_first_member_after_index:
        is_first_member_after_index = False
        if member.name == "/":
          # We don't need this member
          continue
        else:
          print("Warning: Second index appears to be missing", file = sys.stderr)
      if member.name == "//":
        if filename_member is None:
          filename_member = member
        else:
          print("Warning: Ignoring unexpected additional filename lookup member",
                file = sys.stderr)
        continue

      member_name_by_offset[file_offset] = member.name
      self.members[member.name] = member


    # Step 2: Parse the index.

    # First thing in the index file is the symbol count
    symbol_count = index_member.content.read_big_endian_dword()

    # Second thing in the index file is the array of member offsets
    member_offset_stream = index_member.content.read_sub_stream(4 * symbol_count)
    # Third thing in the index file is the list of the symbol names that the member at the
    # corresponding offset describes.
    # Note that the offsets are consecutive `DWORD`s while the symbol names are consecutive C
    # Strings (i.e. null byte delimited).
    symbol_name_stream = index_member.content.read_sub_stream()

    while member_offset_stream.more_to_read():
      member_offset = member_offset_stream.read_big_endian_dword()
      symbol_name = symbol_name_stream.read_cstring()

      member_name = member_name_by_offset[member_offset]
      if symbol_name in self.symbol_member_map:
        raise ArchiveReadException(
          "Oop, I guess this library needs to support symbols in multiple members"
        )
      self.symbol_member_map[symbol_name] = member_name
