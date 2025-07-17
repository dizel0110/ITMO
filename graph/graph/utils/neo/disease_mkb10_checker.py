import re
from typing import Any

# Template for checking ICD-10 format
pattern = r'^[A-Z]\d{2}\.\d{1,2}$'


def is_valid_mkb_code(
    code: str,
) -> Any:
    # Checking the string for matching the pattern
    if re.match(pattern, code):
        return True
    else:
        return False
