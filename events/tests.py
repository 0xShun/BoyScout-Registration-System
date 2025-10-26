"""
Compatibility shim for unittest discovery.

The real event tests live in `events/tests_pkg/`. Historically the app used a
`tests/` package which caused import-discovery conflicts in the test runner.
To be compatible with discovery (which expects `events.tests`), this module
imports the test cases from the `tests_pkg` package.
"""
try:
	# Import all tests from the package so unittest discovery finds them under
	# the `events.tests` module name.
	from .tests_pkg.test_payment_flow import *  # noqa: F401,F403
except Exception:
	# If the package isn't present or the test module is missing, keep this
	# file as a harmless placeholder so discovery doesn't error.
	pass
