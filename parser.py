import os
import io
import sys
import json
import shutil
import pathlib
import zipfile
import pandas as pd
from lxml import html
from pathlib import Path
from authorization import auth
from dotenv import load_dotenv
from requests.exceptions import ConnectionError

load_dotenv()

NAME = os.getenv('NAME')
LOGIN = os.getenv('LOGIN')
PASSWD = os.getenv('PASSWORD')
IS_LOAD = True if os.getenv('IS_LOAD') == 'True' else False
FULL_NAME = None

key_teacher = None

Path(pathlib.Path.cwd(), "json", "teachers").mkdir(parents=True, exist_ok=True)
Path(pathlib.Path.cwd(), "json", "events").mkdir(parents=True, exist_ok=True)
Path(pathlib.Path.cwd(), "EXCEL").mkdir(parents=True, exist_ok=True)
teachers_path = os.path.join(pathlib.Path.cwd(), 'json', 'teachers')
events_path = os.path.join(pathlib.Path.cwd(), 'json', 'events')
xlsx_path = os.path.join(pathlib.Path.cwd(), 'EXCEL')
files_path = 'homework_files'

try:
    shutil.rmtree(files_path)
except OSError as e:
    pass

path = "//div[@class='events-left-block w-100 col-lg-6 mb-4xl']"
zero_key = '00000000-0000-0000-0000-000000000000'

with open('version', encoding='utf8') as f:
    VERSION = f.read()

base_url = 'https://learn.innopolis.university'
instructors_url = 'https://learn.innopolis.university/Instructors/Trainings/{}/ProgressLightweight'
trainings_url = 'https://learn.innopolis.university/api/instructors/trainings'
files_url = 'https://learn.innopolis.university/Instructors/Trainings/{}/Results/Files?work={}&exercise={}&student={}'

print(f'Версия парсера {VERSION}')
print('Парсер запущен ...')

s, response = auth(LOGIN, PASSWD)

if not response.ok:
    print('Безуспешная попытка авторизации.')
    sys.exit()

print('Parsing.. Авторизация - ОК.')
print('Parsing.. Страница модулей')

# Парсим страницу "Курсы" для поиска url перехода на следующую страницу
dom = html.fromstring(response.content).xpath(f"{path}/a/@href")[0]

# Формируем url для перехода на следующую страницу
online_url = base_url + dom

# GET запрос следующей страницы
online = s.get(online_url)

# Парсим страницу "Код будущего" для поиска url перехода на следующую страницу
dom = html.fromstring(online.content).xpath(path)
href = dom[0].xpath('a/@href')[0]

# Формируем url для перехода на следующую страницу
course_url = base_url + href

# GET запрос следующей страницы
response = s.get(course_url)

print('Parsing.. Формируем карточки.')

# Парсим страницу "Онлайн" для формирования списка доступных модулей
dom = html.fromstring(response.content).xpath(path)
cards = []

# Находим все доступные модули и формируем словарь с наименованием курса и ссылкой для перехода
for card in dom:
    card_url = card.xpath("a/@href")[0]
    card_name = card.xpath(
        "a/div[@class='card border-0 bg-white h-100 shadow rounded-lg p-0']"
        "/div[@class='card-body p-4 h-100 d-flex flex-column']"
        "/div[@class='card-title text-dark mb-4 row justify-content-between no-gutters flex-nowrap']/h5/text()")[0]
    cards.append({
        card_name: base_url + card_url
    })

print(f"\nУ вас {len(dom)} модуля.")
print('=' * 50)

for i in range(len(cards)):
    print(f'{i}. {list(cards[i].keys())[0].split(" (онлайн)")[0]}')

print('=' * 50)
sel = int(input('Какой модуль использовать? _ '))

# Формируем наименование выбранного модуля и ссылку для перехода
try:
    get_card = list(cards[sel].values())[0]
    card_names = list(cards[sel].keys())[0]
except (IndexError,):
    print('Нет такого модуля.')
    sys.exit()

# Переходим на страницу выбранного модуля
response = s.get(get_card)

# Парсим страницу модуля для формирования ссылки на журнал
get_list_card_url = html.fromstring(response.content).xpath("//a[@id='training-Progress']/@href")
get_card_url = base_url + get_list_card_url[0]  # Получаем ссылку на первую карточку из списка

cards_id = [i.split("/")[3] for i in get_list_card_url]  # ID модулей
trainings = [f'{trainings_url}/{i}' for i in cards_id]  # Ссылки на модули
list_key = []  # Ключи от всех групп

for training in trainings:
    get_trainings = f'{training}/groups'

    # Переходим в журнал и получаем json объект всех преподавателей модуля
    teachers = s.get(get_trainings).json()
    # Создание файла json со списком преподавателей текущей группы
    with open(os.path.join(f'{teachers_path}', f"{card_names}.json"), 'w+', encoding="utf8") as f:
        json.dump(teachers, f, ensure_ascii=False, indent=4)

    keys = {}

    # Ищем в списке преподавателей свою фамилию и формируем словарь с id и фамилией
    for teacher in teachers:
        teach_id = list(teacher.values())

        if teach_id[1].startswith(NAME):
            keys[teach_id[1]] = teach_id[0]

    key = 0

    # Если на данном направлении несколько групп, разрешаем выбор необходимой группы
    if len(keys) > 1:
        print(f"\nУ вас {len(keys)} группы в данном модуле.")
        print('=' * 50)

        for i, item in enumerate(keys.keys()):
            print(f'{i} - {item}')

        print('=' * 50)

        sel_group = int(input('Какую группу использовать? _ '))
        try:
            key = list(keys.values())[sel_group]
            FULL_NAME = list(keys.keys())[sel_group]
        except (IndexError,):
            print('Нет такой группы.')
            sys.exit()

    # Если группа только одна
    elif len(keys) == 1:
        key = list(keys.values())[0]
        FULL_NAME = list(keys.keys())[0]

    # Если группа еще не сформирована, либо отсутствует
    else:
        print('В данной группе нет учеников.')
        sys.exit()

    list_key.append(key)  # Добавление ключа

dict_key_card = dict(zip(cards_id, list_key))  # Словарь модулей и ключей

# Создаем словарь параметров для фильтрации по фамилии, в качестве ключа передаем id преподавателя.
# Кол-во записей на странице - 50

print('\nParsing.. Ожидаем ответ от сервера.')

count_student = 0
count_homework = 0
verified = 0  # Проверенно
percent_verified = 0  # Процент проверенных
pending_verification = 0  # Ожидают проверки

# Получение словаря идентификаторов и названия модулей
d_module = {}
for i in s.get(f'https://learn.innopolis.university/api/instructors/trainings').json():
    d_module[i.get('id')] = i.get('label')

# Фильтруем страницу

themes = []
for card_id, key in dict_key_card.items():
    print(f'Получаем данные от "{d_module[card_id]}"')
    data_param = {  # Параметры для запроса
        'start': 0,
        'length': 50,
        'group': key,
        'work': '20,30'
    }
    try:
        response_2 = s.get(instructors_url.format(card_id), params={'work': '20,30'})
        dom_themes = html.fromstring(response_2.content).xpath('//th[contains(@class, "exercise")]')
        for theme in dom_themes:
            theme_title = theme.xpath('@title')[0]
            theme_number = theme.xpath('text()')[0]
            themes.append(f'{theme_number}. {theme_title.replace(" Домашнее задание", "").replace("..", ".")}')

        training = f'{trainings_url}/{card_id}'
        response = s.post(f'{training}/ProgressLightweight', params=data_param)
        seconds = response.elapsed.total_seconds()
        print(f'Parsing.. Ответ получен за {seconds} сек.')
    except ConnectionError:
        print('Вышло время ожидания.... (')

    # Создание файла журнала текущей группы в формате json
    with open(os.path.join(f'{events_path}', f"{FULL_NAME} {card_id}.json"), 'w', encoding='utf8') as f:
        json.dump(response.json(), f, ensure_ascii=False, indent=4)
    # ========================================================
    #      Парсим json и формируем журнал в формате xlsx
    # ========================================================
    print('Parsing.. Формируем журнал.\n')
    data = response.json().get('data')

    columns = [i for i in range(1, len(data[0].get('exercises')) + 1)]

    students = []
    values = []
    count_student = 0

    for student_dict in data:
        count_student += 1
        val = []
        student_id = student_dict.get('id')
        surname = student_dict.get('surname')
        firstname = student_dict.get('firstname')
        patronymic = student_dict.get('patronymic')
        student_name = f'{surname} {firstname} {patronymic}'
        students.append(student_name)

        exercises = student_dict.get('exercises')  # Получаем список с домашними заданиями ученика

        for pos, i in enumerate(exercises, 1):
            count_homework += 1
            light = i.get('light')
            match light:
                case 'text-gray':
                    val.append('')
                case 'text-green':
                    val.append(f'{i.get("average"):.2f}'.replace('.', ','))
                    verified += 1
                case 'text-red':
                    if IS_LOAD:
                        file = s.get(files_url.format(card_id, zero_key, i.get('id'), student_id))
                        with file, zipfile.ZipFile(io.BytesIO(file.content)) as archive:
                            archive.extractall(files_path)
                        print(f'{student_name}: ДЗ №{pos} загружено.')
                    val.append('?')
                    pending_verification += 1
        values.append(val)

    percent_verified = f'{(verified * 100) / count_homework:.2f}'

    modules_file_name = os.path.join(f'{xlsx_path}',
                                     f'{card_names} ({d_module[card_id]}).xlsx')  # Название файла по наименованию направления
    teacher_file_name = os.path.join(f'{xlsx_path}', f'{FULL_NAME}.xlsx')  # Название файла по преподавателю

    with pd.ExcelWriter(modules_file_name, engine='xlsxwriter') as writer:
        # В качестве заголовка можно использовать columns=columns (числовое отображение)
        df = pd.DataFrame(values, index=students, columns=columns)
        df.to_excel(writer, sheet_name='events')
        sheet = writer.sheets['events']
        cell_format = writer.book.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter',
                                              'font_name': 'Arial', 'font_size': 10})
        sheet.set_column(0, 0, 30)  # Ширина первой колонки
        sheet.set_column(1, len(themes), 4, cell_format=cell_format)  # Ширина остальных колонок
        sheet.set_row(0, 15)  # Высота первого ряда
        sheet.write_row(0, 1, df.columns, cell_format)

print('=' * 50)
print(f'Общее количество учеников - {count_student}')
print(f'Общее количество ДЗ - {count_homework}')
print(f'Количество проверенных работ - {verified} ({percent_verified}%)')
print(f'Ожидают проверки - {pending_verification}')
print('=' * 50)
print('Parsing.. Done.')
