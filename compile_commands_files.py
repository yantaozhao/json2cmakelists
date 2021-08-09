import sys
import os
import json
import re
import subprocess
import argparse


def loadCompilecommandsJson(jsonfile: str) -> dict:
    with open(jsonfile, encoding='utf-8') as fd:
        js = json.load(fd)
    return js


def changeCompilerCommand(cmdline: str) -> str:
    """
    add -MM, delete -o
    """
    # if cmdline.find('\\') >= 0:
    #     raise Exception('\\ found in cmdline: {}'.format(cmdline))
    parts = cmdline.split()

    o_idx = -1
    o_n = 0
    for i, p in enumerate(parts):
        if p == '-o':
            o_idx = i
            o_n += 1
    if o_n > 1:
        raise Exception('multi -o found: {}'.format(cmdline))
    if o_idx >= 0:
        assert o_idx != 0, '-o at the head of: {}'.format(cmdline)
        parts[o_idx] = ''
        parts[o_idx+1] = ''

    parts.insert(1, '-MM')
    cmdline2 = ' '.join(parts)
    return cmdline2


def runCmd(cmdline: str, env: dict = None) -> str:
    cp = None
    if env and len(env):
        cp = subprocess.run(cmdline, shell=True, check=True, capture_output=True, text=True, env=env)
    else:
        cp = subprocess.run(cmdline, shell=True, check=True, capture_output=True, text=True,)
    return cp.stdout


def extractFilesFromMakeRule(rule: str) -> dict:
    """
    make's rule -> dict
    """
    dic = {
        'target': '',
        'src': '',
        'include': []
    }

    assert len(re.findall(':', rule)) == 1, rule

    colon = rule.find(':')
    target = rule[:colon].strip()
    others = rule[colon+1:].strip()

    parts = re.split(r'\s+|\\', others)
    parts = list(filter(lambda f: len(f), map(lambda p: p.strip(), parts)))

    dic['target'] = target
    dic['src'] = parts[0]  # FIXME: is the 1st file really the source code?
    dic['include'] = parts[1:]
    return dic


def mainImpl(cwd: str, cc_json_file: str, output_file: str,
             paths_unique: bool = True, paths_compact: bool = True, path_abs: bool = True):
    cwd0 = cwd
    os.chdir(cwd)
    exists = set()
    exts = set()  # file extension

    js = loadCompilecommandsJson(cc_json_file)
    with open(output_file, mode='w+', encoding='utf-8') as fd:
        for ji, dic in enumerate(js, start=1):
            print('{}/{}'.format(ji, len(js)))
            cur_dir = dic['directory']
            cur_fil = dic['file']
            cur_cmd = dic.get('command')
            if not cur_cmd:
                cur_cmd = ' '.join(dic.get('arguments'))

            if not os.path.isabs(cur_dir):
                cur_dir = os.path.abspath(os.path.join(cwd0, cur_dir))
            if cwd != cur_dir:
                os.chdir(cur_dir)
                cwd = cur_dir

            if not os.path.isabs(cur_fil):
                cur_fil = os.path.abspath(os.path.join(cur_dir, cur_fil))
            if cur_fil.find('\\') >= 0:
                print('Warning: \\ found in path, result maybe incorrect: {}'.format(cur_fil))
            cur_fil_dir = os.path.dirname(cur_fil)

            cmdline = changeCompilerCommand(cur_cmd)
            rule = runCmd(cmdline)
            rule_dic = extractFilesFromMakeRule(rule)

            # get src and include files
            srcs: list = [cur_fil, rule_dic['src']]
            includes: list = rule_dic['include']

            srcs = map(lambda s: s if os.path.isabs(s) else os.path.abspath(os.path.join(cur_dir, s)), srcs)
            srcs = list(set(srcs))
            assert len(srcs) == 1, '{} duplicated!'.format(srcs)  # to check or not?

            if includes:
                includes = list(map(lambda h: h if os.path.isabs(h) else os.path.abspath(os.path.join(cur_fil_dir, h)), includes))

            # write path of src and include files
            for f in srcs+includes:
                ext = os.path.splitext(f)[-1]
                if ext:
                    exts.add(ext)

                if paths_unique:
                    if f in exists:
                        continue
                    else:
                        exists.add(f)
                # TODO: relative path
                print(f, file=fd)
            if not paths_compact:
                print('', file=fd)  # empty line

    print('file extensions: {}'.format(sorted(exts)))


def main(args):
    cwd = os.getcwd()

    compile_commands_json_file = args.input
    output_file = args.output
    paths_unique = True
    paths_compact = True
    path_abs = True

    compile_commands_json_file = os.path.abspath(os.path.join(cwd, compile_commands_json_file))

    if os.path.exists(output_file) and os.path.isfile(output_file):
        while True:
            yn = input('{} already exist! Overwrite?[y/N]:'.format(output_file))
            if yn in ('y', 'Y',):
                break
            if yn in ('n', 'N', '',):
                print('exit.')
                sys.exit()
            print('make a choice...')
    output_file = os.path.abspath(os.path.join(cwd, output_file))

    if args.paths == 'unique':
        paths_unique = True
    elif args.paths == 'full':
        paths_unique = False
    else:
        raise Exception('unknown value: {}'.format(args.paths))

    if args.no_compact_paths:
        paths_compact = False
    else:
        paths_compact = True

    if args.path_style == 'absolute':
        path_abs = True
    elif args.path_style == 'relative':
        path_abs = False
    else:
        raise Exception('unknown value: {}'.format(args.path_style))

    json_cwd = os.path.dirname(compile_commands_json_file)

    print('input:', compile_commands_json_file)
    mainImpl(cwd=json_cwd, cc_json_file=compile_commands_json_file, output_file=output_file,
             paths_unique=paths_unique, paths_compact=paths_compact, path_abs=path_abs)
    print('output:', output_file)


def parse_args():
    desc = r"""
SYNOPSIS: get all src and included files, by adding `-MM` options to compiler and parse the output.
Supported compilers: gcc/g++, clang/clang++"""
    ap = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input', type=str, default='compile_commands.json', nargs='?',
                    help='path to {0}. [default: {0}]'.format('compile_commands.json'))
    ap.add_argument('output', type=str, default='compile_commands_filelist.txt', nargs='?',
                    help='path to result file. [default: compile_commands_filelist.txt]')
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
