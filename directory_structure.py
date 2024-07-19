import os
import json
import fnmatch
import logging
from pathlib import Path
from typing import Union, Dict, List
import argparse


def load_exclusions(file_path: str) -> List[str]:
    """
    Загружает маски исключений из файла.

    :param file_path: Путь к файлу с масками исключений.
    :return: Список масок исключений.
    """
    if not Path(file_path).exists():
        return []
    with open(file_path, 'r') as f:
        exclusions = f.read().splitlines()
    return exclusions


def should_exclude(item: str, exclusions: List[str]) -> bool:
    """
    Проверяет, нужно ли исключить элемент на основе масок исключений.

    :param item: Имя файла или директории.
    :param exclusions: Список масок исключений.
    :return: True, если элемент нужно исключить, иначе False.
    """
    return any(fnmatch.fnmatch(item, pattern) for pattern in exclusions)


def directory_to_dict(path: str, exclusions: List[str]) -> Union[Dict, str]:
    """
    Рекурсивно обходит директорию и формирует структуру в виде вложенных словарей.

    :param path: Путь к директории.
    :param exclusions: Список масок исключений.
    :return: Структура директории в виде словаря.
    """
    result = {}
    for item in os.listdir(path):
        if should_exclude(item, exclusions):
            continue
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            result[item] = directory_to_dict(item_path, exclusions)
        else:
            with open(item_path, 'r', encoding='utf-8', errors='ignore') as f:
                result[item] = f.read()
    return result


def save_structure_to_json(structure: Dict, output_path: str) -> None:
    """
    Сохраняет структуру директории в файл JSON.

    :param structure: Структура директории.
    :param output_path: Путь к файлу JSON.
    :return: None
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(structure, f, ensure_ascii=False, indent=4)


def directory_to_markdown(path: str, exclusions: List[str]) -> str:
    """
    Рекурсивно обходит директорию и формирует содержимое всех файлов в формате markdown.

    :param path: Путь к директории.
    :param exclusions: Список масок исключений.
    :return: Содержимое всех файлов в формате markdown.
    """
    markdown_content = []
    for item in os.listdir(path):
        if should_exclude(item, exclusions):
            continue
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            markdown_content.append(directory_to_markdown(item_path, exclusions))
        else:
            with open(item_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()
            file_extension = Path(item_path).suffix
            if file_extension == '.py':
                markdown_content.append(f'### {item_path}\n```python\n{file_content}\n```\n')
            else:
                markdown_content.append(f'### {item_path}\n```\n{file_content}\n```\n')
    return '\n'.join(markdown_content)


def update_files_from_json(directory_path: str, json_path: str) -> None:
    """
    Обновляет содержимое файлов по предоставленному JSON-файлу.

    :param directory_path: Абсолютный путь к директории.
    :param json_path: Путь к JSON-файлу с новой структурой.
    :return: None
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        new_structure = json.load(f)

    def update_or_create_file(file_path: str, content: str) -> None:
        """
        Обновляет или создает файл с указанным содержимым.

        :param file_path: Путь к файлу.
        :param content: Новое содержимое файла.
        :return: None
        """
        dir_name = os.path.dirname(file_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            logging.info(f"Создана директория: {dir_name}")

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                old_content = f.read()
            if old_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                old_lines = len(old_content.splitlines())
                new_lines = len(content.splitlines())
                logging.info(f"Обновлен файл: {file_path} (изменено строк: {old_lines} -> {new_lines})")
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"Создан файл: {file_path}")

    def recurse_structure(structure: Dict, current_path: str) -> None:
        """
        Рекурсивно обходит структуру и обновляет или создает файлы.

        :param structure: Структура директории.
        :param current_path: Текущий путь в структуре.
        :return: None
        """
        for name, content in structure.items():
            item_path = os.path.join(current_path, name)
            if isinstance(content, dict):
                recurse_structure(content, item_path)
            else:
                update_or_create_file(item_path, content)

    recurse_structure(new_structure, directory_path)


def main() -> None:
    """
    Основная функция скрипта.

    :return: None
    """
    parser = argparse.ArgumentParser(
        description='Обход директории и формирование структуры или обновление файлов по JSON.')
    parser.add_argument('directory_path', type=str, help='Абсолютный путь к директории.')
    parser.add_argument('--exclude', type=str, default='config.exclude',
                        help='Путь к файлу с конфигурацией исключений.')
    parser.add_argument('--markdown', action='store_true',
                        help='Генерация содержимого файлов в формате markdown.')
    parser.add_argument('--update', type=str, help='Путь к JSON-файлу для обновления содержимого файлов.')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    exclusions = load_exclusions(args.exclude)

    if args.update:
        update_files_from_json(args.directory_path, args.update)
    elif args.markdown:
        markdown_content = directory_to_markdown(args.directory_path, exclusions)
        output_path = os.path.join(args.directory_path, 'directory_structure.md')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f'Markdown содержимое сохранено в {output_path}')
    else:
        structure = directory_to_dict(args.directory_path, exclusions)
        output_path = os.path.join(args.directory_path, 'directory_structure.json')
        save_structure_to_json(structure, output_path)
        print(f'Структура директории сохранена в {output_path}')


if __name__ == '__main__':
    main()

