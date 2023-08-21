import base64
import json
from collections import namedtuple
from http import HTTPMethod, HTTPStatus
from pathlib import Path
from time import sleep
from typing import Dict, List, Optional, Tuple
from urllib import parse, request
from urllib.error import URLError


class Request(request.Request):
    """Request with custom methods"""

    def get_method(self) -> str:
        return self.method


class VacancyStatisticCollector:
    BASE_DIR = Path(__file__).resolve().parent
    ENV_FILE_NAME = "env.json"
    OUTPUT_FILE_NAME = "data.json"
    ENV_FILE_PATH = BASE_DIR / ENV_FILE_NAME
    OUTPUT_FILE_PATH = BASE_DIR / OUTPUT_FILE_NAME
    ENV = namedtuple(
        "Env",
        [
            "email",
            "password",
            "token_url",
            "provider_log_pass",
            "hh_vacancies",
            "partner_vacancies",
            "statistics",
        ],
    )
    REQUEST_PAUSE = 3
    ENV_DONT_EXISTS_MESSAGE = f"Удостоверьтесь, что вы создали файл {ENV_FILE_NAME}"
    ENV_WRONG_FORMAT_MESSAGE = (
        f"Удостоверьтесь в правильности формата файла {ENV_FILE_NAME}"
    )
    ENV_WRONG_NAMES_MESSAGE = (
        f"Удостоверьтесь в правильном названии аргументов файла " f"{ENV_FILE_NAME}"
    )
    SERVER_TRACKER_NOT_AVAILABLE_MESSAGE = "Сервер трекера недоступен"
    SERVER_PROVIDER_NOT_AVAILABLE_MESSAGE = "Сервер парсера недоступен"
    ERROR_PROVIDER_ACCESSES_MESSAGE = (
        "Сервис парсера по URL {url} должен возвращать ответ со статусом 200, "
        "а вернул {status}"
    )
    ERROR_MESSAGE = "Работа клиента завершилась с ошибкой"
    AUTHORIZE_TRACKER_FAILED_MESSAGE = (
        "Не удалось авторизоваться в " "трекере проверьте файл окружения"
    )

    SUCCESS_MESSAGE = "OK"

    def __init__(self):
        self.errors_reports = []

    def collect_statistics(self):
        Env, message = self.extract_env()
        if message != self.SUCCESS_MESSAGE:
            self.errors_reports.append(message)
            return self.ERROR_MESSAGE
        tracker_token, token_message = self.get_tracker_token(Env)
        provider_message = self.check_provider_authorize(Env)
        for message in (token_message, provider_message):
            if message != self.SUCCESS_MESSAGE:
                self.errors_reports.append(message)
        if self.errors_reports:
            return self.ERROR_MESSAGE
        result = dict(
            statistics=self._get_statistics(Env, tracker_token),
            partner_vacancies=self._get_partner_vacancies(Env, tracker_token),
            hh_vacancies=self._get_hh_vacancies(Env),
        )

        with open(self.OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        return "Файл data.json создан/обновлён"

    def _get_statistics(self, env_obj: ENV, token: str) -> Dict:
        url = env_obj.statistics
        request_obj = self.construct_tracker_request(url, token, HTTPMethod.GET)
        response = request.urlopen(request_obj)
        return json.loads(response.read())

    def _get_partner_vacancies(self, env_obj: ENV, token: str) -> List[Dict]:
        result = []
        url = env_obj.partner_vacancies
        while url:
            request_obj = self.construct_tracker_request(url, token, HTTPMethod.GET)
            response = request.urlopen(request_obj)
            out_json = json.loads(response.read())
            print(out_json["next"])
            result += out_json["results"]
            url = out_json["next"]
            sleep(self.REQUEST_PAUSE)
        return result

    def _get_hh_vacancies(self, env_obj: ENV) -> List[Dict]:
        result = []
        url = env_obj.hh_vacancies
        while url:
            request_obj = self.construct_provider_request(
                url, env_obj.provider_log_pass, HTTPMethod.GET
            )
            out_json = json.loads(request.urlopen(request_obj).read())
            result += out_json["results"]
            url = out_json["next"]
        return result

    @classmethod
    def extract_env(cls) -> Tuple[Optional[ENV], str]:
        if not cls.ENV_FILE_PATH.exists() or not cls.ENV_FILE_PATH.is_file():
            return None, cls.ENV_DONT_EXISTS_MESSAGE
        with open(cls.ENV_FILE_PATH, "r") as read_file:
            try:
                result = json.load(read_file)
                env_obj = cls.ENV(
                    **{
                        key: value
                        for key, value in result.items()
                        if key in cls.ENV._fields
                    }
                )
            except json.JSONDecodeError:
                return None, cls.ENV_WRONG_FORMAT_MESSAGE
            except TypeError:
                return None, cls.ENV_WRONG_NAMES_MESSAGE
        return env_obj, cls.SUCCESS_MESSAGE

    @classmethod
    def get_tracker_token(cls, env_obj: ENV) -> Tuple[Optional[str], str]:
        auth_data = parse.urlencode(
            {
                "email": env_obj.email,
                "password": env_obj.password,
                "password2": env_obj.password,
            }
        ).encode()
        auth_req = Request(
            env_obj.token_url,
            data=auth_data,
            method=HTTPMethod.POST,
        )
        try:
            auth_resp = request.urlopen(auth_req)
            raw_token = auth_resp.headers.get("Set-Cookie")
            clear_token = raw_token[: raw_token.find(";")]
        except URLError:
            return None, cls.SERVER_TRACKER_NOT_AVAILABLE_MESSAGE
        if not clear_token:
            return None, cls.AUTHORIZE_TRACKER_FAILED_MESSAGE
        return clear_token, cls.SUCCESS_MESSAGE

    @classmethod
    def check_provider_authorize(cls, env_obj: ENV) -> str:
        request_obj = cls.construct_provider_request(
            env_obj.hh_vacancies, env_obj.provider_log_pass, method=HTTPMethod.HEAD
        )
        try:
            response = request.urlopen(request_obj)
        except URLError:
            return cls.SERVER_PROVIDER_NOT_AVAILABLE_MESSAGE
        if response.status != HTTPStatus.OK:
            return cls.ERROR_PROVIDER_ACCESSES_MESSAGE.format(
                url=env_obj.hh_vacancies, status=response.status_code
            )
        return cls.SUCCESS_MESSAGE

    @staticmethod
    def construct_tracker_request(url: str, token: str, method: HTTPMethod) -> Request:
        return Request(
            url,
            headers={"User-Agent": "Analytic-Client", "Cookie": token},
            method=method,
        )

    @staticmethod
    def construct_provider_request(
        url: str, log_pass: str, method: HTTPMethod
    ) -> Request:
        return Request(
            url,
            headers={
                "User-Agent": "Analytic-Client",
                "Authorization": (
                    f"Basic {base64.b64encode(log_pass.encode()).decode()}"
                ),
            },
            method=method,
        )


if __name__ == "__main__":
    collector = VacancyStatisticCollector()
    print(collector.collect_statistics())
    if collector.errors_reports:
        print("Отчёт об ошибках:")
        [
            print(f"{i} - {error}")
            for i, error in enumerate(collector.errors_reports, start=1)
        ]
