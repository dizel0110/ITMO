import json
import logging
import re
import traceback
from typing import Any, Optional, Union
from unicodedata import normalize

try:
    import json5
except ImportError:
    # If json5 is not available, parsing will be more limited
    json5 = None

logger = logging.getLogger(__name__)


def parse_response_robust(input_str: str) -> dict[str, Any]:
    """
    Attempt to restore json.
    """
    # Удаляем лишние пробелы и символы
    symbol = input_str.strip()

    # Находим блок сущностей
    entity_start = symbol.find('"сущности":')
    if entity_start == -1:
        return {}  # Нет ключа сущности

    # Попытаемся найти начало и конец массива "сущностей"
    opening_bracket_idx = symbol.find('[', entity_start)
    if opening_bracket_idx == -1:
        return {}

    # Извлекаем блок сущностей
    entities_block = symbol[opening_bracket_idx + 1 :]  # noqa: E203

    # Ищем все полные сущности
    entities = re.findall(r'{.*?}', entities_block, re.DOTALL)

    # Преобразуем каждую полную сущность в словарь
    entity_list = []
    for entity in entities:
        try:
            entity_dict = eval(entity.replace('null', 'None'))
            entity_list.append(entity_dict)
        except (SyntaxError, NameError):
            continue  # Пропускаем неполные или некорректные сущности

    return {'сущности': entity_list} if entity_list else {}


def merge_json_outputs(json_outputs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Merges JSON structures obtained from segmented model outputs, handling index offsets,
    parent references, and duplicate entities.

    Parameters:
    - json_outputs: List of JSON dictionaries representing segmented outputs from the model.

    Returns:
    - A combined JSON dictionary containing merged entities with updated indices
      and parent references.
    """
    all_entities = []
    entity_index_map: dict[Any, Any] = {}  # Dictionary to track unique entities by name and value
    max_index = 0  # Tracks the maximum index for correct offset adjustments

    for data in json_outputs:
        for entity in data['сущности']:
            # Check if entity is a duplicate based on unique key (name and value)
            unique_key = (entity['имя'], tuple(entity['значение']))

            if unique_key in entity_index_map:
                # If entity exists, update parent references for child elements
                existing_index = entity_index_map[unique_key]

                # Update references in new elements to the existing parent index
                for new_ind in data['сущности']:
                    if new_ind['родитель'] == entity['индекс']:
                        new_ind['родитель'] = existing_index
            else:
                # Update index and parent references with the current offset
                entity['индекс'] += max_index

                if entity['родитель'] is not None:
                    entity['родитель'] += max_index

                # Store the entity as unique
                all_entities.append(entity)
                entity_index_map[unique_key] = entity['индекс']  # Update map with unique entity index

        # Update max_index for the next segment
        max_index = max(entity['индекс'] for entity in all_entities) + 1

    # Create the combined JSON output
    merged_output = {'сущности': all_entities}
    return merged_output


def parse_json_string(input_str: str) -> Any:  # noqa: C901
    """
    Попытка распарсить потенциально "сломанный" JSON.
    Если не получается – возвращаем исходную строку.
    Ошибки записываются в логи.

    Возвращаем кортеж: (результат, статус)
    результат – распарсенный JSON или исходная строка;
    статус – словарь с информацией о ходе обработки.
    """

    status = {
        'success': False,
        'was_markdown': False,
        'was_truncated': False,
        'had_encoding_issues': False,
        'had_syntax_fixes': False,
        'original_text': input_str,
    }

    try:
        cleaned = handle_encoding(input_str)
        if cleaned != input_str:
            status['had_encoding_issues'] = True

        # Извлекаем из markdown
        md_cleaned = clean_markdown(cleaned)
        if md_cleaned != cleaned:
            status['was_markdown'] = True
        cleaned = md_cleaned

        # Удаляем комментарии, нормализуем пробелы
        cleaned = remove_comments(cleaned)
        cleaned = normalize_whitespace(cleaned)

        # Пробуем обычный json
        result = try_parse(cleaned, json_only=True)
        if result is not None:
            status['success'] = True
            return result, status

        # Пробуем json5 (если есть)
        if json5:
            result = try_parse(cleaned, json_only=False)
            if result is not None:
                status['success'] = True
                return result, status

        # Пробуем починить синтаксис
        preprocessed = preprocess_json(cleaned)
        if preprocessed != cleaned:
            status['had_syntax_fixes'] = True
            result = try_parse(preprocessed, json_only=not bool(json5))
            if result is None and json5:
                result = try_parse(preprocessed, json_only=False)
            if result is not None:
                status['success'] = True
                return result, status

        # Пробуем выдрать валидный кусок
        valid_text, partial_result = get_valid_json(preprocessed)
        if partial_result is not None:
            status['success'] = True
            status['was_truncated'] = True
            status['original_text'] = valid_text
            return partial_result, status

        # Не получилось
        logger.error('Failed to parse JSON')
        return input_str, status

    except Exception:  # noqa: B902 pylint: disable=broad-exception-caught
        logger.error('Unexpected error while parsing JSON: %s', traceback.format_exc())
        return input_str, status


def handle_encoding(text: str) -> str:
    text = text.replace('\ufeff', '')
    text = normalize('NFC', text)
    text = text.replace('\x00', '')
    return text


def clean_markdown(text: str) -> str:
    fence_pattern = r'```(?:json)?(.*?)```'
    matches = re.findall(fence_pattern, text, flags=re.DOTALL)
    if matches:
        return matches[0].strip()
    return text.strip()


def remove_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    return text


def normalize_whitespace(text: str) -> str:
    parts = re.split(r'("(?:\\.|[^"])*")', text)
    for i in range(0, len(parts), 2):
        parts[i] = ' '.join(parts[i].split())
    return ''.join(parts).strip()


def preprocess_json(text: str) -> str:
    fixed = fix_quotes(text)
    fixed = fix_commas(fixed)
    fixed = fix_escapes(fixed)
    return fixed


def fix_quotes(text: str) -> str:
    in_string = False
    escape = False
    quote_char = None
    result = []
    for char in text:
        if char == '\\' and not escape:
            escape = True
            result.append(char)
            continue
        if char in ['"', "'"] and not escape:
            if not in_string:
                in_string = True
                quote_char = char
                result.append('"')
            elif quote_char == char:
                in_string = False
                quote_char = None
                result.append('"')
            else:
                result.append(char)
        else:
            result.append(char)
        escape = False
    return ''.join(result)


def fix_commas(text: str) -> str:
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    text = re.sub(r',\s*,', ',', text)
    return text


def fix_escapes(text: str) -> str:
    # Можно расширить для более сложных случаев
    return text


def get_valid_json(text: str) -> tuple[str, Any]:  # noqa: C901
    """Extract valid JSON up to last complete object in array.
    Returns tuple of (valid_text, parsed_data)"""

    # Находим начало JSON массива
    text = text.strip()
    if not text.startswith('['):
        arr_start = text.find('[')
        if arr_start == -1:
            return text, None
        text = text[arr_start:]

    # Ищем последний полный объект
    stack: list[str] = []  # для скобок
    last_complete_pos = -1  # позиция последнего полного объекта
    in_string = False
    escape = False
    quote_char = None

    for i, char in enumerate(text):
        # Обработка экранирования
        if char == '\\' and not escape:
            escape = True
            continue

        # Обработка строк
        if char in ['"', "'"] and not escape:
            if not in_string:
                in_string = True
                quote_char = char
            elif quote_char == char:
                in_string = False
                quote_char = None

        if not in_string:
            if char == '{':
                stack.append(char)
            elif char == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
                    if not stack:  # объект завершен
                        # Ищем следующую запятую или конец массива
                        next_char_pos = i + 1
                        while next_char_pos < len(text) and text[next_char_pos] in ' \n\r\t':
                            next_char_pos += 1
                        if next_char_pos < len(text):
                            if text[next_char_pos] in [',', ']']:
                                last_complete_pos = next_char_pos

        escape = False

    if last_complete_pos == -1:
        return text, None

    # Если последний символ - запятая, отрезаем её
    valid_text = text[:last_complete_pos]
    if valid_text.endswith(','):
        valid_text = valid_text[:-1]

    # Добавляем закрывающую скобку массива, если нужно
    if not valid_text.endswith(']'):
        valid_text += ']'

    # Пробуем распарсить
    try:
        data = json.loads(valid_text)
        return valid_text, data
    except json.JSONDecodeError:
        if json5:
            try:
                data = json5.loads(valid_text)
                return valid_text, data
            except Exception:  # noqa: B902 pylint: disable=broad-exception-caught
                pass

    return text, None


def try_balance(text: str) -> Union[str, None]:  # noqa: C901
    text = text.strip()
    if not text:
        return None

    if text[0] not in ['{', '[']:
        arr_start = text.find('[')
        obj_start = text.find('{')
        starts = [x for x in [arr_start, obj_start] if x >= 0]
        if not starts:
            return None
        idx = min(starts)
        text = text[idx:]

    stack = []
    in_string = False
    escape = False
    quote_char = None
    for i, char in enumerate(text):
        if char == '\\' and not escape:
            escape = True
            continue
        if char in ['"', "'"] and not escape:
            if not in_string:
                in_string = True
                quote_char = char
            elif quote_char == char:
                in_string = False
                quote_char = None
        elif not in_string:
            if char in ['{', '[']:
                stack.append(char)
            elif char in ['}', ']']:
                if not stack:
                    break
                open_char = stack.pop()
                if (open_char == '{' and char != '}') or (open_char == '[' and char != ']'):
                    break
                if not stack:
                    candidate = text[: i + 1].strip()
                    candidate = re.sub(r',(\s*[}\]])', r'\1', candidate)
                    return candidate
        escape = False

    return None


def try_parse(text: str, json_only: bool = True) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if not json_only and json5:
            try:
                return json5.loads(text)
            except Exception:  # noqa: B902 pylint: disable=broad-exception-caught
                pass
    except Exception:  # noqa: B902 pylint: disable=broad-exception-caught
        pass
    return None


def merge_and_fix_ids(json_lists: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Merge JSON lists and ensure unique IDs by renumbering when needed.

    Args:
        json_lists (list[list[dict[str, Any]]]): List of JSON lists to merge.

    Returns:
        list[dict[str, Any]]: Merged list with unique IDs.
    """
    result: list[dict[str, Any]] = []
    used_ids: set[int] = set()
    next_id = 1

    # Merge all lists
    for json_list in json_lists:
        if isinstance(json_list, list):
            for item in json_list:
                if isinstance(item, dict):
                    # Copy item to avoid modifying original
                    new_item = dict(item)

                    # Get current ID or assign new one
                    current_id = new_item.get('id')

                    # If ID exists and already used, or no ID assigned
                    if current_id is None or current_id in used_ids:
                        # Find next available ID
                        while next_id in used_ids:
                            next_id += 1
                        new_item['id'] = next_id
                        next_id += 1

                    used_ids.add(new_item['id'])
                    result.append(new_item)

    return result


def merge_and_fix_ids2(obj1: Any, obj2: Any) -> Any:  # noqa: C901
    """Merge two JSON objects and ensure unique IDs by renumbering when needed.
    Handles empty objects and fixes references between objects.

    Args:
        obj1: First parsed JSON result (list or dict)
        obj2: Second parsed JSON result (list or dict)

    Returns:
        Merged result with unique IDs and fixed references
    """

    # Функция для проверки пустого объекта
    def is_empty(obj: Any) -> bool:
        if isinstance(obj, list):
            return len(obj) == 0
        if isinstance(obj, dict):
            return len(obj) == 0
        return obj is None

    # Если оба объекта пустые - возвращаем пустой список
    if is_empty(obj1) and is_empty(obj2):
        return []

    # Если один из объектов пустой - возвращаем непустой
    if is_empty(obj1):
        return obj2
    if is_empty(obj2):
        return obj1

    used_ids: dict[int, int] = {}
    next_id = 1

    def get_new_id(old_id: int) -> int:
        if old_id not in used_ids:
            nonlocal next_id
            while next_id in used_ids.values():
                next_id += 1
            used_ids[old_id] = next_id
            next_id += 1
        return used_ids[old_id]

    def fix_item(item: Any) -> Optional[dict[str, Any]]:
        if not isinstance(item, dict):
            return None

        new_item = dict(item)

        # Fix main ID if exists
        if 'index_bd' in new_item:
            old_id = new_item['index_bd']
            if old_id is not None:  # Only process non-null IDs
                new_item['index_bd'] = get_new_id(old_id)

        # Fix references
        if 'parent_prot' in new_item and new_item['parent_prot'] is not None:
            old_parent = new_item['parent_prot']
            new_item['parent_prot'] = used_ids.get(old_parent, old_parent)

        if 'index_prot' in new_item and new_item['index_prot'] is not None:
            old_index = new_item['index_prot']
            new_item['index_prot'] = used_ids.get(old_index, old_index)

        return new_item

    # Объединяем объекты в единый список
    all_items: list[Any] = []

    # Обрабатываем obj1
    if isinstance(obj1, list):
        all_items.extend(item for item in obj1 if item)
    elif isinstance(obj1, dict):
        all_items.append(obj1)

    # Обрабатываем obj2
    if isinstance(obj2, list):
        all_items.extend(item for item in obj2 if item)
    elif isinstance(obj2, dict):
        all_items.append(obj2)

    # Фиксим ID и ссылки для всех элементов
    result = [item for item in (fix_item(item) for item in all_items) if item is not None]

    return result


def merge_and_transform_data(  # noqa: C901
    input1_list: list[str],
    input2_list: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    def process_values(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Обрабатывает данные, добавляя поле value на основе дочерних сущностей с числами
        """
        # Создаем словарь для быстрого поиска элементов по индексу
        # index_map = {item["index"]: item for item in data}

        # Функция проверки наличия чисел в строке
        def has_numbers(text: str) -> bool:
            return bool(re.search(r'\d', text))

        # Создаем копию данных с новым полем value
        result = []
        for item in data:
            new_item = item.copy()
            new_item['value'] = None

            # Ищем дочерние элементы (те, у которых текущий индекс в parents)
            child_elements = [elem for elem in data if item['index'] in elem['parents']]

            # Проверяем наличие дочернего элемента с числом в имени
            for child in child_elements:
                if has_numbers(child['name']):
                    new_item['value'] = child['name']
                    break

            result.append(new_item)

        return result

    def extract_json(json_string: str) -> Any:
        # Удаляем маркеры markdown и лишние символы
        json_string = json_string.replace('```', '').strip()
        # Ищем JSON структуру
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, json_string)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str.replace('\\n', '\n'))
            except json.JSONDecodeError:
                return None
        return None

    # Process first input - list of strings
    data1: dict[str, Any] = {}
    for json_string in input1_list:
        parsed = extract_json(json_string)
        if parsed:
            for key, value in parsed.items():
                if key not in data1:
                    data1[key] = []
                for item in value:
                    if item not in data1[key]:
                        data1[key].append(item)

    # Convert to list of items with class information
    def convert_to_items(data: dict[str, Any]) -> list[dict[str, Any]]:
        items = []
        for class_name, objects in data.items():
            if class_name == 'class name':  # Skip invalid class names
                continue
            for obj in objects:
                items.append({**obj, 'class': class_name})
        return items

    items1 = convert_to_items(data1)

    # If second input is None or empty, skip name updating
    if not input2_list:
        old_to_new = {item['index']: i for i, item in enumerate(items1)}
        return [
            {
                'name': item['name'],
                'index': i,
                'parents': [old_to_new.get(p, p) for p in item['parents']],
                'class': item['class'],
            }
            for i, item in enumerate(items1)
        ]

    # Process second input if exists
    data2: dict[str, Any] = {}
    for json_string in input2_list:
        parsed = extract_json(json_string)
        if parsed:
            for key, value in parsed.items():
                if key not in data2:
                    data2[key] = []
                for item in value:
                    if item not in data2[key]:
                        data2[key].append(item)

    items2 = convert_to_items(data2)

    # Создаём множество имен из первого инпута для быстрой проверки
    names_in_first = {item['name'] for item in items1}

    # Фильтруем второй список
    items2 = [item for item in items2 if item['name'] in names_in_first]

    def objects_match(obj1: dict[str, Any], obj2: dict[str, Any]) -> bool:
        return obj1['name'] == obj2['name'] and obj1['parents'] == obj2['parents']

    # Create new index mapping
    old_to_new = {}
    for new_index, item in enumerate(items1):
        old_to_new[item['index']] = new_index

    # Create final result with updated indices and parents
    result = []
    for new_index, item in enumerate(items1):
        # Get updated name if exists
        matched_item = next((item2 for item2 in items2 if objects_match(item, item2)), None)
        if matched_item and 'name_from_database' in matched_item and matched_item['name_from_database']:
            item['name'] = matched_item['name_from_database']

        result.append(
            {
                'name': item['name'],
                'index': new_index,
                'parents': [old_to_new.get(p, p) for p in item['parents']],
                'class': item['class'],
            },
        )
    if result:
        result = process_values(result)
    return result


def transform_data_db(input_data: dict[str, list[str]]) -> dict[str, Any]:
    # Инициализируем выходной словарь
    result: dict[str, Any] = {}
    current_index = 1

    # Преобразуем каждый список в нужный формат
    for key, values in input_data.items():
        # Создаем список для текущего ключа
        result[key] = []

        # Обрабатываем каждое значение в списке
        for value in values:
            # Создаем новый объект с нужной структурой
            new_obj = {'name': value, 'index': current_index, 'parents': None}

            # Добавляем объект в результат
            result[key].append(new_obj)
            current_index += 1

    return result
