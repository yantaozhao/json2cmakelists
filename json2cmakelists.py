# -*- coding: utf-8 -*-

import sys
import os.path
import getopt
import json
import shlex


# # Get the path in _style_ form
# # @path:
# # @style: normal / relative / absolute
# # @relativeTo:
# def getPathOf(path, style=None, relativeTo=None):
#     p = None
#     if style in ('normal'):
#         p = os.path.normpath(os.path.expanduser(path))
#     elif style in ('relative'):
#         pass
#     elif style in ('absolute'):
#         pass
#     else:
#         print('WARN: unrecognized parameter! @', sys._getframe().f_code.co_name, ':', sys._getframe().f_lineno, sep='')
#
#     if p is None:
#         print('WARN: use original path! @', sys._getframe().f_code.co_name, ':', sys._getframe().f_lineno, sep='')
#         return path
#     else:
#         return p


class CompilationDatabaseTranslator(object):
    def __init__(self):
        # json data
        self.db = []
        # https://gcc.gnu.org/onlinedocs/gcc/Directory-Options.html
        # directories to be searched for include header:
        # 1. .                   : #include "file".
        # 2. -iquote, -Ixxx -I-  : #include "file".  [NO]
        # 3. -I                  : both #include "file" and #include <file>.
        # 4. -isystem            : both #include "file" and #include <file>.
        # 5. standard system dir : both #include "file" and #include <file>.
        # 6. -idirafter          : both #include "file" and #include <file>.  [NO]
        # NOTICE: [NO], i.e. -iquote and -idirafter, have no equivalent cmake-command.
        # so I put these two in options as a workaround.
        self.target_options = []
        self.target_defines = []
        # self.target_include_iquote = []
        self.target_include_I = []
        self.target_include_isystem = []
        # self.target_include_idirafter = []

    def load(self, fd):
        self.db = json.load(fd)

    def store(self, fd, toDirectory=None):
        fd.write(json.dumps(self.db, sort_keys=True, indent=4))

    # Format the command entry to _style_.
    # @style: command/arguments
    def format_command_entry_to(self, style=None):
        if style in ('command'):
            old = 'arguments'
            new = 'command'
            for item in self.db:
                if old in item:
                    value = ' '.join(item[old])
                    del item[old]
                    item[new] = value
        elif style in ('arguments'):
            old = 'command'
            new = 'arguments'
            for item in self.db:
                if old in item:
                    value = shlex.split(item[old])
                    del item[old]
                    item[new] = value
        else:
            print('WARN: unrecognized parameter! @', sys._getframe().f_code.co_name, ':', sys._getframe().f_lineno,
                  sep='')

    # # Format the paths in _entry_'s value to _style._
    # # In practice, the directory's value is always absolute, so others can be relative to it.
    # # @entry: command/arguments/directory/file/all
    # # @style: absolute/relative
    # def format_paths_style(self, entry='all', style=None):
    #     if style in ('absolute'):
    #         for item in self.db:
    #             if entry in ('command', 'arguments'):
    #                 # TODO
    #                 pass
    #             elif entry in ('file'):
    #                 # path = os.path.normpath(os.path.expanduser(item['directory'] + '/' + item['file']))
    #                 path = os.path.normpath(os.path.expanduser(item['file']))
    #                 if path not exist:
    #                     path = os.path.normpath(os.path.expanduser(os.path.join(item['directory'], item['file'])))
    #                 del item['file']
    #                 item['file'] = path
    #             elif entry in ('directory'):
    #                 pass
    #             else:
    #                 pass
    #     elif style in ('relative'):  # relative to directory
    #         for item in self.db:
    #             pass
    #     else:
    #         pass


    def convert_db_to_cmakelists(self, fd):
        cwd = os.getcwd()
        for item in self.db:
            if item['directory'] != cwd:
                print('WARN: directory=%s, file=%s is NOT relative to CWD!' % (item['directory'], item['file']))
        cwd = None

        cmakelists_header = """\
cmake_minimum_required(VERSION 2.8.12)
project(autogenerated)
#SET(CMAKE_EXPORT_COMPILE_COMMANDS ON)
"""
        fd.write(cmakelists_header)
        fd.write('\n')

        seq_num = 0
        for item in self.db:
            seq_num += 1
            cmdvalue = None
            self.target_options = []
            self.target_defines = []
            self.target_include_I = []
            self.target_include_isystem = []
            if 'command' in item:
                cmdvalue = shlex.split(item['command'])
            elif 'arguments' in item:
                if isinstance(item['arguments'], list):
                    cmdvalue = item['arguments']
                    # for i in range(len(cmdvalue)):
                    #     cmdvalue[i] = cmdvalue[i].strip()  # remove leading and trailing whitespaces
                else:
                    print('Error: value of entry arguments is not list type!')
            else:
                print('Error: no commands entry found! @', sys._getframe().f_code.co_name, ':',
                      sys._getframe().f_lineno, sep='')

            del cmdvalue[0]  # remove the beginning cc/c++
            iquote_flag = False
            for i in reversed(range(len(cmdvalue))):
                if cmdvalue[i] == item['file'].strip():
                    # del cmdvalue[i]
                    cmdvalue[i] = ''  # leave an empty hole there
                elif cmdvalue[i] == '-o':
                    cmdvalue[i + 1] = ''
                    cmdvalue[i] = ''
                elif cmdvalue[i] == '-c':
                    cmdvalue[i] = ''
                elif cmdvalue[i] == '-I-':
                    iquote_flag = True
                    cmdvalue[i] = ''
                elif cmdvalue[i] == '-I' and cmdvalue[i + 1] == '-':
                    iquote_flag = True
                    cmdvalue[i + 1] = ''
                    cmdvalue[i] = ''
                elif cmdvalue[i].startswith('-I') and iquote_flag:
                    cmdvalue[i].replace('-I', '-iquote', 1)  # treat those -Ixxx before -I- as -iquote

            i = -1
            cmdvalue_len = len(cmdvalue)
            while True:
                i += 1
                if i >= cmdvalue_len:
                    break  # yeah, i as index, c++ for() style. ugly but work, ha~ :-)

                # include
                if cmdvalue[i] == '-iquote':
                    self.target_options.append(cmdvalue[i])
                    i += 1
                    self.target_options.append(cmdvalue[i])
                elif cmdvalue[i].startswith('-iquote'):
                    self.target_options.append(cmdvalue[i])
                elif cmdvalue[i] == '-I':
                    i += 1
                    self.target_include_I.append(cmdvalue[i])
                elif cmdvalue[i].startswith('-I'):
                    self.target_include_I.append(cmdvalue[i][2:])
                elif cmdvalue[i] == '-isystem':
                    i += 1
                    self.target_include_isystem.append(cmdvalue[i])
                elif cmdvalue[i].startswith('-isystem'):
                    self.target_include_isystem.append(cmdvalue[i][8:])
                elif cmdvalue[i] == '-idirafter':
                    self.target_options.append(cmdvalue[i])
                    i += 1
                    self.target_options.append(cmdvalue[i])
                elif cmdvalue[i].startswith('-idirafter'):
                    self.target_options.append(cmdvalue[i])
                # define
                elif cmdvalue[i] == '-D':
                    i += 1
                    self.target_defines.append(cmdvalue[i])
                elif cmdvalue[i].startswith('-D'):
                    self.target_defines.append(cmdvalue[i][2:])
                # others
                elif len(cmdvalue[i]) != 0:
                    self.target_options.append(cmdvalue[i])

            # Then, write one item to file
            fd.write('add_library(target_xxxxxx_%d OBJECT\n' % seq_num)
            # TODO: if directory entry is not CWD, adjust file path
            fd.write('    %s\n' % item['file'])
            fd.write(')\n')

            if len(self.target_options) > 0:
                fd.write('target_compile_options(target_xxxxxx_%d PRIVATE\n' % seq_num)
                for v in self.target_options:
                    fd.write('    %s\n' % v)
                fd.write(')\n')

            if len(self.target_defines) > 0:
                fd.write('target_compile_definitions(target_xxxxxx_%d PRIVATE\n' % seq_num)
                for v in self.target_defines:
                    fd.write('    %s\n' % v)
                fd.write(')\n')

            if len(self.target_include_I) > 0:
                fd.write('target_include_directories(target_xxxxxx_%d PRIVATE\n' % seq_num)
                for v in self.target_include_I:
                    fd.write('    %s\n' % v)
                fd.write(')\n')

            if len(self.target_include_isystem) > 0:
                fd.write('target_include_directories(target_xxxxxx_%d SYSTEM PRIVATE\n' % seq_num)
                for v in self.target_include_isystem:
                    fd.write('    %s\n' % v)
                fd.write(')\n')
            fd.write('\n')


def usage():
    hlp = """
Convert JSON Compilation Database compile_commands.json to CMakeLists.txt

SYNOPSIS:
json2cmakelists [-i compile_commands.json] [-o CMakeLists.txt]

OPTIONS:
-i        : JSON Compilation Database file. default: compile_commands.json
-o        : CMake listfiles. default: CMakeLists.txt
-h  --help: print this help and exit
"""
    print(hlp)


def main():
    database_file = 'compile_commands.json'
    cmakelists_file = 'CMakeLists.txt'

    # parse command line args
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hi:o:', ['help'])
    except getopt.GetoptError as err:
        print('Error: %s!' % err)
        sys.exit(2)
    for o, a in opts:
        if o == '-i':
            database_file = a
        elif o == '-o':
            cmakelists_file = a
        elif o in ('-h', '--help'):
            usage()
            sys.exit()

    # check files existence
    if os.path.isfile(database_file):
        if os.path.dirname(os.path.realpath(database_file)) != os.getcwd():
            print('Error: please run this script in the same dir of compile_commands.json')
            sys.exit()
    else:
        print('Error: %s not exist!' % database_file)
        sys.exit()
    if os.path.isfile(cmakelists_file):
        i = input('%s already exist, overwrite it? [y/N]:' % cmakelists_file)
        if i.lower() not in ('y', 'yes'):
            print('nothing done, exit.')
            sys.exit()

    # run
    translator = CompilationDatabaseTranslator()

    with open(database_file, mode='r') as infd:
        translator.load(infd)

    # translator.format_command_entry_to('command')
    # translator.format_paths_style('file', 'absolute')

    with open(cmakelists_file, mode='w') as outfd:
        translator.convert_db_to_cmakelists(outfd)


if __name__ == '__main__':
    main()