import requests
from lxml import html


url = 'https://learn.innopolis.university/Account/Login'
login_url = 'https://auth.lms.innopolis.university/Account/Login'
check_url = 'https://learn.innopolis.university/signin-oidc'

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
}

s = requests.Session()


def auth(login, password):
    ReturnUrl = None
    RequestVerificationToken = None
    code = None
    scope = None
    state = None
    session_state = None
    params = {'back': ''}

    # GET запрос базового url для парсинга токена формы
    response = s.get(url, params=params, headers=headers)

    # Создание DOM объекта страницы с формой входа
    dom = html.fromstring(response.content)
    user_form = dom.xpath("//div[@class='col-md-9']/form")

    # Парсим токен из формы
    for item in user_form:
        ReturnUrl = item.xpath("input[@name='ReturnUrl']/@value")[0]
        RequestVerificationToken = item.xpath("input[@name='__RequestVerificationToken']/@value")[0]

    # Формируем параметры url и данные для POST запроса авторизации
    params = {
        "ReturnUrl": ReturnUrl
    }
    data = {
        "Login": login,
        "Pass": password,
        "button": "login",
        "__RequestVerificationToken": RequestVerificationToken,
    }

    # Авторизуемся
    print('Parsing.. Страница авторизации')
    response = s.post(login_url, params=params, data=data, headers=headers)

    # Создаем объект скрытой формы, сформированной в ответе на форму авторизации, для проверки данных.
    # Парсим данные из скрытой формы для проверки и передачи необходимых параметров
    dom_2 = html.fromstring(response.content)
    sign_form = dom_2.xpath('//form')

    for item in sign_form:
        code = item.xpath("input[@name='code']/@value")[0]
        scope = item.xpath("input[@name='scope']/@value")[0]
        state = item.xpath("input[@name='state']/@value")[0]
        session_state = item.xpath("input[@name='session_state']/@value")[0]

    check_data = {
        'code': code,
        'scope': scope,
        'state': state,
        'session_state': session_state
    }

    # Проходим проверку
    check_response = s.post(check_url, data=check_data, headers=headers)

    return s, check_response
