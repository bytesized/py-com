# SPDX-License-Identifier: GPL-3.0-or-later

def parse_big_endian(be_bytes):
  result = 0
  for byte in be_bytes:
    result <<= 8
    result |= byte
  return result

def parse_little_endian(le_bytes):
  return parse_big_endian(reversed(le_bytes))

def wide_string(python_string):
  return python_string.encode("utf-16-le")
