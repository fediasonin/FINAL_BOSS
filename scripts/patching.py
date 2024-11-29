import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import API_CLIENT

class DataSyncService:
    def __init__(self, storage, api_client):
        """
        storage: хранилище данных (например, объект класса для работы с БД или API).
        api_client: клиент для работы с удалённым API.
        """
        self.storage = storage
        self.api_client = api_client
        self.scheduler = BackgroundScheduler()

    def sync_data(self):
        """Основной метод для синхронизации данных."""
        logging.info("Начало синхронизации данных...")
        try:
            # Получить обновления из хранилища
            updated_records = self.storage.get_updated_records()
            for record in updated_records:
                self.process_record(record)

            # Получить записи, которые нужно удалить
            deleted_records = self.storage.get_deleted_records()
            for record in deleted_records:
                self.api_client.delete_variable(record)

        except Exception as e:
            logging.error(f"Ошибка в процессе синхронизации данных: {e}")

    def process_record(self, record):
        """
        Обрабатывает один изменённый/новый элемент из хранилища.
        Если запись новая — создаёт переменную,
        если существующая — обновляет.
        """
        variable_id = record.get("id")
        name = record.get("name")
        var_type = record.get("type")
        value = record.get("value", "")
        comment = record.get("comment", "")

        if variable_id:  # Если запись уже существует, обновить
            logging.info(f"Обновление переменной ID={variable_id}...")
            self.api_client.update_variable(variable_id, value)
        else:  # Если запись новая, создать
            logging.info(f"Создание новой переменной {name}...")
            self.api_client.create_variable(name, var_type, value, comment)

    def start(self, interval_seconds):
        """Запускает службу с указанным интервалом."""
        logging.info("Запуск службы синхронизации данных...")
        self.scheduler.add_job(self.sync_data, 'interval', seconds=interval_seconds)
        self.scheduler.start()

    def stop(self):
        """Останавливает службу."""
        logging.info("Остановка службы синхронизации данных...")
        self.scheduler.shutdown()


# Пример использования:
class MockStorage:
    """Пример хранилища данных."""
    def get_updated_records(self):
        # Возвращает список обновлённых записей
        return [
            {"id": 1, "name": "var1", "type": "string", "value": "new_value1", "comment": "Updated value"},
            {"name": "var2", "type": "integer", "value": "42", "comment": "New variable"},
        ]

    def get_deleted_records(self):
        # Возвращает список записей для удаления
        return [{"id": 2, "diff": "-"}]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Инициализация клиента и хранилища
    api_client = API_CLIENT.APIClient(api_base_url="https://api.example.com", username="user", password="pass")
    storage = MockStorage()

    # Запуск службы синхронизации
    service = DataSyncService(storage, api_client)
    service.start(interval_seconds=60)  # Выполнять каждые 60 секунд

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()
