import json
import logging
import time
import asyncio
from scripts.API_CLIENT import APIClient
from scripts.utilits import collect_hierarchy, upload_hierarchy
from scripts.patching import monitor_directory

logging.basicConfig(level=logging.INFO)


with open('credits.json', 'r') as f:
    credits = json.load(f)

API_BASE_URL = credits['api_base_url']
USERNAME = credits['username']
PASSWORD = credits['password']
DIRECTORY_PATH = credits['directory_path']


async def first_load(api_client):
    """Асинхронная первая загрузка данных."""
    logging.info("Начало первой загрузки...")
    start_time = time.time()

    hierarchy = await collect_hierarchy(DIRECTORY_PATH)  # Ожидаем завершения асинхронной функции

    upload_hierarchy(api_client, hierarchy)

    end_time = time.time()
    logging.info(f"Execution time: {end_time - start_time} seconds.")
    logging.info("Первая загрузка завершена.")


async def patching(api_client):
    """Асинхронная функция для мониторинга изменений."""
    logging.info("Начало мониторинга изменений...")
    await monitor_directory(api_client, DIRECTORY_PATH)
    logging.info("Мониторинг завершён.")


async def main():
    """Главная асинхронная функция для выполнения задач."""
    api_client = APIClient(API_BASE_URL, USERNAME, PASSWORD)
    try:
        await first_load(api_client)
        await patching(api_client)
    finally:
        api_client.close_session()


if __name__ == "__main__":
    asyncio.run(main())
