"""Exercise harness shared by browser Python and regression tests."""
import builtins
import copy
import hashlib
import contextlib
import io
import json
import traceback


class LimitedOutput(io.StringIO):
    def write(self, text):
        if self.tell() + len(text) > 20_000:
            raise RuntimeError('Output limit reached. Check whether your loop is printing too often.')
        return super().write(text)


def execute_case(source, case):
    output = LimitedOutput()
    answers = iter(case.get('stdin', []))

    def read_input(prompt=''):
        print(prompt, end='', file=output)
        try:
            return str(next(answers))
        except StopIteration:
            raise EOFError('Not enough program input. Add one line per input() call, then run again.') from None

    local_builtins = dict(vars(builtins))
    local_builtins['input'] = read_input
    namespace = {'__name__': '__main__', '__builtins__': local_builtins}
    result = {'output': '', 'passed': True, 'expected': '', 'actual': '', 'error': ''}
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(compile(source, 'mission.py', 'exec'), namespace)
            if 'function' in case:
                function = namespace.get(case['function'])
                if not callable(function):
                    raise AssertionError(f"Define a function named {case['function']}.")
                output_start = output.tell()
                arguments = copy.deepcopy(case.get('args', []))
                keywords = copy.deepcopy(case.get('kwargs', {}))
                before_arguments = copy.deepcopy(arguments)
                before_keywords = copy.deepcopy(keywords)
                actual = function(*arguments, **keywords)
                expected = case['expected']
                result.update(passed=actual == expected, expected=repr(expected), actual=repr(actual))
                if 'call_stdout' in case:
                    actual_output = output.getvalue()[output_start:].replace('\r\n', '\n').rstrip('\n')
                    expected_output = case['call_stdout'].replace('\r\n', '\n').rstrip('\n')
                    if actual_output != expected_output:
                        result.update(passed=False, expected=f'Output from function: {expected_output!r}', actual=f'Output from function: {actual_output!r}')
                if case.get('unchanged_args') and (arguments != before_arguments or keywords != before_keywords):
                    result.update(passed=False, expected='Input arguments left unchanged', actual='The function changed an input argument')
                if 'args_after' in case and arguments != case['args_after']:
                    result.update(passed=False, expected='Arguments after call: ' + repr(case['args_after']), actual='Arguments after call: ' + repr(arguments))
                if case.get('new_result') and any(actual is value for value in [*arguments, *keywords.values()]):
                    result.update(passed=False, expected='A new result object, separate from the inputs', actual='Returned an input object')
            elif 'stdout' in case:
                actual = output.getvalue().replace('\r\n', '\n').rstrip('\n')
                expected = case['stdout'].replace('\r\n', '\n').rstrip('\n')
                result.update(passed=actual == expected, expected=expected, actual=actual)
            for name, expected in case.get('variables', {}).items():
                if namespace.get(name) != expected:
                    result.update(passed=False, expected=f'{name} = {expected!r}', actual=f'{name} = {namespace.get(name)!r}')
                    break
    except BaseException:
        result.update(passed=False, error=traceback.format_exc(limit=5))
    result['output'] = output.getvalue()
    return result


def describe_case_input(case):
    lines = []
    if 'function' in case:
        arguments = [repr(value) for value in case.get('args', [])]
        if case.get('kwargs'):
            arguments.append('**' + repr(case['kwargs']))
        lines.append(f"{case['function']}({', '.join(arguments)})")
    if case.get('stdin'):
        lines.append('Program input (one quoted value per line)')
        lines.extend(repr(value) for value in case['stdin'])
    return '\n'.join(lines) or 'No program input.'


def run_request(request_json):
    request = json.loads(request_json)
    if request['mode'] == 'run':
        result = execute_case(request['code'], {'stdin': request['stdin']})
        return json.dumps({'mode': 'run', **result})
    results = []
    for case in request['tests']:
        result = execute_case(request['code'], case)
        result.update(label=case['label'], hint=case.get('hint', ''))
        if not result['passed']:
            result['sample_input'] = describe_case_input(case)
        results.append(result)
    return json.dumps({'mode': request['mode'], 'results': results, 'digest': hashlib.sha256(request['code'].encode()).hexdigest()})
