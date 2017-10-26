# json2cmakelists

## Introduction

`json2cmakelists` is a tool that generates a ***CMakeLists.txt*** from [JSON compilation database](http://clang.llvm.org/docs/JSONCompilationDatabase.html) file ***compile_commands.json***.

A compilation database is a JSON file named *compile_commands.json*, which consist of an array of “command objects”, where each command object specifies one way a translation unit is compiled in the project.

*CMakeLists.txt* is the input to the CMake build system. It contains a set of directives and instructions describing the project's source files and targets, which control the build process.



## How to use

### Basic usage

Goto the directory which containing *compile_commands.json* file, and run this tool.

```sh
cd ${DIR_HAS_compile_commands.json}
json2cmakelists    # in PATH
```

Alternatively, if `json2cmakelists` is not in `PATH`, you can run it simply like this:

```sh
cd ${DIR_HAS_compile_commands.json}
python3 /path/to/json2cmakelists    # force using Python3
```

Done.



### Advanced usage

Default, the tool use *compile_commands.json* as input file, *CMakeLists.txt* as output file.

You can use options such as `-i file` and `-o file` to specify a different input / output file. Use `-h` or `--help` to see help info.

```sh
json2cmakelists -h    # print help
```



Of course, with the generated *CMakeLists.txt*, you can re-generate *compile_commands.json* again in canonical way using `cmake` as you like.



## Problem reports

This tool script is originally written under Python 3.5 on Linux.

If you find a bug, or would like to propose an improvement, please let me know. Patches are also welcome.

