"""Author the functions chapter; does not register it or touch learner data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
missions = []


def section(heading, text, code=None):
    return {'heading': heading, 'text': text, **({'code': code} if code else {})}


def script(label, output, inputs=(), public=True, hint='Trace the calls and the resulting output in order.'):
    return {'label': label, 'public': public, 'stdin': list(inputs), 'stdout': output, 'hint': hint}


def call(name, args, expected, public=True, *, output='', kwargs=None):
    return {'label': f'{name}({", ".join([repr(a) for a in args] + [f"{k}={v!r}" for k,v in (kwargs or {}).items()])})',
            'public': public, 'function': name, 'args': args, 'kwargs': kwargs or {}, 'expected': expected, 'call_stdout': output,
            'hint': 'Check the function name, supplied arguments, returned value, and whether it should print anything.'}


def mission(slug, title, concepts, lesson, requirements, starter, example, hints, tests, solution, notes, inputs='', boss=False):
    number = len(missions) + 1
    missions.append({'id': f'py-fn-{number:02}-{slug}', 'version': 1, 'title': title, 'concepts': concepts,
        'xp': 30 if boss else 10, 'prerequisites': [missions[-1]['id'] if missions else 'py-07-session-tool'],
        'lesson': lesson, 'brief': requirements[0], 'requirements': requirements, 'starter': starter, 'example': example,
        'input': inputs, 'hints': hints, 'tests': tests, 'reference': {'code': solution, 'notes': notes}, 'boss': boss})


mission('call', 'A definition is not a call', 'Reading code · def · execution order', [
    section('Predict before running', 'A def statement creates a function. Its indented body is saved for later; it does not run just because Python reaches the definition. A call uses parentheses to ask the function to run.', 'def sound_check():\n    print("Testing audio")\n\nprint("Before")\nsound_check()\nprint("After")'),
    section('Follow the detour', 'At sound_check(), execution enters the function, prints its message, then returns to the next line after the call. Predict the starter output before running it. Add only the missing call; this first mission is about reading the route through the code.')],
    ['Call announce_ready between the two existing outer print statements.', 'Keep the function and the existing printed messages unchanged. The three lines should appear in the order shown.'],
    'def announce_ready():\n    print("Workshop ready")\n\nprint("Starting")\n# Call the function here.\nprint("Finished")\n',
    'Starting\nWorkshop ready\nFinished',
    ['Which indented line never gets visited when you run the starter?', 'Put the call where you want the function output to appear, at the same indentation as the outer prints.', 'Use the function name followed by empty parentheses. You are calling it, not defining it again.'],
    [script('The call happens between Starting and Finished', 'Starting\nWorkshop ready\nFinished\n'), call('announce_ready', [], None, False, output='Workshop ready')],
    'def announce_ready():\n    print("Workshop ready")\n\nprint("Starting")\nannounce_ready()\nprint("Finished")\n',
    ['The definition stores the behavior; the later call runs it. Moving the call changes when its output appears.', 'Writing announce_ready without parentheses would refer to the function but would not execute its body.'])

mission('define', 'Package a repeated action', 'Define a function · call it twice', [
    section('Give an action a name', 'A function can group an action you want to repeat. Start with def, a descriptive name, parentheses, and a colon. Its body is indented four spaces.', 'def print_separator():\n    print("----------")\n\nprint_separator()\nprint_separator()'),
    section('One definition, several calls', 'Define the behavior once, then call it wherever needed. Repeating a function call is fine. Repeating its whole body makes later changes harder to keep consistent.')],
    ['Define show_prompt with no parameters. Its body prints Choose a tool.', 'Call show_prompt twice after its definition. The final output is two identical lines.'],
    '# Define show_prompt here.\n\n# Call it twice below.\n', 'Choose a tool.\nChoose a tool.',
    ['There should be one def statement and two separate calls.', 'The printed text belongs inside the function; the two calls belong outside it.', 'A no-parameter function still needs () in both its definition and its calls.'],
    [script('The action runs twice', 'Choose a tool.\nChoose a tool.\n'), call('show_prompt', [], None, False, output='Choose a tool.')],
    'def show_prompt():\n    print("Choose a tool.")\n\nshow_prompt()\nshow_prompt()\n',
    ['The named function describes the repeated action. If the message changes, there is one body to edit.', 'There is no return value needed for this display-only action. Later missions separate calculations from display.'])

mission('parameter', 'One function, different values', 'One parameter · supplied arguments', [
    section('A parameter is a local name', 'A parameter appears inside the definition parentheses. Each call supplies an argument: the actual value the parameter will refer to during that call.', 'def announce_station(station):\n    print(f"Station: {station}")\n\nannounce_station("North")\nannounce_station("West")'),
    section('Read the contract', 'For this exercise the checks call your function themselves with different names. You do not need input(). Keep the sample calls for Run; those calls alone are not proof the function works for other values.')],
    ['Define greet(learner) to print Hello, NAME! using its parameter.', 'Keep the two sample calls. The function must also work with other names; do not hard-code them.'],
    'def greet(learner):\n    pass\n\ngreet("David")\ngreet("Morgan")\n', 'greet("David") prints Hello, David!\ngreet("Morgan") prints Hello, Morgan!',
    ['The parameter learner already contains the supplied name when the body runs.', 'You need a print inside the function, using an f-string.', 'Place the parameter name in braces, rather than quoting it as literal text.'],
    [call('greet', ['David'], None, output='Hello, David!'), call('greet', ['Morgan'], None, output='Hello, Morgan!'), call('greet', ['Sam Lee'], None, False, output='Hello, Sam Lee!')],
    'def greet(learner):\n    print(f"Hello, {learner}!")\n\ngreet("David")\ngreet("Morgan")\n',
    ['The same body handles every name. The argument changes from call to call; the parameter name does not.'])

mission('names', 'The caller can use another name', 'Arguments by value · caller names', [
    section('Names do not need to match', 'An argument can be a variable with a completely different name. Python evaluates that argument and binds the resulting value to the parameter.', 'def show_project(title):\n    print(f"Project: {title}")\n\ncurrent_project = "Radio logger"\nshow_project(current_project)'),
    section('Find the boundary', 'Read your calls from outside inward: what value does this outside variable hold, and which parameter receives it? The function should use its parameter rather than reaching back to an outside variable.')],
    ['Repair label_device(device_name) so it prints Device: NAME using its parameter.', 'Keep the sample outside variable named selected_device and its call. The function must work with any supplied name.'],
    'def label_device(device_name):\n    print(f"Device: {selected_device}")\n\nselected_device = "Headset"\nlabel_device(selected_device)\n',
    'label_device("Headset") prints Device: Headset\nlabel_device("Radio") prints Device: Radio',
    ['The starter looks correct for its one sample, but it ignores the supplied argument.', 'Which name belongs to the definition parentheses?', 'Inside the body, use the parameter rather than selected_device. Keep the outside call unchanged.'],
    [call('label_device', ['Headset'], None, output='Device: Headset'), call('label_device', ['Radio'], None, output='Device: Radio'), call('label_device', ['Printer'], None, False, output='Device: Printer')],
    'def label_device(device_name):\n    print(f"Device: {device_name}")\n\nselected_device = "Headset"\nlabel_device(selected_device)\n',
    ['Using device_name makes the behavior depend on the actual argument. Matching the parameter name to an outside variable is unnecessary.', 'The initial code accidentally worked for Headset. Testing another argument exposes the hidden dependency.'])

mission('order', 'Two arguments, two jobs', 'Positional arguments · parameter order', [
    section('Position establishes the match', 'With ordinary positional arguments, the first value goes to the first parameter, the second to the second. Meaningful parameter names help you remember the order.', 'def show_route(origin, destination):\n    print(f"{origin} -> {destination}")\n\nshow_route("Home", "Workshop")'),
    section('Trace before fixing', 'In the starter, the function is correct but the sample call swaps two values. Work out which value each parameter currently receives, then fix only the call.')],
    ['Keep show_item(item, location) unchanged and repair the argument order in the sample call.', 'The supplied item is Radio and its location is Desk. Print Radio @ Desk.'],
    'def show_item(item, location):\n    print(f"{item} @ {location}")\n\nitem_name = "Radio"\nroom_name = "Desk"\nshow_item(room_name, item_name)\n', 'Radio @ Desk',
    ['The parameter item should receive the value stored in item_name.', 'The two outside variables are fine; inspect their order inside the call.', 'Read the definition left to right, then match the call in that same order.'],
    [script('The radio belongs at the desk', 'Radio @ Desk\n'), call('show_item', ['Printer', 'Bench'], None, False, output='Printer @ Bench')],
    'def show_item(item, location):\n    print(f"{item} @ {location}")\n\nitem_name = "Radio"\nroom_name = "Desk"\nshow_item(item_name, room_name)\n',
    ['The parameter order is part of the function contract. Swapping valid strings produces no exception, but changes the meaning.'])

mission('two', 'Build a two-parameter action', 'Independent practice · two parameters', [
    section('A small variation', 'Use the same parameter-and-argument pattern in a new context. The checks will supply both values. Nothing inside the function needs to ask for input.', 'def show_score(player, points):\n    print(f"{player}: {points} points")'),
    section('Keep the output contract visible', 'The body should use both parameters. Pay attention to spaces and punctuation when a program is expected to produce a specific line.')],
    ['Define announce_job(job_name, copies) to print JOB: COUNT copies.', 'Use the word copies even when the number is one. This lesson is about arguments, not pluralization.'],
    '# Define announce_job here.\n\n# Add a sample call if you want to see output with Run.\n', 'announce_job("Bracket", 3) prints Bracket: 3 copies',
    ['There are two parameters: one text value and one number.', 'An f-string can insert both values directly; you do not need to convert the number to text first.', 'Use job_name and copies inside the function body, not a fixed sample title or count.'],
    [call('announce_job', ['Bracket', 3], None, output='Bracket: 3 copies'), call('announce_job', ['Knob', 1], None, output='Knob: 1 copies'), call('announce_job', ['Cable clip', 8], None, False, output='Cable clip: 8 copies')],
    'def announce_job(job_name, copies):\n    print(f"{job_name}: {copies} copies")\n\nannounce_job("Bracket", 3)\n',
    ['The function has one display responsibility and receives all the data it needs. A sample call helps manual testing, but the independent checks exercise other values.'])

mission('return', 'Give a value back', 'return · calculation versus display', [
    section('A returned value belongs to the caller', 'print sends text to the output panel. return hands a value back to the calling expression. The caller can then print it, store it, or calculate with it.', 'def double(value):\n    return value * 2\n\nanswer = double(6)\nprint(answer)'),
    section('Checks can inspect the result', 'From here, many checks call a function and compare its return value. Printing the right number inside the function is not enough. Do not print inside the calculation function; the sample caller will handle display.')],
    ['Define minutes_for_sessions(length, count) to return the numeric product of its arguments.', 'Do not print or read input inside the function. Keep the sample outer print for Run.'],
    'def minutes_for_sessions(length, count):\n    pass\n\nprint(minutes_for_sessions(25, 3))\n', 'minutes_for_sessions(25, 3) returns 75\nminutes_for_sessions(10, 0) returns 0',
    ['The arithmetic is familiar; the new part is how its result leaves the function.', 'Replace pass with a return statement, not a print.', 'The returned expression should multiply the two parameter values.'],
    [call('minutes_for_sessions', [25, 3], 75), call('minutes_for_sessions', [10, 0], 0), call('minutes_for_sessions', [12, 4], 48, False)],
    'def minutes_for_sessions(length, count):\n    return length * count\n\nprint(minutes_for_sessions(25, 3))\n',
    ['This function returns a number and produces no output of its own. Its caller chooses what to do with the number.'])

mission('none', 'It printed correctly. What came back?', 'Debugging · implicit None', [
    section('Two different channels', 'A function can display a number and still return no useful value. If it reaches its end without return, the returned value is None, representing the absence of a value.', 'def broken_double(value):\n    print(value * 2)\n\nanswer = broken_double(4)\nprint(answer)\n# Output: 8, then None'),
    section('Repair the boundary', 'Run the starter and inspect both lines. The internal calculation is right; the caller is receiving the wrong thing. Change how the function delivers its result.')],
    ['Repair add_setup_time(work_minutes, setup_minutes) to return their sum.', 'The function must not print. The existing outer print should show 40, with no extra line.'],
    'def add_setup_time(work_minutes, setup_minutes):\n    print(work_minutes + setup_minutes)\n\nresult = add_setup_time(35, 5)\nprint(result)\n', '40',
    ['What value is being assigned to result right now?', 'The function is sending its calculation to the screen instead of the caller.', 'Replace the output operation inside the function with the operation that hands back a value.'],
    [call('add_setup_time', [35, 5], 40), call('add_setup_time', [0, 5], 5), call('add_setup_time', [12, 8], 20, False), script('Only the caller displays the answer', '40\n', public=False)],
    'def add_setup_time(work_minutes, setup_minutes):\n    return work_minutes + setup_minutes\n\nresult = add_setup_time(35, 5)\nprint(result)\n',
    ['Changing print to return repairs the interface without changing the arithmetic. Returning a value lets other code use the result.'])

mission('store', 'Use the result again', 'Store a returned value · reuse', [
    section('A call is an expression', 'A function call can appear on the right side of an assignment. The returned value, not the function, becomes the value of that variable.', 'def square(number):\n    return number * number\n\narea = square(4)\nprint(area)\nprint(area + 2)'),
    section('Keep responsibilities separate', 'The helper below is already complete. Use its result in two output lines. Read a whole-number item price and quantity with input() without prompt text. Invalid numeric text is outside this exercise.')],
    ['Read unit price and quantity as two whole-number inputs, in that order.', 'Call batch_cost and store its result in subtotal.', 'Print Subtotal: VALUE and then With packing: VALUE, adding 5 only for the second line.'],
    'def batch_cost(unit_price, quantity):\n    return unit_price * quantity\n\n# Read the two inputs.\n# Store the returned subtotal, then use it in both messages.\n', 'Input: 4, then 3\nOutput:\nSubtotal: 12\nWith packing: 17',
    ['Use int(input()) twice, then pass those values to the helper.', 'Your assignment needs a call with arguments on the right-hand side.', 'Use subtotal unchanged in the first message and subtotal + 5 in the second.'],
    [script('Three items at four each', 'Subtotal: 12\nWith packing: 17\n', ['4','3']), script('A different order', 'Subtotal: 14\nWith packing: 19\n', ['7','2'], False), script('Zero items', 'Subtotal: 0\nWith packing: 5\n', ['3','0'], False)],
    'def batch_cost(unit_price, quantity):\n    return unit_price * quantity\n\nunit_price = int(input())\nquantity = int(input())\nsubtotal = batch_cost(unit_price, quantity)\nprint(f"Subtotal: {subtotal}")\nprint(f"With packing: {subtotal + 5}")\n',
    ['subtotal names a value reused in two places. Keeping the extra packing calculation outside batch_cost lets that function stay focused.'], inputs='4\n3')

mission('inline', 'Call it inside the message', 'Calls inside expressions · f-strings', [
    section('Braces can contain expressions', 'An f-string can evaluate a function call directly. That is useful when the result is simple and only needed once.', 'def square(number):\n    return number * number\n\nprint(f"Area: {square(5)}")'),
    section('Same call, different location', 'Putting a call in an f-string does not change parameter matching or return behavior. The call must still include its arguments. This is the pattern you used in the demo project.')],
    ['Read a whole-number session length followed by a whole-number count.', 'Use total_minutes inside the f-string to print Planned: TOTAL minutes.', 'Keep the provided calculation function unchanged.'],
    'def total_minutes(length, count):\n    return length * count\n\nlength = int(input())\ncount = int(input())\n# Print the message with a function call inside the braces.\n', 'Input: 20, then 3\nOutput: Planned: 60 minutes',
    ['The expression between the braces should produce the numeric total.', 'Call total_minutes with length and count, in that order.', 'The function call needs its own parentheses inside the f-string braces.'],
    [script('Three sessions', 'Planned: 60 minutes\n', ['20','3']), script('A different plan', 'Planned: 28 minutes\n', ['7','4'], False)],
    'def total_minutes(length, count):\n    return length * count\n\nlength = int(input())\ncount = int(input())\nprint(f"Planned: {total_minutes(length, count)} minutes")\n',
    ['The expression is short enough to read comfortably inside the message. This is an option, not a universal improvement over a named result.'], inputs='20\n3')

mission('clarity', 'Give an intermediate result a name', 'Readable expressions · refactoring', [
    section('A name can explain an expression', 'A long expression can be correct yet difficult to follow. A meaningful intermediate variable gives its result a name and makes reuse straightforward.', 'area = width * height\nprint(f"Area: {area}")'),
    section('Preserve behavior while changing structure', 'Refactoring changes the organization without changing the intended behavior. The starter contains working helpers but repeats a nested expression. Replace that repetition with two named steps. Add the missing final line using the second value.')],
    ['Read unit price and quantity as whole numbers. Keep both helper functions unchanged.', 'Set base_cost to the result of batch_cost. Set packed_cost to add_packing(base_cost).', 'Print Base: VALUE, Packed: VALUE, and Packed again: VALUE in that order. Reuse packed_cost for both packed messages.'],
    'def batch_cost(price, quantity):\n    return price * quantity\n\ndef add_packing(cost):\n    return cost + 5\n\nprice = int(input())\nquantity = int(input())\nprint(f"Packed: {add_packing(batch_cost(price, quantity))}")\nprint(f"Packed again: {add_packing(batch_cost(price, quantity))}")\n',
    'Input: 4, then 3\nOutput:\nBase: 12\nPacked: 17\nPacked again: 17',
    ['Calculate the base first, then pass that value to add_packing.', 'Use the variable names requested in the contract so each stage is visible.', 'Once packed_cost exists, both packed messages can use the same variable.'],
    [dict(script('Named stages retain the correct amounts', 'Base: 12\nPacked: 17\nPacked again: 17\n', ['4','3']), variables={'base_cost':12,'packed_cost':17}), script('Another order', 'Base: 20\nPacked: 25\nPacked again: 25\n', ['10','2'], False)],
    'def batch_cost(price, quantity):\n    return price * quantity\n\ndef add_packing(cost):\n    return cost + 5\n\nprice = int(input())\nquantity = int(input())\nbase_cost = batch_cost(price, quantity)\npacked_cost = add_packing(base_cost)\nprint(f"Base: {base_cost}")\nprint(f"Packed: {packed_cost}")\nprint(f"Packed again: {packed_cost}")\n',
    ['base_cost and packed_cost explain two distinct stages. The repeated packed value no longer requires another nested call.', 'The gain here is readability and avoiding unnecessary repeated work. The shorter inline form from the previous mission remains appropriate for simple one-use expressions.'], inputs='4\n3')

mission('missing-call', 'A function is not its answer', 'Debugging · function versus call', [
    section('Two valid assignments, different meanings', 'A function is itself a value. Assigning its name to another variable is legal, but it does not run the function. Assigning a call stores what the function returns.', 'def double(value):\n    return value * 2\n\noperation = double\nanswer = double(6)'),
    section('Why the starter fails', 'The starter tries to add 5 to a function object. That is not the number it intended to calculate. Repair the assignment rather than changing the arithmetic or the helper.')],
    ['Keep session_total unchanged. Read session length and count as whole numbers.', 'Repair the assignment to total so it stores the result of calling session_total with those inputs.', 'Print the total plus a five-minute break as With break: VALUE.'],
    'def session_total(length, count):\n    return length * count\n\nlength = int(input())\ncount = int(input())\ntotal = session_total\nprint(f"With break: {total + 5}")\n', 'Input: 15, then 2\nOutput: With break: 35',
    ['What kind of value is total holding right now?', 'The function needs to be called before its numeric result can be used.', 'Add call parentheses containing the two input variables to the assignment.'],
    [script('The result is numeric', 'With break: 35\n', ['15','2']), script('Different inputs reach the helper', 'With break: 65\n', ['20','3'], False)],
    'def session_total(length, count):\n    return length * count\n\nlength = int(input())\ncount = int(input())\ntotal = session_total(length, count)\nprint(f"With break: {total + 5}")\n',
    ['session_total is the function; session_total(length, count) is a call whose value is the returned number. Both forms are useful in Python, but this calculation needs the second.'], inputs='15\n2')

mission('compose', 'Connect two small functions', 'Composition · returned input to another call', [
    section('One result can become another argument', 'Functions compose when one function supplies a value that another can use. Read nested calls from the inside out, or name the intermediate result.', 'def double(value):\n    return value * 2\n\ndef add_one(value):\n    return value + 1\n\nresult = add_one(double(4))'),
    section('Keep the flow explicit', 'The supplied helpers calculate work time and then add a break. The new function should connect them and return the final value. It should not print or ask for input.')],
    ['Implement planned_minutes(length, count) using work_minutes and with_break.', 'Pass the work total into with_break and return its result. The helpers add one five-minute break to the whole plan, even for a zero work total.'],
    'def work_minutes(length, count):\n    return length * count\n\ndef with_break(minutes):\n    return minutes + 5\n\ndef planned_minutes(length, count):\n    pass\n\nprint(planned_minutes(20, 3))\n', 'planned_minutes(20, 3) returns 65\nplanned_minutes(10, 0) returns 5',
    ['First find which helper accepts length and count.', 'Its returned number is the argument for the second helper.', 'Do not lose the second result: the outer function also needs to return it.'],
    [call('planned_minutes', [20,3],65), call('planned_minutes',[10,0],5), call('planned_minutes',[7,2],19,False)],
    'def work_minutes(length, count):\n    return length * count\n\ndef with_break(minutes):\n    return minutes + 5\n\ndef planned_minutes(length, count):\n    work = work_minutes(length, count)\n    return with_break(work)\n\nprint(planned_minutes(20, 3))\n',
    ['The intermediate name work makes the data flow easy to inspect. A nested call would also be correct and reasonably readable here.', 'Each helper performs one operation; the outer function coordinates them.'])

mission('keywords', 'Make the arguments explicit', 'Keyword arguments · named calls', [
    section('Name the destination parameter', 'Keyword arguments use parameter=value in a call. Their order can differ from the definition because the names make the mapping explicit.', 'def describe_box(width, height):\n    return f"{width} by {height}"\n\nprint(describe_box(height=3, width=8))'),
    section('Names belong to the definition', 'The keyword on the left must match a parameter name. The value on the right may come from any expression or outside variable. Positional arguments must come before keyword arguments if you mix the two styles.')],
    ['Keep make_label(device, location) unchanged. Read device and location text from two input lines.', 'Repair the reversed label by calling make_label with keyword arguments. Map device to selected_device and location to selected_location.', 'Print the returned label. Use no input prompts.'],
    'def make_label(device, location):\n    return f"{device} @ {location}"\n\nselected_device = input()\nselected_location = input()\nlabel = make_label(selected_location, selected_device)\nprint(label)\n', 'Input: Radio, then Desk\nOutput: Radio @ Desk',
    ['The values are fine; their mapping to the parameters is wrong.', 'Use the function parameter names as the keywords, not the outside variable names.', 'You can write the location keyword first and device second, provided each maps to the correct outside value.'],
    [script('The named arguments reach the right places', 'Radio @ Desk\n', ['Radio','Desk']), script('A different label', 'Printer @ Bench\n', ['Printer','Bench'], False), dict(call('make_label', [], 'Headset @ Shelf', False, kwargs={'location':'Shelf','device':'Headset'}), stdin=['Radio','Desk'])],
    'def make_label(device, location):\n    return f"{device} @ {location}"\n\nselected_device = input()\nselected_location = input()\nlabel = make_label(location=selected_location, device=selected_device)\nprint(label)\n',
    ['The keyword names are taken from the definition. Writing them makes the intended mapping visible, even when both values are strings.', 'The checks verify behavior and keyword support; the comparison is your chance to check that you practiced the requested call style.'], inputs='Radio\nDesk')

mission('defaults', 'A useful default, not a hidden assumption', 'Default arguments · omitted values', [
    section('Let a caller omit one value', 'A default in the definition is used when the caller leaves out that argument. Required parameters come before parameters with defaults.', 'def add_margin(value, margin=2):\n    return value + margin\n\nprint(add_margin(8))\nprint(add_margin(8, margin=5))'),
    section('Omitted is different from zero', 'If a caller explicitly supplies zero, Python uses zero rather than the default. A default is not a substitute for every false-looking value. We are using a simple numeric default; mutable defaults are a later topic.')],
    ['Define with_setup(work_minutes, setup_minutes=5) to return their sum.', 'Support omitted setup, a positional setup value, and a keyword setup value. Explicit zero means no setup time.', 'Do not print or read input inside the function.'],
    'def with_setup(work_minutes, setup_minutes=5):\n    pass\n\nprint(with_setup(30))\nprint(with_setup(30, setup_minutes=0))\n', 'with_setup(30) returns 35\nwith_setup(30, 8) returns 38\nwith_setup(30, setup_minutes=0) returns 30',
    ['The default is already present in the starter definition.', 'The body can use setup_minutes directly, whether its value came from the default or the caller.', 'You only need to return the sum of the two parameters; no conditional fallback is needed.'],
    [call('with_setup',[30],35), call('with_setup',[30],30,kwargs={'setup_minutes':0}), call('with_setup',[30,8],38,False), call('with_setup',[0],5,False)],
    'def with_setup(work_minutes, setup_minutes=5):\n    return work_minutes + setup_minutes\n\nprint(with_setup(30))\nprint(with_setup(30, setup_minutes=0))\n',
    ['The signature tells callers what will happen when setup time is omitted. Explicit arguments still take priority, including zero.'])

mission('toolkit', 'Build a session calculation toolkit', 'Chapter project · functions working together', [
    section('Small contracts, one application', 'Build three reusable functions, then a short console caller that combines them. You have already practiced every operation: multiplication, adding a default amount, cleaning text, and returning a formatted string.'),
    section('Keep input at the edge', 'The functions receive values and return values. Only the outer program reads input and prints. That separation means the same helpers could later be used by a GUI or another program.'),
    section('Build and test one layer at a time', 'Start with the work-total function, then the setup function, then the formatter. Finally connect them to input. Checks call each helper independently and also run the whole program. Numeric inputs are nonnegative integers; handling invalid text and negative values is deliberately outside this project.')],
    ['Define work_minutes(length, count) to return their product.', 'Define with_setup(minutes, setup=5) to return minutes plus setup. Callers may override setup, including zero.', 'Define format_plan(name, minutes) to strip surrounding whitespace from name and return NAME: TOTAL minutes. without printing. If the cleaned name is empty, use Learner (as in the demo).', 'At the top level, read name, session length, and session count, in that order. Convert the two numeric inputs to integers.', 'Use the helpers to calculate total work, add one default five-minute setup to the whole plan, format the message, and print it exactly once. Even zero sessions still includes setup.', 'The three helper functions must not call input() or print(). Keep the numeric and string results reusable.'],
    '# 1. Define work_minutes.\n\n# 2. Define with_setup with its default.\n\n# 3. Define format_plan.\n\n# 4. Read the inputs, connect the helpers, and print the result.\n',
    'Input:\n  David  \n25\n3\n\nOutput:\nDavid: 80 minutes.',
    ['Build the numerical helpers before the input section. Work time and setup time are two separate calculations.', 'The formatter returns a string; the outer caller prints it. Clean the name before checking for an empty string.', 'Trace the flow: input values -> work_minutes -> with_setup -> format_plan -> print. Every arrow needs a returned value, not a function name without parentheses.'],
    [script('Complete three-session plan','David: 80 minutes.\n',['  David  ','25','3']), script('Blank name and zero sessions','Learner: 5 minutes.\n',['   ','20','0']), script('Another plan','Morgan: 26 minutes.\n',['Morgan','7','3'],False),
     dict(call('work_minutes',[12,4],48,False),stdin=['Test','1','1']), dict(call('with_setup',[30],35,False),stdin=['Test','1','1']), dict(call('with_setup',[30],30,False,kwargs={'setup':0}),stdin=['Test','1','1']), dict(call('format_plan',['  Sam  ',42],'Sam: 42 minutes.',False),stdin=['Test','1','1']), dict(call('format_plan',[' ',0],'Learner: 0 minutes.',False),stdin=['Test','1','1'])],
    'def work_minutes(length, count):\n    return length * count\n\ndef with_setup(minutes, setup=5):\n    return minutes + setup\n\ndef format_plan(name, minutes):\n    clean_name = name.strip()\n    if clean_name == "":\n        clean_name = "Learner"\n    return f"{clean_name}: {minutes} minutes."\n\nname = input()\nlength = int(input())\ncount = int(input())\nwork = work_minutes(length, count)\nplanned = with_setup(work)\nmessage = format_plan(name, planned)\nprint(message)\n',
    ['Each helper has a small contract that can be checked independently. Input conversion and display stay in the outer program.', 'Named intermediate results make the path easy to explain and debug. A shorter nested expression would also work, but is not automatically better.', 'This is a reusable first version, not a production scheduler. Validation, files, and interfaces can be added later without mixing those responsibilities into the calculations.'], inputs='  David  \n25\n3', boss=True)

chapter = {'id':'python-functions', 'title':'Functions and returned values', 'language':'python', 'version':1, 'badge':'Function Builder', 'missions':missions}
(ROOT / 'content/python-functions.json').write_text(json.dumps(chapter, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
solutions_path = ROOT / 'tests/solutions.json'
solutions = json.loads(solutions_path.read_text())
solutions.update({m['id']:m['reference']['code'] for m in missions})
solutions_path.write_text(json.dumps(solutions, indent=2, ensure_ascii=False)+'\n',encoding='utf-8')
print(f'Authored {len(missions)} functions missions. Registration is separate.')
