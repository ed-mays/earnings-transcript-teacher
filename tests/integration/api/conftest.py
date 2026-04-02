"""Shared setup for API integration tests.

Auth fixtures (RSA keys, jwt helpers, client) are defined per-file following
the same pattern as tests/unit/api/.  Modal is installed in this environment
so no sys.modules stub is needed here.
"""
