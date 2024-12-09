import os
import re
import logging
import asyncio
from aiofiles import open as aio_open
from aiofiles.os import path as aio_path


def sanitize_name(name):
    """Убирает недопустимые символы и приводит имя к безопасному формату."""
    name = name.strip()
    name = re.sub(r'[^\w\d_-]', '_', name)
    return name.encode('ascii', errors='ignore').decode('ascii')


async def parse_agency_file(filepath):
    """Асинхронно обрабатывает файл и возвращает иерархию."""
    agencies = {}
    parent_agency = os.path.basename(filepath).replace('.md', '')
    agencies[parent_agency] = {'children': [], 'ip_addresses': []}
    has_children = False

    if not await aio_path.exists(filepath):
        logging.warning(f"File not found: {filepath}. Marking as empty.")
        agencies[parent_agency] = {'children': None, 'ip_addresses': []}
        return agencies

    async with aio_open(filepath, 'r', encoding='utf-8') as file:
        async for line in file:
            child_match = re.search(r'\[\[\$(.*?)\]\]', line)
            ip_match = re.search(r'\b\d{1,3}(\.\d{1,3}){3}/\d{1,2}\b', line)

            if child_match:
                has_children = True
                child_agency = child_match.group(1).strip()
                agencies[parent_agency]['children'].append(child_agency)

            if ip_match:
                ip_address = ip_match.group()
                description = line.split('|')[-1].strip()
                agencies[parent_agency]['ip_addresses'].append((ip_address, description))

    if not has_children:
        agencies[parent_agency]['children'] = None

    return agencies


async def collect_hierarchy(directory, filename="!!!Корневой слой.md", processed=None):
    """Асинхронный сбор иерархии."""
    if processed is None:
        processed = set()

    filepath = os.path.join(directory, filename)

    if filepath in processed:
        logging.warning(f"Circular reference detected for file: {filepath}. Skipping.")
        return {}

    processed.add(filepath)
    hierarchy = await parse_agency_file(filepath)
    full_hierarchy = {}

    tasks = []
    for agency, details in hierarchy.items():
        full_hierarchy[agency] = details
        if details['children']:
            for child in details['children']:
                child_filename = f"${child}.md"
                tasks.append(collect_hierarchy(directory, child_filename, processed))

    # Параллельное выполнение всех дочерних задач
    results = await asyncio.gather(*tasks)
    for result in results:
        full_hierarchy.update(result)

    return full_hierarchy


def build_variable_value(details):
    """Создает значение переменной из её деталей."""
    if details['children'] and details['ip_addresses']:
        value = ", ".join(f"${sanitize_name(child)}" for child in details['children']) + ", " + ", ".join(
            ip for ip, _ in details['ip_addresses'])
    elif details['children']:
        value = ", ".join(f"${sanitize_name(child)}" for child in details['children'])
    elif details['ip_addresses']:
        value = ", ".join(ip for ip, _ in details['ip_addresses'])
    else:
        value = ""
    return value


def upload_hierarchy(api_client, hierarchy):
    """Загрузка иерархии в API."""
    for agency, details in hierarchy.items():
        upload_variable(api_client, agency, details)


def upload_variable(api_client, agency_name, details):
    """Отправляет данные об одной переменной в API."""
    cleaned_name = sanitize_name(agency_name.replace("$", ""))
    value = build_variable_value(details)

    try:
        api_client.create_variable(name=cleaned_name, var_type="ip", value=value, comment="")
        logging.info(f"Переменная {cleaned_name} успешно обновлена.")
    except Exception as e:
        logging.error(f"Ошибка обновления переменной {cleaned_name}: {e}")


async def handle_full_reset(api_client, directory_path):
    """Удаление всех переменных и пересоздание."""
    try:
        logging.info("Полное удаление всех переменных...")
        api_client.delete_all_variables()
        logging.info("Все переменные успешно удалены.")

        # Асинхронный сбор иерархии
        logging.info("Начало обработки иерархии...")
        hierarchy = await collect_hierarchy(directory_path)
        upload_hierarchy(api_client, hierarchy)
    except Exception as e:
        logging.error(f"Ошибка при полном обновлении переменных: {e}")