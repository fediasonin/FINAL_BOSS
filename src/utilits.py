import os
import re
import logging
from multiprocessing import Pool

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

def collect_hierarchy_child(args):
    directory, filename = args
    return collect_hierarchy_single(directory, filename)

def collect_hierarchy_single(directory, filename):
    """Обрабатывает один файл (без рекурсии)."""
    filepath = os.path.join(directory, filename)
    return parse_agency_file(filepath)

def collect_hierarchy(directory, filename="!!!Корневой слой.md"):
    """
    Сбор всех данных в памяти с использованием пула процессов.
    Переходим к итеративному подходу (BFS) вместо рекурсивного.
    """
    # Инициализируем пул процессов
    with Pool() as pool:
        # Очередь для обхода
        queue = [filename]
        full_hierarchy = {}
        visited = set()

        while queue:
            # Обрабатываем текущий уровень файлов
            current_files = queue
            queue = []
            args_list = [(directory, f) for f in current_files]

            # Параллельная обработка файлов
            results = pool.map(collect_hierarchy_child, args_list)

            for fname, res in zip(current_files, results):
                filepath = os.path.join(directory, fname)
                if filepath in visited:
                    continue
                visited.add(filepath)
                full_hierarchy.update(res)

                # Добавляем дочерние файлы следующего уровня
                for agency, details in res.items():
                    if details['children']:
                        for child in details['children']:
                            child_filename = f"${child}.md"
                            child_path = os.path.join(directory, child_filename)
                            if child_path not in visited:
                                queue.append(child_filename)

        return full_hierarchy


def upload_hierarchy(api_client, hierarchy):
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

def sanitize_name(name):
    name = name.strip()
    name = re.sub(r'[^\w\d_-]', '_', name)
    return name.encode('ascii', errors='ignore').decode('ascii')


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
