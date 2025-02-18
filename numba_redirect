import logging

logger = logging.getLogger(__name__)

def is_numba_available() -> (bool, str):
    """
    Check if numba is available and working.

    Returns:
        tuple: A boolean indicating numba availability and an Exception (if any).
    """
    try:
        import numba
        return True, None
    except Exception as e:

        # get exception type

        e_type = type(e).__name__

        return False, e_type

def _dummy_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

def _dummy_prange(*args, **kwargs):
    # Use the built-in range for sequential iteration.
    return range(*args, **kwargs)

# Check for numba availability.
_available, _exception = is_numba_available()

if _available:
    import numba
    # Redirect to numba's implementations.
    jit = numba.jit
    njit = numba.njit
    prange = numba.prange
    from numba.typed import List as NumbaList
    List = NumbaList
else:
    logger.warning("Numba is not available. Falling back to pure python. Exception: %s", _exception)
    jit = _dummy_decorator
    njit = _dummy_decorator
    prange = _dummy_prange
    List = list
