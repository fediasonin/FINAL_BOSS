from scripts.api_client import APIClient  # Импортируем ваш класс APIClient


def replace_ip_in_variable(api_client, variable_id, old_ip, new_ip):
    variables = api_client.get_all_variables()
    variable = next((v for v in variables if v["id"] == variable_id), None)

    if not variable:
        print(f"Переменная с ID {variable_id} не найдена.")
        return

    value = variable.get("value", "")

    if old_ip not in value:
        print(f"IP-адрес {old_ip} не найден в переменной {variable['name']}.")
        return

    updated_value = value.replace(old_ip, new_ip).strip(", ")

    # Обновляем переменную
    if updated_value != value:
        api_client.update_variable(variable_id, updated_value)
        print(f"IP-адрес {old_ip} успешно заменён на {new_ip} в переменной {variable['name']}.")
    else:
        print(f"Значение переменной {variable['name']} не изменилось.")


if __name__ == "__main__":
    # Укажите ваш URL API, имя пользователя и пароль
    API_BASE_URL = "https://192.168.1.83/api/v2"
    USERNAME = "administrator"
    PASSWORD = "Administr@t0r"

    # Создаем экземпляр клиента API
    api_client = APIClient(API_BASE_URL, USERNAME, PASSWORD)

    try:
        # Укажите ID переменной, старый и новый IP-адрес
        variable_id = 5132  # Замените на нужный ID переменной
        old_ip = "10.151.252.204/30"  # Старый IP, который нужно заменить
        new_ip = "192.168.1.0/24"  # Новый IP, на который заменить

        # Заменяем IP-адрес в переменной
        replace_ip_in_variable(api_client, variable_id, old_ip, new_ip)
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        # Закрываем сессию
        api_client.close_session()

"""
API_BASE_URL = "https://192.168.1.83/api/v2"
USERNAME = "administrator"
PASSWORD = "Administr@t0r"

variable_id = 3675
variable_name = "MIR_SUD_1"
"""