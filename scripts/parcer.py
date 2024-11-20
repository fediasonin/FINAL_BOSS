import os
import re


def parse_agency_file_universal(filepath):
    agencies = {}
    parent_agency = os.path.basename(filepath).replace('.md', '')  # Извлекаем название материнской организации из имени файла
    agencies[parent_agency] = {'children': [], 'ip_addresses': []}
    has_children = False  # Флаг для проверки наличия дочерних ведомств

    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            # Поиск дочерних ведомств в формате [[...]]
            child_agency_match = re.search(r'\[\[\$(.*?)\]\]', line)
            if child_agency_match:
                has_children = True
                child_agency = child_agency_match.group(1).strip()
                agencies[parent_agency]['children'].append(child_agency)
            # Поиск IP-адресов в формате CIDR (с маской) или без маски
            ip_match = re.search(r'\b\d{1,3}(\.\d{1,3}){3}/\d{1,2}\b', line)
            if ip_match:
                ip_address = ip_match.group()
                description = line.split('|')[-1].strip()  # Описание для IP-адреса, если оно присутствует
                agencies[parent_agency]['ip_addresses'].append((ip_address, description))

    # Если дочерних ведомств не найдено, интерпретируем файл как низший уровень
    if not has_children:
        agencies[parent_agency]['children'] = None  # Устанавливаем в None, если это нижний уровень

    return agencies



file_path = "../PT-NAD_Catalog/$GU_MIR_SUDEY.md"
file_path_low_level = "../PT-NAD_Catalog/$MIR_SUD_69.md"

parsed_data_upper_level = parse_agency_file_universal(file_path)          # Файл с дочерними ведомствами
parsed_data_lowest_level = parse_agency_file_universal(file_path_low_level)  # Файл с IP-адресами на нижнем уровне

print(parsed_data_upper_level,"\n\n", parsed_data_lowest_level)

