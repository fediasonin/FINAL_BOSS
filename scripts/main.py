import os
import re
import time
import logging
from api_client import APIClient

logging.basicConfig(level=logging.INFO)


def parse_agency_file(filepath):
    agencies = {}
    parent_agency = os.path.basename(filepath).replace('.md', '')
    agencies[parent_agency] = {'children': [], 'ip_addresses': []}
    has_children = False

    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            child_agency_match = re.search(r'\[\[\$(.*?)\]\]', line)
            if child_agency_match:
                has_children = True
                child_agency = child_agency_match.group(1).strip()
                agencies[parent_agency]['children'].append(child_agency)
            ip_match = re.search(r'\b\d{1,3}(\.\d{1,3}){3}/\d{1,2}\b', line)
            if ip_match:
                ip_address = ip_match.group()
                description = line.split('|')[-1].strip()
                agencies[parent_agency]['ip_addresses'].append((ip_address, description))

    if not has_children:
        agencies[parent_agency]['children'] = None
    return agencies


def parse_hierarchy(api_client, directory, filename="!!!Корневой слой.md"):
    """
    файлы в df
    многопоток ?
    делаем из md csv
    """
    filepath = os.path.join(directory, filename)
    hierarchy = parse_agency_file(filepath)

    for agency, details in hierarchy.items():
        if details['children']:
            for child in details['children']:
                parse_hierarchy(api_client, directory, f"${child}.md")

        cleaned_name = agency.replace("$", "")

        if details['children'] and details['ip_addresses']:
            value = ", ".join(f"${child}" for child in details['children']) + ", " + ", ".join(
                ip for ip, _ in details['ip_addresses'])
        elif details['children']:
            value = ", ".join(f"${child}" for child in details['children'])
        elif details['ip_addresses']:
            value = ", ".join(ip for ip, _ in details['ip_addresses'])
        else:
            value = ""

        api_client.create_variable(name=cleaned_name, var_type="ip", value=value, comment="")


def main():
    api_base_url = "https://192.168.1.83/api/v2"
    username = "administrator"
    password = 'Administr@t0r'

    api_client = APIClient(api_base_url, username, password)
    directory_path = '../PT-NAD_Catalog/'

    parse_hierarchy(api_client, directory_path)

    api_client.close_session()


if __name__ == "__main__":
    start_time = time.time()
    try:
        main()
    finally:
        print("Нажмите любую клавишу, чтобы выйти...")
    end_time = time.time()
    print(end_time - start_time)

