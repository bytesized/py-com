# SPDX-License-Identifier: GPL-3.0-or-later
from . import util

# Parsing utilities

class BufferStreamIndexError(Exception):
  pass

class BufferStream:
  """
    Basically a buffer and a cursor. When data is pulled out of the buffer,
    the cursor is advanced past it.

    All `read_` methods with a `length` parameter retrieve the rest of the data available if
    `length is None`.
  """

  def __init__(self, data, cursor = 0):
    self.data = data
    self.cursor = cursor

  def more_to_read(self):
    return self.cursor < len(self.data)

  def seek(self, position):
    if position is not None:
      self.cursor = position

  def _new_cursor(self, length):
    if length is None:
      return len(self.data)
    return self.cursor + length

  def read_bytes(self, length = None, seek = None):
    self.seek(seek)
    new_cursor = self._new_cursor(length)
    result = self.data[self.cursor:new_cursor]
    if length is not None and len(result) != length:
      raise BufferStreamIndexError(f"Insufficient data in buffer to return {length} bytes")
    self.cursor = new_cursor
    return result

  def read_ascii(self, length = None, seek = None):
    return self.read_bytes(seek = seek, length = length).decode("utf-8")

  def read_ascii_integer(self, length = None, seek = None):
    return int(self.read_ascii(seek = seek, length = length))

  def read_big_endian_dword(self, seek = None):
    return util.parse_big_endian(self.read_bytes(seek = seek, length = 4))

  def read_cstring(self, seek = None):
    self.seek(seek)

    if not self.more_to_read():
      raise BufferStreamIndexError(f"Unable to read from buffer - no more to read")

    string_end_offset = self.cursor
    while self.data[string_end_offset] != 0:
      if string_end_offset > len(self.data):
        raise BufferStreamIndexError(f"End of C String not found within the buffer")
      string_end_offset += 1

    # Skip the null byte but do not include it in the returned value
    new_cursor = string_end_offset + 1
    result = self.data[self.cursor:string_end_offset].decode("utf-8")
    self.cursor = new_cursor
    return result

  def read_sub_stream(self, length = None, seek = None):
    self.seek(seek)
    new_cursor = self._new_cursor(length)
    result = BufferStream(self.data[self.cursor:new_cursor])
    self.cursor = new_cursor
    return result

  def clone(self, reset = False):
    args = [self.data]
    if not reset:
      args.append(self.cursor)
    return BufferStream(*args)
