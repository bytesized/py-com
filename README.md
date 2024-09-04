# py-com
There is a bit of a silly story behind this repository. I wanted to do something in Python that required COM. I poked around for COM packages and could only find one that I really didn't like. I wondered if I could just call into the things I wanted with `ctypes` instead of using a COM package at all. Then this turned into the plan for a COM package of my own. Then I discovered that [someone else](pypi.org/project/comtypes/) had already done very nearly exactly this.

I still hope to come back to this project at some point, because I felt like the exploration I did while I was looking into this was fascinating and I learned a lot. And also because I'm still not _really_ happy with the existing packages. I think that `comtypes` is the best option currently available, but I'm not excited about certain design choices. `CoUninitialize`, for example, runs at program exit and there seems to be no real way to make it run sooner without mismatching the init/uninit calls. Also, I _think_ that COM objects returned by `CreateObject` just need to be manually freed by calling `Release`? The documentation never really seems to mention releasing things, so I'm a bit unsure. But that's what I suspect after inspecting the source.

So I'm shelving this for now. Hopefully I'll come back to it soon.

---

Note to my future self for where to pick back up here:
`ar.py` is looking pretty good. You can pull a `.lib` out of the Windows SDK (for me, currently `C:\Program Files (x86)\Windows Kits\10\Lib\10.0.22621.0\um\x64`). Then you can demo that with
```
cd src
python3
>>> import link.ar
>>> a = link.ar.ArchiveReader()
>>> a.read_file("lib_path.lib")
>>> a.members
>>> a.symbol_member_map
```

The next chunk of the work is going to be in `coff.py` where I wanna build a parser for the COFF file format (see the source listed in that file for the spec).

I'm a little unsure about the path forward after that, but I suspect it might look something like:
 - Writing an IDL parser.
 - Write a "linker" that uses all the parsed COFF and IDL data to spit out something consumable by
   Python.
 - Write whatever consumes that "linker" data and uses it to construct interfaces that match the
   IDLs and can call methods from its vtable.
 - Write the base functions that basically wrap things like `CoInitializeEx` and
   `CoCreateInstance`.
 - Write some context managers that let us use `with` statements to ensure COM resources are
   cleaned up when desired.
 - Hopefully figure out a way to `Release` things when they go out of scope or are deleted.
