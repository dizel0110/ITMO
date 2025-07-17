import logging
from collections.abc import Callable
from functools import wraps
from time import time
from typing import Any

from akcent_graph import settings


def timing(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrap(*args: tuple[Any], **kw: dict[str, Any]) -> Any:
        if settings.ENV == 'development':
            ts = time()
            result = func(*args, **kw)
            te = time()
            logging.debug(msg=f'func:{func.__name__} took: {te-ts} sec')
        else:
            result = func(*args, **kw)
        return result

    return wrap
