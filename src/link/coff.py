# SPDX-License-Identifier: GPL-3.0-or-later

# Work in Progress - Mostly just some fragments of code I started to write as part of
# `ArchiveReader` but then decided they belonged in a different file.

# Parses the COFF file format to provide access to the data provided.

# File format sources:
# (1) https://web.archive.org/web/20100314154747/http://www.microsoft.com/whdc/system/platform/firmware/PECOFF.mspx

# TODO: Use this or remove it
def is_internal_lib_symbol(symbol_name):
  if symbol_name.startswith("__IMPORT_DESCRIPTOR_"):
    return True
  if symbol_name.startswith("__NULL_IMPORT_DESCRIPTOR"):
    return True
  return "_NULL_THUNK_DATA" not in symbol_name


# This is a bit similar to `IMAGE_FILE_HEADER` in `winnt.h`.
ImageMember = namedtuple("ImageMember", ["machine", "timestamp", "symbol_table_pointer",
                                         "characteristics"]) # TODO: sections, symbols, optional header

# This is a bit similar to `IMAGE_SECTION_HEADER` in `winnt.h`.
# TODO