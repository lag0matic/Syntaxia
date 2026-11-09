import copy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('collection_runner',ROOT/'src/runner.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

class CollectionContractTests(unittest.TestCase):
    def test_required_mutation_and_fixture_isolation(self):
        case={'function':'add','args':[['A'],'B'],'expected':None,'args_after':[['A','B'],'B']}
        before=copy.deepcopy(case)
        source='def add(items, item):\n    items.append(item)'
        self.assertTrue(runner.execute_case(source,case)['passed'])
        self.assertTrue(runner.execute_case(source,case)['passed'])
        self.assertEqual(case,before)
        self.assertFalse(runner.execute_case('def add(items, item):\n    pass',case)['passed'])

    def test_preserve_nested_inputs(self):
        case={'function':'inspect','args':[[{'quantity':1}]],'expected':1,'unchanged_args':True}
        bad='def inspect(records):\n    records[0]["quantity"] = 2\n    return 1'
        self.assertFalse(runner.execute_case(bad,case)['passed'])
        self.assertTrue(runner.execute_case('def inspect(records):\n    return records[0]["quantity"]',case)['passed'])

    def test_fresh_output_is_not_an_alias(self):
        case={'function':'preview','args':[[]],'expected':[],'unchanged_args':True,'new_result':True}
        self.assertFalse(runner.execute_case('def preview(items):\n    return items',case)['passed'])
        self.assertTrue(runner.execute_case('def preview(items):\n    return items.copy()',case)['passed'])

    def test_equivalent_plain_loop_is_accepted(self):
        case={'function':'double','args':[[1,0,-2]],'expected':[2,0,-4],'unchanged_args':True,'new_result':True}
        code='def double(values):\n    result=[]\n    for value in values:\n        result.append(value*2)\n    return result'
        self.assertTrue(runner.execute_case(code,case)['passed'])
