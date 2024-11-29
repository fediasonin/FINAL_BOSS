import os
import re
from functools import partial

import pandas as pd
import logging
import requests
import time
from urllib3.exceptions import InsecureRequestWarning
from concurrent.futures import ThreadPoolExecutor, Future

def md_to_df(file_path):
    """
    Проверяет файл, обрабатывает таблицу в формате Markdown и возвращает DataFrame.

    :param file_path: Путь к файлу Markdown.
    :return: DataFrame с данными из таблицы или None, если файл не существует или пустой.
    """
    if not os.path.isfile(file_path):
        logging.error(f"Файл {file_path} не найден.")
        return None

    if os.path.getsize(file_path) == 0:
        logging.warning(f"Файл {file_path} пустой.")
        return None

    pattern = r'((\|.*?\|\n)+)'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            md_text = f.read()

        table_text = re.search(pattern, md_text, re.DOTALL).group(1)
        rows = table_text.strip().split('\n')

        data = []
        for row in rows:
            cols = row.strip().split('|')
            cols = [col.strip() for col in cols]
            data.append(cols)

        max_columns = max(len(row) for row in data)
        data = [row + [''] * (max_columns - len(row)) for row in data]

        df = pd.DataFrame(data[1:], columns=data[0])
        df = df.loc[:, df.columns.notnull()]
        df = df.loc[:, df.columns != '']
        df = df.iloc[1:]
        df.replace({'': None}, inplace=True)
        if 'Группа PT-NAD' in df.columns:
            df['Группа PT-NAD'] = df['Группа PT-NAD'].map(
                lambda x: str(x).replace('[', '').replace(']', '') if isinstance(x, str) else x
            )
        logging.info(f"Файл {file_path} успешно обработан")

        return df

    except Exception as e:
        logging.error(f"Ошибка при обработке файла {file_path}: {e}")
        return None

class APIClient:
    def __init__(self, api_base_url, username, password):
        self.session = requests.Session()
        self.api_base_url = api_base_url
        self.create_variable_url = f"{api_base_url}/variables"
        self.username = username
        self.password = password
        self.csrf_token = ''
        self.headers = {
            "Content-Type": "application/json",
            "Referer": self.api_base_url,
            "X-CSRFToken": self.csrf_token
        }
        self.authenticate()

    def authenticate(self):
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        self.session.verify = False

        auth_url = f"{self.api_base_url}/auth/login"
        try:
            response = self.session.post(auth_url, json={"username": self.username, "password": self.password})
            if response.status_code == 200:
                logging.info("Успешная аутентификация")
                if 'csrftoken' in self.session.cookies:
                    self.csrf_token = self.session.cookies['csrftoken']
                    self.headers["X-CSRFToken"] = self.csrf_token
                    logging.info("CSRF токен получен")
                else:
                    logging.warning("CSRF токен не найден в куках")
            else:
                logging.error(f"Ошибка аутентификации: {response.status_code} - {response.text}")
                exit()
        except Exception as e:
            logging.error(f"Ошибка при аутентификации: {e}")
            exit()

    def create_variable(self, name, var_type, value="", comment=""):
        payload = {
            "type": var_type,
            "name": name,
            "value": value,
            "comment": comment
        }
        try:
            response = self.session.post(self.create_variable_url, headers=self.headers, json=payload)
            if response.status_code == 201:
                logging.info(f"Переменная {name} успешно создана")
            else:
                logging.error(f"Ошибка создания переменной {name}: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Ошибка при создании переменной {name}: {e}")

    def close_session(self):
        self.session.close()


class GraphProcessor:
    def __init__(self, api_client, root_filename):
        self.api_client = api_client
        self.root_filename = root_filename
        self.executor = ThreadPoolExecutor(max_workers=4)  # Настройте max_workers

    def process_leaf_node(self, item, parent_data):
        """
        Обрабатывает конечный узел (лист) и отправляет данные через API.
        """
        logging.info(f"Обрабатываю конечный узел (лист): {item['Правило']}")
        comment = f"{item['Описание']} | Родитель: {parent_data.get('Наименование организации', 'Неизвестно')}"
        self.api_client.create_variable(
            name=item['Правило'],
            var_type='rule',
            value=item['Описание'],
            comment=comment
        )

    def process_missing_child(self, missing_filename, parent_data):
        """
        Обрабатывает случай, когда файл ребенка отсутствует.
        """
        logging.warning(f"Файл {missing_filename} не найден. Создаю запись на основе данных родителя.")
        variable_name = os.path.splitext(missing_filename)[0]
        comment = f"Файл {missing_filename} отсутствует. Данные родителя: {parent_data.get('Наименование организации', 'Неизвестно')}"
        self.api_client.create_variable(
            name=variable_name,
            var_type='missing',
            value="",
            comment=comment
        )

    def process_node(self, filename, parent_data=None):
        table = md_to_df(os.path.join(BASE_DIRECTORY, filename))
        print(table.head())
        if table is None:
            return None

        node_future = self.executor.submit(lambda: None)

        if 'Группа PT-NAD' in table.columns:
            child_futures = []
            remaining = 0
            all_children_future = Future()

            for _, item in table.iterrows():
                if pd.notna(item["Группа PT-NAD"]):
                    child_filename = item["Группа PT-NAD"] + '.md'
                    print(child_filename)
                    child_filepath = os.path.join(BASE_DIRECTORY, child_filename)

                    if os.path.exists(child_filepath):
                        child_future = self.executor.submit(self.process_node, child_filename, item)
                        child_futures.append(child_future)
                    elif child_filename != ".md":
                        self.executor.submit(self.process_missing_child, child_filename, item)
                    else:
                        self.executor.submit(self.process_leaf_node, item, parent_data)

            remaining = len(child_futures)

            def all_children_done(fut, parent_data):
                logging.info(f"Обрабатываю узел: {parent_data}")

                if parent_data is None:
                    parent_data = {}

                comment = f"Группа: {parent_data.get('Наименование организации', 'Неизвестно')} | Комментарий: {parent_data.get('Комментарий', 'Нет комментария')}"
                self.api_client.create_variable(
                    name=parent_data.get('Группа PT-NAD', 'Неизвестная группа'),
                    var_type='group',
                    value='',
                    comment=comment
                )
                if not node_future.done():
                    node_future.set_result(None)

            def child_done(fut):
                nonlocal remaining
                remaining -= 1
                if remaining == 0:
                    all_children_future.set_result(None)

            for cf in child_futures:
                cf.add_done_callback(child_done)

            all_children_future.add_done_callback(partial(all_children_done, parent_data=parent_data))

        return node_future

    def start_processing(self):
        root_future = self.process_node(self.root_filename)
        root_future.result()

        # Завершаем executor корректно
        self.executor.shutdown(wait=True)





if __name__ == "__main__":
    BASE_DIRECTORY = r"C:\Users\fedia\PycharmProjects\FINAL_BOSS\PT-NAD_Catalog"
    api_client = APIClient('https://192.168.1.83/api/v2', 'administrator', 'Administr@t0r')
    #os.chdir(R"Z:\PT-NAD_Catalog")
    graph_processor = GraphProcessor(api_client, '!!!Корневой слой.md')
    graph_processor.start_processing()