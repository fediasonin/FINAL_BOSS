import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache


class APIClient:
    _instance = None

    def __new__(cls, api_base_url, username, password):
        # Если экземпляр ещё не создан, создаём его
        if cls._instance is None:
            cls._instance = super(APIClient, cls).__new__(cls)
            cls._instance._init_instance(api_base_url, username, password)
        return cls._instance

    def _init_instance(self, api_base_url, username, password):
        """Инициализация экземпляра."""
        self.session = requests.Session()
        self.api_base_url = api_base_url
        self.create_variable_url = f"{api_base_url}/variables"
        self.username = username
        self.password = password
        self.csrf_token = ''
        self.headers = {
            "Content-Type": "application/json",
            "Referer": self.api_base_url,
            "X-CSRFToken": self.csrf_token,
            "Accept-Encoding": "gzip, deflate"
        }
        self._configure_session()
        self.authenticate()

    def _configure_session(self):
        """Настройка пула соединений и ретраев."""
        adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=Retry(total=3, backoff_factor=0.3))
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.verify = False  # Отключить проверку SSL

    def authenticate(self):
        """Аутентификация и получение CSRF токена."""
        requests.packages.urllib3.disable_warnings(category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

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

    @lru_cache(maxsize=128)
    def get_all_variables(self):
        """Получает все переменные с сервера с кешированием."""
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

        logging.info(f"Получено переменных: {len(all_variables)}")
        return all_variables

    def create_variable(self, name, var_type, value="", comment=""):
        """Создает новую переменную."""
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

    def delete_all_variables(self):
        """Удаляет все переменные параллельно."""
        variables = self.get_all_variables()
        if variables:
            logging.info(f"Найдено {len(variables)} переменных для удаления")
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(self.delete_variable, variables)
        else:
            logging.info("Переменных для удаления не найдено")

    def update_variable(self, variable_id, new_value):
        """Обновляет переменную по ID."""
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

    def get_variable_by_name(self, variable_name):
        """Получает объект переменной по имени."""
        clean_name = variable_name.strip().upper()
        logging.info(f"Ищем переменную с именем: {clean_name}")

        url = self.create_variable_url
        while url:
            try:
                response = self.session.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    variable = next(
                        (var for var in data.get('results', []) if var['name'].upper() == clean_name), None)
                    if variable:
                        logging.info(f"Переменная найдена: {variable}")
                        return variable
                    url = data.get('next')
                else:
                    logging.error(f"Ошибка при запросе переменных: {response.status_code} - {response.text}")
                    break
            except Exception as e:
                logging.error(f"Ошибка при попытке получить переменную {clean_name}: {e}")
                break

        logging.warning(f"Переменная с именем {clean_name} не найдена.")
        return None

    def delete_variable(self, variable):
        """Удаляет переменную по ID."""
        variable_id = variable['id']
        delete_url = f"{self.create_variable_url}/{variable_id}"

        try:
            response = self.session.delete(delete_url, headers=self.headers)
            if response.status_code in [204, 200]:
                logging.info(f"Переменная с ID {variable_id} успешно удалена.")
            else:
                logging.error(f"Ошибка удаления переменной с ID {variable_id}: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Ошибка при удалении переменной с ID {variable_id}: {e}")

    def close_session(self):
        """Закрывает сессию."""
        self.session.close()