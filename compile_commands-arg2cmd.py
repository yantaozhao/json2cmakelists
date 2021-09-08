# -*- coding: utf-8 -*-

import sys
import json
import time


compile_commands_postfix = f'{time.strftime("%Y-%m-%d_%H-%M-%S_%Z")}'


def usage():
    doc = """
Usage: convert compile_commands.json with `arguments` entry to `command` form.
    script.py compile_commands.json

Ref:
    https://clang.llvm.org/docs/JSONCompilationDatabase.html
    https://releases.llvm.org/4.0.0/tools/clang/docs/JSONCompilationDatabase.html
"""
    print(doc)


def getOutputPath(path: str):
    newname = f'{path}.{compile_commands_postfix}'
    return newname


def cvtCompileCommandsArg2cmd(inputjson_path: str, outputjson_path: str):
    with open(inputjson_path, encoding='utf-8') as fi, open(outputjson_path, mode='w+', encoding='utf-8') as fo:
        j = json.load(fi)

        fo.write('[\n')
        for n, unit in enumerate(j):
            item = {
                'directory': unit['directory'],
                'command': ' '.join(unit['arguments']),  # arguments -> command
                'file': unit['file'],
            }
            if 'output' in unit:
                item.update({'output': unit['output']})
            s = json.dumps(item, indent=2)
            if n != 0:
                fo.write(',\n')
            fo.write(s)
        fo.write('\n]\n')


def main(argv):
    if len(argv) == 1:
        inputjson_path = 'compile_commands.json'  # default
    elif (len(argv) == 2) and (argv[1] not in ('-h', '--help')):
        inputjson_path = argv[1]
    else:
        usage()
        sys.exit()
    outputjson_path = getOutputPath(inputjson_path)

    cvtCompileCommandsArg2cmd(inputjson_path, outputjson_path)
    print(f'result: {inputjson_path} --> {outputjson_path}')


if __name__ == "__main__":
    main(sys.argv)
