import argparse
import os
from pathlib import Path
import re


def filter_d_files(d_files: list[Path]):
    """
    check: stem.d + stem.*
    """
    files: list[Path] = []
    for fil in d_files:
        parent = fil.parent
        stem = fil.stem
        if len(list(parent.glob(f'{stem}.*'))) >= 2:
            files.append(fil)
        else:
            print(f'!!!orphan: {fil}')
    return files


def parse_d_file(dfile: Path):
    td = {}
    try:
        with open(dfile, encoding='utf-8') as fd:
            text = fd.read()
        parentdir = dfile.parent
        matches: list[str] = re.findall(r'^\s*(.+?:.*?[^\\])\s*$', text, flags=re.MULTILINE | re.DOTALL)
        for m in matches:
            parts = m.split(':', maxsplit=1)
            target = parts[0].strip()
            dependencies = parts[1].strip()
            deps = re.split(r'\s*\\\s*\n\s*|\s+', dependencies)
            deps = list(map(lambda x: x if os.path.isabs(x) else os.path.normpath(os.path.join(parentdir, x)), deps))
            td[target] = deps
    except Exception as e:
        print('!!!parse:', dfile, type(e), e)
    return td


def get_dependencies_from_dfiles(dfiles: list[Path]):
    deps = set()
    for dfile in dfiles:
        td = parse_d_file(dfile)
        for t, d in td.items():
            deps |= set(d)
    return deps


def main():
    """
    parse make's *.d files generated by compiler with `-MD` or `-MMD` option.

    See: https://gcc.gnu.org/onlinedocs/gcc/Preprocessor-Options.html
    """
    parser = argparse.ArgumentParser('Get all dependencies from *.d rule files')
    parser.add_argument('sourcetree_root', default='.', nargs='?', type=str, help='root folder of source tree')
    parser.add_argument('-o', '--output', type=str, default='output_d_dependencies.txt', help='result output file')
    args = parser.parse_args()
    print(vars(args))

    sourcetree_root = os.path.abspath(args.sourcetree_root)
    assert os.path.exists(sourcetree_root)

    all_dfiles = sorted(Path(sourcetree_root).rglob('*.d'))
    all_dfiles = filter_d_files(all_dfiles)

    deps = get_dependencies_from_dfiles(all_dfiles)
    print(f"dependencies: {len(deps)}")

    print(f'writing result under: {Path(os.getcwd(), args.output).parent}')
    with open(args.output, mode='w', encoding='utf-8') as fd:
        deps = sorted(deps)
        for dep in deps:
            print(dep, file=fd)


if __name__ == "__main__":
    main()
