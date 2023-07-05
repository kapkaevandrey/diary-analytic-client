import json
import sys

from cryptography.fernet import Fernet


def env_extract() -> dict:
    with open('env.json', 'r') as read_file:
        env = json.load(read_file)
        read_file.close()
        return env


def decrypt_file(file_path, key):
    try:
        cipher = Fernet(key)
        with open(file_path, 'rb') as encrypted_file:
            ciphertext = encrypted_file.read()
    except FileNotFoundError:
        print("Указанный файл не найден.")
        sys.exit(1)
    except IOError:
        print("Ошибка при чтении файла.")
        sys.exit(1)
    else:
        decrypted_content = cipher.decrypt(ciphertext)

    try:
        with open(f'{file_path}', 'wb') as decrypted_file:
            decrypted_file.write(decrypted_content)
    except IOError:
        print("Ошибка при записи файла.")
        sys.exit(1)
    except:
        print("Произошла неизвестная ошибка.")
        sys.exit(1)
    else:
        print(f"Файл {file_path} успешно расшифрован и сохранён.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Необходимо указать путь к файлу в качестве аргумента командной строки.")
        sys.exit(1)
    env = env_extract()
    key = env["key"]
    file_path = sys.argv[1]
    decrypt_file(file_path, key)
