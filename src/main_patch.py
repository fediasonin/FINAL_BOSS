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



def pathcing():
    api_client = APIClient(API_BASE_URL, USERNAME, PASSWORD)
    monitor_directory(api_client, DIRECTORY_PATH)
    api_client.close_session()


pathcing()