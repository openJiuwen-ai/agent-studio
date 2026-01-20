import json


def get_base_code(inputs, lang):
    if lang == 'python':
        return get_py_base_code(inputs)
    elif lang == 'javascript':
        return get_js_base_code(inputs)
    else:
        raise Exception(f"Unknown code language: {lang}")


def get_py_base_code(inputs):
    inputs = json.dumps(inputs).encode('utf8').hex()
    code = f'''
import json
import sys
code = sys.argv[1]
exec(code)
args = Args(json.loads(bytes.fromhex('{inputs}').decode('utf8')))
res = main(args)
res = json.dumps(res).encode('ascii')
print(f"\\n[[output]]{{res.hex()}}[[output]]", end='')
'''
    return code


def get_js_base_code(inputs):
    inputs = json.dumps(inputs).encode('utf8').hex()
    code = f'''
const code = process.argv[2] + `;return {{ ArgsCls: Args, main_func: main }};`
process.stdout.write(code)
const {{ ArgsCls, main_func }} = new Function(code)();
const args = new ArgsCls(JSON.parse(Buffer.from('{inputs}', 'hex'),toString('utf-8')));
let result = main_func(args);
process.stdout.write('\\n[[output]]' + Buffer.from(JSON.stringify(result)).toString('hex') + '[[output]]');
process.exit(0);
'''
    return code


def parse_result(output: str):
    output_tag = '[[output]]'
    res = output[(output.rindex('\n') + 1):]

    if not res.startswith(output_tag) or not res.endswith(output_tag):
        raise Exception(f"corrupted code result \"{res}\"")
    res = res.split(output_tag)[1]
    res = json.loads(bytes.fromhex(res).decode('utf8'))
    return res