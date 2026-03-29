"""Shutdown coordination — shared event set on SIGTERM."""

import threading

shutdown_event = threading.Event()
