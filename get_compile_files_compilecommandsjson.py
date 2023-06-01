import argparse
import sys
import os
from pathlib import Path
import json
import shlex
import re
import shutil
import subprocess


g_is_posix = not sys.platform.casefold().startswith('win')


def _path_style(path: str):
    """
    determine path style.
    """
    if path.startswith('/'):
        return 'posix'
    if re.match(r'[A-Za-z]:', path):
        return 'nt'
    # if path.startswith(r'\\'):
    #     return 'unc'
    return None


def _parse_compile_commands_json(ccfile='compile_commands.json'):
    """
    absolute paths, and macros

    see:
      https://clang.llvm.org/docs/JSONCompilationDatabase.html
    """
    with open(ccfile, encoding='utf-8') as fd:
        js = json.load(fd)
        print(f'{ccfile} entries: {len(js)}')

        # source files
        all_files = []  # type:list[str]
        for dic in js:
            fil = dic['file']
            if not os.path.isabs(fil):
                fil = os.path.join(dic['directory'], fil)
            assert os.path.isabs(fil)

            if _path_style(fil) == 'posix':
                fil = Path(os.path.normpath(fil)).as_posix()
            else:
                fil = os.path.normpath(fil)
            all_files.append(fil)

        # macros
        all_macros = {}  # type:dict[str, int]
        _D = '-D'
        _U = '-U'
        if 'arguments' in js[0]:
            compile_commands = [dic['arguments'] for dic in js]  # type:list[list[str]]
        elif 'command' in js[0]:
            styles = [_path_style(dic['command']) for dic in js]
            style_posix = any(map(lambda x: x == 'posix', styles))
            style_nt = any(map(lambda x: x == 'nt', styles))
            assert not (style_posix and style_nt), 'compilers in posix and nt path style?'
            if style_posix:
                is_posix = True
            elif style_nt:
                is_posix = False
            else:
                is_posix = g_is_posix
            compile_commands = [shlex.split(dic['command'], posix=is_posix) for dic in js]
        else:
            compile_commands = []

        for cmdparts in compile_commands:
            for i, pa in enumerate(cmdparts):
                if not pa.startswith((_D, _U)):
                    continue
                macro = (pa + ' ' + cmdparts[i + 1]) if pa in (_D, _U) else pa
                macro = bytes(macro, 'utf-8').decode('unicode_escape')
                if macro not in all_macros:
                    all_macros[macro] = 1
                else:
                    all_macros[macro] += 1

        return all_files, all_macros


def _which_ninja():
    ninja = 'ninja'
    p = shutil.which(ninja)
    if p is not None:
        return ninja
    while True:
        p = input('where is ninja:').strip()
        if not p:
            break
        elif os.path.exists(p):
            return p
        else:
            print(f'"{p}" not exist!')
    return None


def _get_include_files_using_ninja(cmake_ninja_build_root_abs: str = None):
    """
    absolute paths.

    see:
      https://ninja-build.org/manual.html#ref_headers
      https://github.com/ninja-build/ninja/blob/v1.11.1/src/ninja.cc#L559
    """
    assert (cmake_ninja_build_root_abs is None) or os.path.isabs(cmake_ninja_build_root_abs)
    pwd = cmake_ninja_build_root_abs
    empty_ret = []

    ninja = _which_ninja()
    if not ninja:
        print('ninja command not found, ignore include files')
        return empty_ret

    try:
        cp = subprocess.run([ninja, '-t', 'deps'],
                            capture_output=True, cwd=pwd, check=True)
        deps_info = cp.stdout.decode('utf-8').split('\n')
    except Exception as e:
        print(type(e), e)
        return empty_ret

    include_files = set()
    if pwd is None:
        pwd = os.getcwd()
    for line in deps_info:
        if not line.startswith(' '):
            continue
        line = line.strip()
        if (not line) or re.search(r'.+?:\s*#deps\s+?\d+?.+?deps\s+?mtime\s', line):
            # TODO: skip the source file which is the next of #deps mark line
            continue

        if not os.path.isabs(line):
            line = os.path.join(pwd, line)
        assert os.path.isabs(line)
        if _path_style(line) == 'posix':
            line = Path(os.path.normpath(line)).as_posix()
        else:
            line = os.path.normpath(line)
        # same path maybe has posix or nt format
        include_files.add(line)
    return include_files


def get_source_files_and_macros():
    print('get sources files...')
    return _parse_compile_commands_json()


def get_include_files(cmakebuild_root: str = None):
    print('get include files...')
    if Path('.' if cmakebuild_root is None else cmakebuild_root).joinpath('.ninja_deps').exists():
        return _get_include_files_using_ninja(cmakebuild_root)
    else:
        # TODO: compile, use command adding '-MM' or '/showIncludes' option
        return []


def main():
    """
    parse compile_commands.json and .ninja_deps generated by ninja.
    """
    parser = argparse.ArgumentParser(description='Get all built sources and macros from cmake build databases')
    parser.add_argument('cmakebuild_root', type=str, help='root folder of cmake build')
    parser.add_argument('sourcetree_root', default='.', nargs='?', type=str, help='root folder of source tree')
    parser.add_argument('-p', '--output_prefix', type=str, default='output_compilecommands_', help="result filename's prefix")
    parser.add_argument('-a', '--all', action='store_true', help='all files including system files')
    args = parser.parse_args()
    print(f'posix: {g_is_posix}; {vars(args)}')

    old_dir = os.getcwd()
    cmakebuild_root = os.path.abspath(args.cmakebuild_root)
    sourcetree_root = os.path.abspath(args.sourcetree_root)
    assert os.path.exists(cmakebuild_root) and os.path.exists(sourcetree_root)

    source_files = []
    include_files = []
    macros = []

    try:
        os.chdir(cmakebuild_root)
        source_files, macros_dic = get_source_files_and_macros()
        macros = sorted(macros_dic.items(), key=lambda x: -x[1])
        include_files = get_include_files()
        print(f'result. sources:{len(source_files)}, includes:{len(include_files)}, macros:{len(macros)}')
    except Exception as e:
        print(type(e), e)
        raise
    else:
        os.chdir(sourcetree_root)
        print(f'writing result under: {sourcetree_root}')
        output_filelist_txt = f'{args.output_prefix}files.txt'
        output_macros_txt = f'{args.output_prefix}macros.txt'
        if os.path.exists(output_filelist_txt) or os.path.exists(output_macros_txt):
            while True:
                yn = input(f'{output_filelist_txt} or {output_macros_txt} already exists! Overwrite?[y/n]:').strip().casefold()
                if yn in ('y', 'yes'):
                    if not macros:
                        Path(output_macros_txt).unlink(missing_ok=True)
                    print('overwriting...')
                    break
                elif yn in ('n', 'no'):
                    print('quit.')
                    sys.exit()
                else:
                    continue

        exists = set()
        with open(output_filelist_txt, mode='w', encoding='utf-8') as fd:
            # files
            for fil in source_files:
                exists.add(fil)
                # fil = os.path.relpath(fil, sourcetree_root)
                print(fil, file=fd)

            print('', file=fd)

            # sorted deps
            tmp = set()
            for fil in include_files:
                if fil in exists:
                    continue
                if not args.all:
                    # only in-sourcetree files
                    if not fil.startswith(sourcetree_root):
                        continue
                exists.add(fil)
                # fil = os.path.relpath(fil, sourcetree_root)
                tmp.add(fil)
            tmp = sorted(tmp)
            for fil in tmp:
                print(fil, file=fd)

        if macros:
            with open(output_macros_txt, mode='w', encoding='utf-8') as fd:
                delim = '\t\t'
                print(f'<MACRO>{delim}<COUNT>', file=fd)
                for macro_cnt in macros:
                    line = delim.join(map(str, macro_cnt))
                    print(line, file=fd)
    finally:
        os.chdir(old_dir)
        print('done.')


if __name__ == "__main__":
    main()
