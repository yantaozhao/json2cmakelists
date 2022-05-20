import sys
import os
import json
import re
import shlex
import subprocess
import argparse
from pathlib import Path


def loadCompilecommandsJson(jsonfile: str) -> dict:
    with open(jsonfile, encoding='utf-8') as fd:
        js = json.load(fd)
    return js


def changeCompilerCommand(cmdline):
    """
    delete -o, add -MM
    """
    if isinstance(cmdline, (list, tuple)):
        arguments = list(cmdline)  # type: list
    elif isinstance(cmdline, str):
        arguments = shlex.split(cmdline)
    else:
        raise Exception("unknown command")

    # find -o, erase it
    o_idx = -1
    o_cnt = 0
    for i, a in enumerate(arguments):
        if a == '-o':
            o_idx = i
            o_cnt += 1
    if o_cnt > 1:
        raise Exception('multi -o found: {}'.format(cmdline))
    if o_idx >= 0:
        assert o_idx != 0, '-o at the head of: {}'.format(cmdline)
        arguments[o_idx] = ''
        arguments[o_idx + 1] = ''

    # add -MM
    arguments.insert(1, '-MM')
    arguments = list(filter(lambda p: p.strip(), arguments))

    cmdline2 = shlex.join(arguments)  # type:str
    return cmdline2, arguments


def getDefinitionFromArguments(argument: list):
    """
    get define from -Dxxx

    :param argument:
    :return: ['xxx', 'xxx=yyy']
    """
    defines = []
    i, arg_len = 0, len(argument)
    while i < arg_len:
        a = argument[i].strip()  # type:str
        """
        cases:
            -Dxxx
            -D xxx
            -Dxxx=yyy
            -D xxx=yyy
            -D xxx = yyy  # TODO:is this case exists?
        """
        d = None
        if a == '-D':
            i += 1
            d = argument[i].strip()
        elif a.startswith('-D'):
            d = a[2:]

        if d:
            defines.append(d)
        i += 1
    return defines


def runCmd(cmdline: str, env: dict = None) -> str:
    cp = None
    if env and len(env):
        cp = subprocess.run(cmdline, shell=True, check=True, capture_output=True, text=True, env=env)
    else:
        cp = subprocess.run(cmdline, shell=True, check=True, capture_output=True, text=True, )
    return cp.stdout


def extractFilesFromMakeRule(rule: str) -> dict:
    """
    make's rule -> dict
    """
    dic = {
        'target':  '',
        'src':     '',
        'include': []
    }

    assert len(re.findall(':', rule)) == 1, rule

    colon = rule.find(':')
    target = rule[:colon].strip()
    others = rule[colon + 1:].strip()

    parts = shlex.split(others)  # split file lists
    parts = list(filter(lambda f: len(f), map(lambda p: p.strip(), parts)))

    dic['target'] = target
    dic['src'] = parts[0]  # FIXME: is the 1st file really the source code?
    dic['include'] = parts[1:]
    return dic


def mainImpl(cwd: str, cc_json_file: str, output_filelist: str, output_definition: str,
             paths_unique: bool = True, paths_compact: bool = True, path_abs: bool = True):
    """

    :param cwd:
    :param cc_json_file:
    :param output_filelist: output file for filelist
    :param output_definition: output file for definition
    :param paths_unique:
    :param paths_compact:
    :param path_abs:
    :return:
    """
    cwd0 = cwd  # absolute path
    os.chdir(cwd)
    exists = set()
    extentions = set()  # file extension
    definitions = []

    js = loadCompilecommandsJson(cc_json_file)
    with open(output_filelist, mode='w+', encoding='utf-8') as fd_f:
        for ji, dic in enumerate(js, start=1):
            print('{}/{}'.format(ji, len(js)))

            cur_dir = dic['directory']
            cur_fil = dic['file']
            cur_cmd = dic.get('command')  # type: str
            if not cur_cmd:
                cur_cmd = dic.get('arguments')  # type: dict
            assert os.path.exists(cur_dir) and os.path.exists(cur_fil), f"{cur_dir} or {cur_fil} not exist!"

            # respect to current command and directory
            if not os.path.isabs(cur_dir):
                cur_dir = os.path.abspath(os.path.join(cwd0, cur_dir))
            if cwd != cur_dir:
                try:
                    os.chdir(cur_dir)
                    cwd = cur_dir
                except:
                    print(f"chdir to {cur_dir} fail!")
                    raise

            if not os.path.isabs(cur_fil):
                cur_fil = os.path.abspath(os.path.join(cur_dir, cur_fil))
            # if cur_fil.find('\\') >= 0:
            #     print('Warning: \\ found in path, result maybe incorrect: {}'.format(cur_fil))
            cur_fil_dir = os.path.dirname(cur_fil)

            # tweak command line
            cmdline, argument = changeCompilerCommand(cur_cmd)

            # definitions
            defines = getDefinitionFromArguments(argument)
            defines = filter(lambda x: x not in definitions, defines)
            definitions.extend(defines)

            # run it by compiler
            rule = runCmd(cmdline)
            rule_dic = extractFilesFromMakeRule(rule)

            # get src and include files
            srcs = [cur_fil, rule_dic['src']]
            includes: list = rule_dic['include']

            srcs = map(lambda s: s if os.path.isabs(s) else os.path.abspath(os.path.join(cur_dir, s)), srcs)
            srcs = list(set(srcs))
            assert len(srcs) == 1, '{} duplicated!'.format(srcs)  # to check or not?

            if includes:
                includes = list(map(lambda h: h if os.path.isabs(h) else os.path.abspath(os.path.join(cur_fil_dir, h)), includes))

            # write path of src and include files
            for f in srcs + includes:
                ext = os.path.splitext(f)[-1]
                if ext:
                    extentions.add(ext)

                if paths_unique:
                    if f in exists:
                        continue
                    else:
                        exists.add(f)
                # TODO: relative path
                print(f, file=fd_f)
            if not paths_compact:
                print('', file=fd_f)  # empty line
    with open(output_definition, mode='w+', encoding='utf-8') as fd_d:
        print('\n'.join(definitions), file=fd_d)

    print('all file extensions: {}'.format(sorted(extentions)))


def main(args):
    cwd = os.getcwd()
    print(f"cwd: {cwd}")

    opt_compile_commands_json = args.input
    __compile_commands_json_path = Path(opt_compile_commands_json)
    opt_output_filelist = os.path.join(__compile_commands_json_path.parent, __compile_commands_json_path.stem + "-filelist.txt")
    opt_output_definition = os.path.join(__compile_commands_json_path.parent, __compile_commands_json_path.stem + "-definition.txt")
    opt_paths_unique = True
    opt_paths_compact = True
    opt_path_abs = True

    if not os.path.exists(opt_compile_commands_json):
        raise Exception(f"{opt_compile_commands_json} not exist!")

    if os.path.exists(opt_output_filelist) or os.path.exists(opt_output_definition):
        while True:
            yn = input('{} or {} already exist! Overwrite?[y/N]:'.format(opt_output_filelist, opt_output_definition))
            if yn in ('y', 'Y',):
                break
            if yn in ('n', 'N', '',):
                print('exit.')
                sys.exit()
            print('make a choice...')
    opt_compile_commands_json = os.path.abspath(os.path.join(cwd, opt_compile_commands_json))
    opt_output_filelist = os.path.abspath(os.path.join(cwd, opt_output_filelist))
    opt_output_definition = os.path.abspath(os.path.join(cwd, opt_output_definition))

    if args.paths == 'unique':
        opt_paths_unique = True
    elif args.paths == 'full':
        opt_paths_unique = False
    else:
        raise Exception('unknown value: {}'.format(args.paths))

    if args.no_compact_paths:
        opt_paths_compact = False
    else:
        opt_paths_compact = True

    if args.path_style == 'absolute':
        opt_path_abs = True
    elif args.path_style == 'relative':
        opt_path_abs = False
    else:
        raise Exception('unknown value: {}'.format(args.path_style))

    json_cwd = os.path.dirname(opt_compile_commands_json)

    print('input:', opt_compile_commands_json)
    mainImpl(cwd=json_cwd, cc_json_file=opt_compile_commands_json,
             output_filelist=opt_output_filelist, output_definition=opt_output_definition,
             paths_unique=opt_paths_unique, paths_compact=opt_paths_compact, path_abs=opt_path_abs)
    print('output:', opt_output_filelist)
    print('output:', opt_output_definition)


def parse_args():
    desc = r"""
SYNOPSIS: get all src and included files, by adding `-MM` options to compiler and parse the output.
Supported compilers: gcc/g++, clang/clang++
"""
    ap = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input', type=str, default='compile_commands.json', nargs='?',
                    help='path to {0}. [default: {0}]'.format('compile_commands.json'))
    ap.add_argument('--paths', type=str, choices=['unique', 'full'], default='unique',
                    help='control if the output content paths can be duplicated. [default: unique]')
    ap.add_argument('--no-compact-paths', action='store_true',
                    help='insert an empty line between path groups in content.')
    ap.add_argument('--path-style', type=str, choices=['absolute', 'relative'], default='absolute',
                    help="the style file's path in content. [default: absolute]. (NOT implemented)")
    args = ap.parse_args()
    return args


if __name__ == '__main__':
    main(parse_args())
