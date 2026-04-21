"""
Модуль для работы с 3x-ui API
"""

import requests
import json
import random
import string
import uuid
from typing import Optional, Dict, List
import config

class XUIClient:
    """Клиент для работы с 3x-ui API"""

    def __init__(self):
        self.base_url = config.XUI_URL
        self.username = config.XUI_USERNAME
        self.password = config.XUI_PASSWORD
        self.session = requests.Session()
        self.session.verify = False  # Отключаем проверку SSL (т.к. самоподписанный сертификат)

    def login(self) -> bool:
        """Авторизация в 3x-ui"""
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={
                    "username": self.username,
                    "password": self.password
                }
            )
            data = response.json()
            return data.get("success", False)
        except Exception as e:
            print(f"Ошибка авторизации: {e}")
            return False

    def get_clients(self) -> List[Dict]:
        """Получить список всех клиентов"""
        try:
            # Сначала авторизуемся
            if not self.login():
                return []

            # Получаем список inbounds
            response = self.session.get(f"{self.base_url}/panel/api/inbounds/list")
            data = response.json()

            if not data.get("success"):
                return []

            # Ищем наш inbound
            for inbound in data.get("obj", []):
                if inbound["id"] == config.INBOUND_ID:
                    return inbound.get("clientStats", [])

            return []
        except Exception as e:
            print(f"Ошибка получения клиентов: {e}")
            return []

    def generate_email(self) -> str:
        """Генерирует случайный email для клиента"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    def create_client(self, name: str, traffic_gb: int = 0, expiry_days: int = 0) -> Optional[Dict]:
        """
        Создать нового клиента

        Args:
            name: Имя клиента (subId)
            traffic_gb: Лимит трафика в ГБ (0 = безлимит)
            expiry_days: Срок действия в днях (0 = бессрочно)

        Returns:
            Данные созданного клиента или None при ошибке
        """
        try:
            if not self.login():
                return None

            # Генерируем данные клиента
            email = self.generate_email()

            # Вычисляем expiry time (если нужно)
            expiry_time = 0
            if expiry_days > 0:
                import time
                expiry_time = int((time.time() + expiry_days * 86400) * 1000)

            # Конвертируем ГБ в байты
            total_bytes = traffic_gb * 1024 * 1024 * 1024 if traffic_gb > 0 else 0

            # Генерируем UUID для клиента
            client_uuid = str(uuid.uuid4())

            client_data = {
                "id": config.INBOUND_ID,
                "settings": json.dumps({
                    "clients": [{
                        "id": client_uuid,
                        "email": email,
                        "enable": True,
                        "flow": "",
                        "limitIp": 0,
                        "totalGB": total_bytes,
                        "expiryTime": expiry_time,
                        "subId": name,
                        "tgId": "",
                        "reset": 0
                    }]
                })
            }

            response = self.session.post(
                f"{self.base_url}/panel/api/inbounds/addClient",
                json=client_data
            )

            result = response.json()
            if result.get("success"):
                return {
                    "email": email,
                    "subId": name,
                    "totalGB": traffic_gb,
                    "expiryDays": expiry_days
                }

            return None
        except Exception as e:
            print(f"Ошибка создания клиента: {e}")
            return None

    def get_client_link(self, email: str) -> Optional[str]:
        """Получить ссылку подключения для клиента"""
        try:
            if not self.login():
                return None

            response = self.session.get(f"{self.base_url}/panel/api/inbounds/list")
            data = response.json()

            if not data.get("success"):
                return None

            for inbound in data.get("obj", []):
                if inbound["id"] == config.INBOUND_ID:
                    settings = json.loads(inbound.get("settings", "{}"))
                    clients = settings.get("clients", [])

                    for client in clients:
                        if client.get("email") == email:
                            return f"{self.base_url}/{config.INBOUND_ID}/{email}"

            return None
        except Exception as e:
            print(f"Ошибка получения ссылки: {e}")
            return None

    def delete_client(self, email: str) -> bool:
        """Удалить клиента по email"""
        try:
            if not self.login():
                print("Ошибка авторизации при удалении")
                return False

            url = f"{self.base_url}/panel/api/inbounds/{config.INBOUND_ID}/delClient/{email}"
            print(f"Удаление клиента: {url}")

            response = self.session.post(url)
            print(f"Ответ сервера: {response.text}")

            result = response.json()
            print(f"Результат: {result}")
            return result.get("success", False)
        except Exception as e:
            print(f"Ошибка удаления клиента: {e}")
            return False
