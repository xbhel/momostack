import inspect
import os
import sys
import unittest
from typing import Any

import coverage

# Can't use __file__ because when running with coverage via command line,
# __file__ is not the full path
current_location = os.path.dirname(os.path.abspath(inspect.stack()[0][1]))


def test_runner_suite() -> Any:
    tests_source_root = os.path.join(current_location, 'tests')
    # commons_tests_sources = os.path.join(current_location, 'test_commons')

    # Region needed to run when using coverage.py so the imports are properly resolved.
    source_root = os.path.join(current_location, 'src')
    sys.path.append(source_root)

    cov = coverage.Coverage(source=[source_root])
    cov.start()

    tests = unittest.TestLoader().discover(tests_source_root)
    # tests.addTests(commons_tests_sources)
    result = unittest.runner.TextTestRunner().run(tests)

    cov.stop()
    cov.report()

    return result


if __name__ == '__main__':
    print(test_runner_suite())
