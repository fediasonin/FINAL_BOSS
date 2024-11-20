import requests
import logging
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

disable_warnings(category=InsecureRequestWarning)

"""
сделать класс статичным
поработать с многопотоком для парсера
убрать лишние параметры в парсере
повысить лимит get
структура
sourse файл 
в различияъ linux и windows добвить определение платформы
"""

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

    def get_all_variables(self):
        all_variables = []
        url = self.create_variable_url
        while url:
            try:
                response = self.session.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    all_variables.extend(data.get('results', []))
                    url = data.get('next')
                else:
                    logging.error(f"Ошибка получения переменных: {response.status_code} - {response.text}")
                    break
            except Exception as e:
                logging.error(f"Ошибка при запросе списка переменных: {e}")
                break
        return all_variables

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

    def delete_variable(self, variable):
        variable_id = variable['id']
        diff = variable['diff']
        delete_url = f"{self.create_variable_url}/{variable_id}"
        try:
            response = self.session.delete(delete_url, headers=self.headers)
            if response.status_code == 204 or (response.status_code == 200 and diff in ['=', '*', '-']):
                logging.info(f"Переменная с ID {variable_id} успешно обработана (diff: {diff})")
            else:
                logging.error(f"Ошибка удаления переменной с ID {variable_id}: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Ошибка при удалении переменной с ID {variable_id}: {e}")

    def delete_all_variables(self):
        variables = self.get_all_variables()
        if variables:
            logging.info(f"Найдено {len(variables)} переменных для удаления")
            for variable in variables:
                self.delete_variable(variable)
        else:
            logging.info("Переменных для удаления не найдено")

    def update_variable(self, variable_id, new_value):
        url = f"{self.create_variable_url}/{variable_id}"
        payload = {"value": new_value}
        try:
            response = self.session.put(url, headers=self.headers, json=payload)
            if response.status_code == 200:
                logging.info(f"Переменная с ID {variable_id} успешно обновлена. Новое значение: {new_value}")
            else:
                logging.error(
                    f"Ошибка обновления переменной с ID {variable_id}: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Ошибка при обновлении переменной с ID {variable_id}: {e}")

    def close_session(self):
        self.session.close()