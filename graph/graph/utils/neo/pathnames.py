from typing import Any, Optional


def find_paths_with_names(
    protocol_index_map: dict[int, dict[str, Any]],
    current_index: Optional[int],
    counter: int = 0,
    parent_index: int = -1,
    current_paths: list[Any] = [],
) -> list[list[tuple[str, int]]]:
    counter = counter
    if counter == 0:
        current_paths = []
    counter += 1
    if current_index is None or current_index not in protocol_index_map:
        return []

    node = protocol_index_map[current_index]
    path = [(node['name'], current_index)]
    current_paths.append(path[0][0])

    if counter > 20:
        return []

    if len(current_paths) != len(set(current_paths)):
        return []

    if not node['parents']:
        return [path]

    paths_with_parents = []
    for parent_index in node['parents']:
        parent_paths = find_paths_with_names(protocol_index_map, parent_index, counter, parent_index, current_paths)
        for parent_path in parent_paths:
            paths_with_parents.append(path + parent_path)
    if not paths_with_parents:
        return [path]
    return paths_with_parents
