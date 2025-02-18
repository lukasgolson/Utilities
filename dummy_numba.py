import logging

# Configure the logger for this module.
logger = logging.getLogger(__name__)

# On certain systems, numba is not available / fails to load llvm libraries.
# This script provides a dummy class that can be used in place of numba to avoid import errors.
def is_numba_available() -> (bool, Exception):
    try:
        import numba
        return True, None
    except Exception as e:
        return False, e


def jit(*jit_args, **jit_kwargs):
    def decorator(func):
        return func
    return decorator

def njit(*jit_args, **jit_kwargs):
    def decorator(func):
        return func
    return decorator


def prange(*args, **kwargs):
    # Use the built-in range for sequential iteration.
    return range(*args, **kwargs)



# Check numba availability and log a warning if it is not available.
_available, _exception = is_numba_available()
if not _available:
    logger.warning("Numba is not available. Using dummy implementations. Exception: %s", _exception)
