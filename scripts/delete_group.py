from scripts.api_client import APIClient  # Импортируем ваш класс APIClient


def build_dependency_tree(api_client):
    """
    Построить дерево зависимости переменных.
    """
    variables = api_client.get_all_variables()
    dependency_tree = {}

    for variable in variables:
        group_name = variable["name"]
        value = variable.get("value", "")
        # Найти все ссылки на другие группы в поле value
        references = [v.strip("$") for v in value.split(",") if v.strip().startswith("$")]
        dependency_tree[group_name] = references

    return dependency_tree


def get_removal_order(dependency_tree):
    """
    Получить порядок удаления групп (сначала листья, затем родительские группы).
    """
    removal_order = []

    def visit(group_name):
        # Если группа уже обработана, пропускаем
        if group_name in removal_order:
            return
        # Рекурсивно обходим все зависимости
        for dependency in dependency_tree.get(group_name, []):
            visit(dependency)
        # Добавляем группу в порядок удаления
        removal_order.append(group_name)

    # Обходим все группы в дереве
    for group in dependency_tree:
        visit(group)

    return removal_order


def delete_group(api_client, group_name):
    """
    Удалить группу и все ссылки на неё.
    """
    group_reference = f"${group_name}"
    variables = api_client.get_all_variables()

    # Удаляем ссылки на группу
    for variable in variables:
        if group_reference in variable.get("value", ""):
            # Удаляем ссылку из поля value
            updated_value = [v.strip() for v in variable["value"].split(",") if v.strip() != group_reference]
            updated_value = ", ".join(updated_value).replace(",,", ",").strip(", ")
            api_client.update_variable(variable["id"], updated_value)
            print(f"Обновлено значение переменной {variable['name']} без ссылки на {group_name}")

    # Удаляем саму группу
    group_to_delete = next((v for v in variables if v["name"] == group_name), None)
    if group_to_delete:
        api_client.delete_variable(group_to_delete)
        print(f"Группа {group_name} успешно удалена.")


if __name__ == "__main__":
    # Укажите ваш URL API, имя пользователя и пароль
    API_BASE_URL = "https://192.168.1.83/api/v2"
    USERNAME = "administrator"
    PASSWORD = "Administr@t0r"

    # Создаем экземпляр клиента API
    api_client = APIClient(API_BASE_URL, USERNAME, PASSWORD)

    try:
        # Укажите имя главной группы для удаления
        root_group_name = "MIR_SUD_1"

        # Построить дерево зависимости
        dependency_tree = build_dependency_tree(api_client)
        print("Дерево зависимости:", dependency_tree)

        # Получить порядок удаления
        removal_order = get_removal_order(dependency_tree)
        print("Порядок удаления:", removal_order)

        # Удаляем группы в порядке удаления
        for group_name in reversed(removal_order):  # Сначала нижние группы
            delete_group(api_client, group_name)

        print(f"Группа {root_group_name} и все её зависимости успешно удалены.")
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
