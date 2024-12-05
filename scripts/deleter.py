import json
import os

from API_CLIENT import APIClient
os.chdir('C:/Users/fedia/PycharmProjects/FINAL_BOSS')
with open('credits.json', 'r') as f:
    credits = json.load(f)
API_BASE_URL = credits['api_base_url']
USERNAME = credits['username']
PASSWORD = credits['password']
DIRECTORY_PATH = credits['directory_path']
f.close()

api_client = APIClient(API_BASE_URL, USERNAME, PASSWORD)

try:
    api_client.delete_all_variables()
    print("Все переменные успешно удалены.")
except Exception as e:
    print(f"Ошибка при удалении переменных: {e}")
finally:
    api_client.close_session()