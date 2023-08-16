from time import sleep
from urllib import request, parse
import json
from urllib.error import URLError


def func(email, password, token_url):
    auth_data = parse.urlencode({
        "email": email,
        "password": password,
        "password2": password
    }).encode()

    auth_req = request.Request(token_url, data=auth_data, method="POST")
    clear_token = False
    try:
        auth_resp = request.urlopen(auth_req)
        dirty_token = auth_resp.headers.get('Set-Cookie')
        clear_token = dirty_token[:dirty_token.find(";")]
    except URLError:
        return "Сервер недоступен"

    if clear_token:
        result = {"statistics": {}, "hh_vacancies": [], "partner_vacancies": []}

        statistic_url = env["statistics"]
        analyst_req = request.Request(statistic_url,
                                      headers={'User-Agent': 'Analytic-Client', 'Cookie': clear_token},
                                      method="GET")
        analyst_resp = request.urlopen(analyst_req)
        out_json = json.loads(analyst_resp.read())
        result["statistics"] = out_json

        prefix_set = ("hh_vacancies", "partner_vacancies")
        for prefix in prefix_set:
            analyst_url = env[prefix]
            while analyst_url:
                sleep(3)
                analyst_req = request.Request(analyst_url,
                                              headers={'User-Agent': 'Analytic-Client', 'Cookie': clear_token},
                                              method="GET")
                analyst_resp = request.urlopen(analyst_req)
                out_json = json.loads(analyst_resp.read())
                print(out_json["next"])
                result[prefix] += out_json["results"]
                analyst_url = out_json["next"]
        with open('data.json', 'w') as f:
            json.dump(result, f)
            f.close()
            return "Файл data.json создан/обновлён"
    return "Произошла ошибка, проверте файл окружения"


def env_extract() -> dict:
    with open('env.json', 'r') as read_file:
        env = json.load(read_file)
        read_file.close()
        return env


env = env_extract()

print(func(env["email"], env["password"], env["token_url"]))
