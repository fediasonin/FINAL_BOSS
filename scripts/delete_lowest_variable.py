from scripts.api_client import APIClient

if __name__ == "__main__":
    API_BASE_URL = "https://192.168.1.83/api/v2"
    USERNAME = "administrator"
    PASSWORD = "Administr@t0r"

    api_client = APIClient(API_BASE_URL, USERNAME, PASSWORD)

    try:
        group_name = "GU_MIR_SUDEY"
        group_reference = f"${group_name}"

        variables = api_client.get_all_variables()

        for variable in variables:
            if group_reference in variable.get("value", ""):
                values = [v.strip() for v in variable["value"].split(",") if v.strip() and v.strip() != group_reference]
                updated_value = ", ".join(values)
                api_client.update_variable(variable["id"], updated_value)
                print(f"Обновлено значение переменной {variable['name']} без ссылки на {group_name}")

        group_to_delete = next((v for v in variables if v["name"] == group_name), None)
        if group_to_delete:
            api_client.delete_variable(group_to_delete)
            print(f"Группа {group_name} успешно удалена.")
        else:
            print(f"Группа {group_name} не найдена.")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        api_client.close_session()


"""
API_BASE_URL = "https://192.168.1.83/api/v2"
USERNAME = "administrator"
PASSWORD = "Administr@t0r"

variable_id = 3675
variable_name = "MIR_SUD_1"
"""