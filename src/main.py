import json
import logging
import time
from multiprocessing import Pool

from api_client import APIClient
from utilits import collect_hierarchy, upload_hierarchy
from patching import monitor_directory

logging.basicConfig(level=logging.INFO)

with open('../credits.json', 'r') as f:
    credits = json.load(f)

API_BASE_URL = credits['api_base_url']
USERNAME = credits['username']
PASSWORD = credits['password']
DIRECTORY_PATH = credits['directory_path']


def first_load():
    api_client = APIClient(API_BASE_URL, USERNAME, PASSWORD)

    start_time = time.time()

    # Используем пул процессов для параллельного сбора иерархии
    with Pool() as pool:
        hierarchy = collect_hierarchy(DIRECTORY_PATH)

    # Отправка данных в API
    upload_hierarchy(api_client, hierarchy)

    api_client.close_session()

    end_time = time.time()
    logging.info(f"Execution time: {end_time - start_time} seconds.")


def pathcing():
    api_client = APIClient(API_BASE_URL, USERNAME, PASSWORD)
    monitor_directory(api_client, DIRECTORY_PATH)
    api_client.close_session()


if __name__ == "__main__":
    first_load()
    pathcing()
