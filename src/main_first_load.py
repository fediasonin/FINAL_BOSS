import logging
import time
from multiprocessing import Pool
import os

from dotenv import load_dotenv
from api_client import APIClient
from utilits import collect_hierarchy, upload_hierarchy
from patching import monitor_directory

logging.basicConfig(level=logging.INFO)

load_dotenv()

API_BASE_URL = os.getenv('API_BASE_URL')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
DIRECTORY_PATH = os.getenv('DIRECTORY_PATH')

print(f"API URL: {API_BASE_URL}")
print(f"Username: {USERNAME}")
print(f"Directory Path: {DIRECTORY_PATH}")


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



first_load()
pathcing()
