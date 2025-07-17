from datetime import datetime
from typing import Any


def check_range_in_string(
    input_str: str,
) -> Any:
    # Split the string into parts, removing all characters except numbers
    numbers = ''.join([char for char in input_str if char.isdigit()])
    if not numbers:
        return 0
    number = int(numbers)
    if 1900 <= number <= 2100:
        return number
    else:
        return 0


def normalize_and_check_date(  # noqa: C901, pylint: disable=too-complex
    date_str: str,
) -> Any:
    check_year = check_range_in_string(date_str)
    if check_year != 0:
        return check_year
    # Replace all punctuation and spaces with a hyphen
    date_str = date_str.replace(',', '-').replace('.', '-').replace(' ', '-')
    date_str = date_str.replace(':', '-').replace('"', '-').replace(';', '-')
    date_str = date_str.replace('\n', '-').replace('\t', '-')
    date_str = date_str.replace('(', '-').replace(')', '-')
    # Removing double hyphens and spaces at the beginning and end of a line
    while date_str.startswith('-'):
        date_str = date_str[1:]
    while date_str.endswith('-'):
        date_str = date_str[:-1]
    while date_str.find('--') >= 0:
        date_str = date_str.replace('--', '-')
    # Date check
    try:
        first_date = datetime.strptime(date_str, '%d-%m-%Y')
        if (first_date) and (first_date > datetime(1900, 1, 1)):
            if first_date < datetime(2100, 1, 1):
                return first_date.strftime('%d-%m-%Y')
            else:
                return False
        else:
            return False
    except ValueError:
        try:
            second_date = datetime.strptime(date_str, '%m-%d-%Y')
            if (second_date) and (second_date > datetime(1900, 1, 1)):
                if second_date < datetime(2100, 1, 1):
                    return second_date.strftime('%d-%m-%Y')
                else:
                    return False
            else:
                return False
        except ValueError:
            try:
                third_date = datetime.strptime(date_str, '%Y-%m-%d')
                if (third_date) and (third_date > datetime(1900, 1, 1)):
                    if third_date < datetime(2100, 1, 1):
                        return third_date.strftime('%d-%m-%Y')
                    else:
                        return False
                else:
                    return False
            except ValueError:
                return False
