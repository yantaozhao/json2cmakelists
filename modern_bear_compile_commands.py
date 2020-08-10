# -*- coding: utf-8 -*-

import sys
import json
import time


compile_commands_postfix = f'{time.strftime("%Y-%m-%d_%H-%M-%S_%Z")}'


def usage():
    doc = """
    Usage: convert Bear compile_commands.json to official modern form.
        script.py compile_commands.json
    """
    print(doc)


def getOutputPath(path: str):
    newname = f'{path}.{compile_commands_postfix}'
    return newname


def modernCompileCommandsForm(inputjson_path: str, outputjson_path: str):
    with open(inputjson_path, encoding='utf-8') as fi, open(outputjson_path, mode='w+', encoding='utf-8') as fo:
        j = json.load(fi)

        fo.write('[\n')
        for n, unit in enumerate(j):
            item = {
                'directory': unit['directory'],
                'command': ' '.join(unit['arguments']),  # arguments -> command
                'file': unit['file'],
            }
            s = json.dumps(item, indent=2)
            if n != 0:
                fo.write(',\n')
            fo.write(s)
        fo.write('\n]\n')


def main(argv):
    if len(argv) != 2:
        usage()
        sys.exit()

    inputjson_path = argv[1]
    outputjson_path = getOutputPath(inputjson_path)
    modernCompileCommandsForm(inputjson_path, outputjson_path)
    print(f'result: {outputjson_path}')


if __name__ == "__main__":
    main(sys.argv)
