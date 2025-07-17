import re
from typing import Any


def convert_dict_to_special_string(
    my_dict: dict[Any, Any],
) -> str:
    dict_str = str(my_dict)
    result = re.sub(r"'([^']+)'\s*:", r'\1: ', dict_str)
    return result
