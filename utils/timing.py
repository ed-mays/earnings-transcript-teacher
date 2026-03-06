import time
import functools
from typing import Callable, Any


def measure_execution_time(func: Callable) -> Callable:
    """Decorator that prints the wall-clock execution time of the wrapped function."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"Function '{func.__name__}' executed in {elapsed:.6f} seconds.")
        return result
    return wrapper
