#!/usr/bin/env python3
import os
import json
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    retcode: int
    stdout: str
    stderr: str

def generate_eval_command(lang, interpreter, code, *args):
    match lang:
        case 'python':
            cmd = [interpreter or 'python', '-c']
        case 'javascript':
            cmd = [interpreter or 'node', '-e']
        case _:
            raise ValueError(f"Unsupported language: {lang}")
    return cmd + [code] + list(args)


def merge_environments(base_envs, new_envs):
    """Merge new_envs into base_envs, prepending PATH-style values with the platform path separator."""
    sep = os.pathsep
    # On Windows, env vars are case-insensitive but os.environ.copy()
    # returns a case-sensitive dict (e.g. key is 'Path' not 'PATH').
    # We must match the existing key's case to avoid creating duplicates
    # that confuse CreateProcess (which only honours the first occurrence).
    if os.name == 'nt':
        upper_to_key = {k.upper(): k for k in base_envs}
    for key, new_val in new_envs.items():
        if os.name == 'nt':
            key = upper_to_key.get(key.upper(), key)
        existing = base_envs.get(key, '')
        base_envs[key] = f"{new_val}{sep}{existing}" if existing else new_val
    return base_envs


def get_base_code(inputs, lang):
    generators = {'python': _get_py_base_code, 'javascript': _get_js_base_code}
    if lang not in generators:
        raise ValueError(f"Unsupported language: {lang}")
    return generators[lang](inputs)


def _get_py_base_code(inputs):
    hex_inputs = json.dumps(inputs).encode('utf8').hex()
    return f'''
import json, sys
code = sys.argv[1]
exec(code)
args = Args(json.loads(bytes.fromhex('{hex_inputs}').decode('utf8')))
res = main(args)
res = json.dumps(res).encode('ascii')
print(f"\\n[[output]]{{res.hex()}}[[output]]", end='')
'''


def _get_js_base_code(inputs):
    hex_inputs = json.dumps(inputs).encode('utf8').hex()
    return f'''
const code = process.argv[1] + '\\n;return {{ ArgsCls: Args, main_func: main }};';
const {{ ArgsCls, main_func }} = new Function(code)();
const args = new ArgsCls(JSON.parse(Buffer.from('{hex_inputs}', 'hex').toString('utf-8')));
let result = main_func(args);
process.stdout.write('\\n[[output]]' + Buffer.from(JSON.stringify(result)).toString('hex') + '[[output]]');
process.exit(0);
'''


def parse_result(output: str):
    tag = '[[output]]'
    last_line = output[output.rindex('\n') + 1:]
    if not last_line.startswith(tag) or not last_line.endswith(tag):
        raise ValueError(f'Corrupted code result: "{last_line}"')
    hex_data = last_line.split(tag)[1]
    return json.loads(bytes.fromhex(hex_data).decode('utf8'))
