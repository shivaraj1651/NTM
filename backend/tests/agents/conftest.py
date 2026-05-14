"""
Register conftest_evals as a pytest plugin so its marker, autouse fixtures,
and session reporter are active for all eval tests in this package.
"""

pytest_plugins = ["backend.tests.agents.conftest_evals"]
