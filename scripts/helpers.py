import functools
import os
import time
import asyncio

def duration(func):
    async def helper(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            print(f"this function is a coroutine: {func.__name__}")
            return await func(*args, **kwargs)
        else:
            print(f"not a coroutine: {func.__name__}")
            return func(*args, **kwargs)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_ts = time.time()
        result = await helper(func, *args, **kwargs)
        dur = time.time() - start_ts
        print('{} took {:.2} seconds'.format(func.__name__, dur))

        return result

    return wrapper


def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
        # return absolute path
        return os.path.abspath(directory)
    except OSError:
        print ('Error: Creating directory. ' +  directory)