import os
import re
import logging


def sanitize_name(name):
    """
    Убирает недопустимые символы и приводит имя к безопасному формату.
    """
    name = name.strip()
    name = re.sub(r'[^\w\d_-]', '_', name)  # Замена запрещённых символов на "_"
    return name.encode('ascii', errors='ignore').decode('ascii')


def parse_agency_file(filepath):
    agencies = {}
    parent_agency = os.path.basename(filepath).replace('.md', '')
    agencies[parent_agency] = {'children': [], 'ip_addresses': []}
    has_children = False

    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                child_agency_match = re.search(r'\[\[\$(.*?)\]\]', line)
                if child_agency_match:
                    has_children = True
                    child_agency = child_agency_match.group(1).strip()
                    agencies[parent_agency]['children'].append(child_agency)
                ip_match = re.search(r'\b\d{1,3}(\.\d{1,3}){3}/\d{1,2}\b', line)
                if ip_match:
                    ip_address = ip_match.group()
                    description = line.split('|')[-1].strip()
                    agencies[parent_agency]['ip_addresses'].append((ip_address, description))

        if not has_children:
            agencies[parent_agency]['children'] = None
    except FileNotFoundError:
        logging.warning(f"File not found: {filepath}. Marking as empty.")
        agencies[parent_agency] = {'children': None, 'ip_addresses': []}

    return agencies


def collect_hierarchy(directory, filename="!!!Корневой слой.md", processed=None):
    """
    Сбор всех данных в памяти (рекурсивно), возвращает полный словарь.
    """
    if processed is None:
        processed = set()

    filepath = os.path.join(directory, filename)

    if filepath in processed:
        logging.warning(f"Circular reference detected for file: {filepath}. Skipping.")
        return {}

    processed.add(filepath)

    hierarchy = parse_agency_file(filepath)
    full_hierarchy = {}

    for agency, details in hierarchy.items():
        full_hierarchy[agency] = details
        if details['children']:
            for child in details['children']:
                child_hierarchy = collect_hierarchy(directory, f"${child}.md", processed)
                full_hierarchy.update(child_hierarchy)

    return full_hierarchy


def upload_hierarchy(api_client, hierarchy):
    """
    Загрузка данных в API батчами.
    """
    for agency, details in hierarchy.items():
        cleaned_name = sanitize_name(agency.replace("$", ""))

        if details['children'] and details['ip_addresses']:
            value = ", ".join(f"${sanitize_name(child)}" for child in details['children']) + ", " + ", ".join(
                ip for ip, _ in details['ip_addresses'])
        elif details['children']:
            value = ", ".join(f"${sanitize_name(child)}" for child in details['children'])
        elif details['ip_addresses']:
            value = ", ".join(ip for ip, _ in details['ip_addresses'])
        else:
            value = ""

        try:
            api_client.create_variable(name=cleaned_name, var_type="ip", value=value, comment="")
        except Exception as e:
            logging.error(f"Ошибка создания переменной {cleaned_name}: {e}")


def upload_variable(api_client, agency_name, details):
    """
    Отправляет данные об одной переменной в API.
    """
    cleaned_name = sanitize_name(agency_name.replace("$", ""))

    if details['children'] and details['ip_addresses']:
        value = ", ".join(f"${sanitize_name(child)}" for child in details['children']) + ", " + ", ".join(
            ip for ip, _ in details['ip_addresses'])
    elif details['children']:
        value = ", ".join(f"${sanitize_name(child)}" for child in details['children'])
    elif details['ip_addresses']:
        value = ", ".join(ip for ip, _ in details['ip_addresses'])
    else:
        value = ""

    try:
        api_client.create_variable(name=cleaned_name, var_type="ip", value=value, comment="")
        logging.info(f"Переменная {cleaned_name} успешно обновлена.")
    except Exception as e:
        logging.error(f"Ошибка обновления переменной {cleaned_name}: {e}")


def handle_full_reset(api_client, directory_path):
    """
    Полностью удаляет все переменные и пересоздаёт их.
    """
    try:
        logging.info("Полное удаление всех переменных...")
        api_client.delete_all_variables()
        logging.info("Все переменные успешно удалены.")

        # Запуск полного парсинга и обновления переменных
        parse_hierarchy(api_client, directory_path)
    except Exception as e:
        logging.error(f"Ошибка при полном обновлении переменных: {e}")


def parse_hierarchy(api_client, directory, filename="!!!Корневой слой.md"):
    """
    Рекурсивно обрабатывает иерархию, начиная с корневого слоя.
    """
    filepath = os.path.join(directory, filename)
    hierarchy = parse_agency_file(filepath)

    for agency, details in hierarchy.items():
        if details['children']:
            for child in details['children']:
                parse_hierarchy(api_client, directory, f"${child}.md")

        upload_variable(api_client, agency, details)
