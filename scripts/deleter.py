from API_CLIENT import APIClient  # Импортируем ваш класс APIClient

if __name__ == "__main__":
    API_BASE_URL = "https://192.168.1.83/api/v2"
    USERNAME = "administrator"
    PASSWORD = "Administr@t0r"

    api_client = APIClient(API_BASE_URL, USERNAME, PASSWORD)

    try:
        api_client.delete_all_variables()
        print("Все переменные успешно удалены.")
    except Exception as e:
        print(f"Ошибка при удалении переменных: {e}")
    finally:
        api_client.close_session()

""" 

API_BASE_URL = "https://192.168.1.83/api/v2"
USERNAME = "administrator"
PASSWORD = "Administr@t0r"

"""


