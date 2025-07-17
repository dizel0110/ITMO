from typing import Any


def parents_index_checker(
    data_protocol: Any,
) -> Any:
    data_protocol_new = []
    for record in data_protocol:
        record_new = record.copy()
        possible_parents = record.get('parents')
        possible_values = record.get('value')
        if isinstance(possible_values, str):
            possible_values = [possible_values]
        current_index = record.get('index')
        if not possible_values:
            parents = [num for num in possible_parents if num != current_index]
            record_new['parents'] = parents
        elif len(possible_parents) != len(possible_values):
            if len(possible_parents) <= 1:
                record_new['parents'] = possible_parents
                record_new['value'] = possible_values
            else:
                parents, value = [], None
                record_new['parents'] = parents
                record_new['value'] = value
        elif len(possible_parents) == len(possible_values):
            list_equal = []
            for position, current_parent in enumerate(possible_parents):
                if current_index == current_parent:
                    list_equal.append(position)
            if list_equal:
                parents = [num for count, num in enumerate(possible_parents) if count not in list_equal]
                values = [num for count, num in enumerate(possible_values) if count not in list_equal]
                record_new['parents'] = parents
                record_new['value'] = values
            else:
                record_new['parents'] = possible_parents
                record_new['value'] = possible_values
        data_protocol_new.append(record_new)
    return data_protocol_new
