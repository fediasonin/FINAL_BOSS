import os
import re
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from API_CLIENT import APIClient

logging.basicConfig(level=logging.INFO)

# ===== Утилиты ===== #

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


# ===== Обработчик событий ===== #

class DirectoryChangeHandler(FileSystemEventHandler):
    def __init__(self, api_client, directory):
        """
        Инициализация обработчика изменений.
        :param api_client: Экземпляр APIClient
        :param directory: Путь к директории для отслеживания изменений
        """
        self.api_client = api_client
        self.directory = directory

    def on_modified(self, event):
        """
        Обрабатывает модификацию файлов.
        """
        if event.is_directory:
            return

        if event.src_path.endswith('.md'):
            logging.info(f"Обнаружено изменение файла: {event.src_path}")
            self.update_variable_or_reset(event.src_path)

    def on_created(self, event):
        """
        Обрабатывает создание файлов.
        """
        if event.is_directory:
            return

        if event.src_path.endswith('.md'):
            logging.info(f"Обнаружено создание файла: {event.src_path}")
            self.update_variable_or_reset(event.src_path)

    def on_deleted(self, event):
        """
        Обрабатывает удаление файла или директории.
        """
        if not event.is_directory and event.src_path.endswith(".md"):
            # Очистка имени: удаляем '$' и '.md'
            agency_name = os.path.basename(event.src_path).replace(".md", "").replace("$", "")
            try:
                # Удаляем переменную через API-клиент
                variable = self.api_client.get_variable_by_name(agency_name)
                if variable:
                    self.api_client.delete_variable(variable)
                else:
                    logging.warning(f"Переменная с именем {agency_name} не найдена для удаления.")
            except Exception as e:
                logging.error(f"Ошибка удаления переменной {agency_name}: {e}")

    def update_variable_or_reset(self, filepath):
        """
        Обновляет переменную или выполняет полный сброс переменных.
        """
        filename = os.path.basename(filepath)
        if filename == "!!!Корневой слой.md":  # Проверка изменения главного узла
            logging.info("Изменён узел верхнего уровня. Выполняется полный сброс переменных.")
            handle_full_reset(self.api_client, self.directory)
        else:
            logging.info(f"Обновление переменной для файла: {filepath}")
            agency_data = parse_agency_file(filepath)
            for agency, details in agency_data.items():
                upload_variable(self.api_client, agency, details)



# ===== Парсинг и иерархия ===== #

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


# ===== Основная программа ===== #

def monitor_directory(api_client, directory_path):
    """
    Запуск наблюдателя за изменениями в директории.
    """
    event_handler = DirectoryChangeHandler(api_client, directory_path)
    observer = Observer()
    observer.schedule(event_handler, path=directory_path, recursive=True)
    observer.start()

    try:
        logging.info(f"Наблюдение за изменениями в директории: {directory_path}")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


def patching():
    api_base_url = "https://192.168.1.83/api/v2"
    username = "administrator"
    password = 'Administr@t0r'

    api_client = APIClient(api_base_url, username, password)
    directory_path = 'PT-NAD_Catalog/'

    # Запуск наблюдения за директорией
    monitor_directory(api_client, directory_path)

    api_client.close_session()



