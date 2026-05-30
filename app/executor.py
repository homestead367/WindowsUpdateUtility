from concurrent.futures import ThreadPoolExecutor

_executor = None

def get_executor(max_workers=10):
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor
