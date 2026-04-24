"""
Модуль для работы с 3x-ui API
"""

import requests
import json
import random
import string
import uuid
import urllib3
from typing import Optional, Dict, List
import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class XUIClient:
    """Клиент для работы с 3x-ui API"""

    def __init__(self):
        self.base_url = config.XUI_URL
        self.username = config.XUI_USERNAME
        self.password = config.XUI_PASSWORD
        self.session = requests.Session()
        self.session.verify = False

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

    def get_all_inbounds(self) -> List[Dict]:
        """Получить все inbound'ы"""
        try:
            if not self.login():
                return []
            response = self.session.get(f"{self.base_url}/panel/api/inbounds/list")
            data = response.json()
            if not data.get("success"):
                return []
            return data.get("obj", [])
        except Exception as e:
            print(f"Ошибка получения inbounds: {e}")
            return []

    def get_clients(self) -> List[Dict]:
        """Получить статистику по всем подпискам (subId) со всех inbound'ов"""
        try:
            inbounds = self.get_all_inbounds()
            if not inbounds:
                return []

            # Группируем по subId, суммируем трафик
            subs: Dict[str, Dict] = {}

            for inbound in inbounds:
                for stat in inbound.get("clientStats", []):
                    sub_id = stat.get("subId") or stat.get("email", "")
                    if not sub_id:
                        continue

                    if sub_id not in subs:
                        subs[sub_id] = {
                            "subId": sub_id,
                            "email": stat.get("email", ""),
                            "enable": stat.get("enable", True),
                            "up": 0,
                            "down": 0,
                            "allTime": 0,
                            "total": stat.get("total", 0),
                            "expiryTime": stat.get("expiryTime", 0),
                            "inbounds": []
                        }

                    subs[sub_id]["up"] += stat.get("up", 0)
                    subs[sub_id]["down"] += stat.get("down", 0)
                    subs[sub_id]["allTime"] += stat.get("up", 0) + stat.get("down", 0)
                    subs[sub_id]["inbounds"].append(inbound.get("remark", f"inbound {inbound['id']}"))

                    # Если хоть один inbound отключён — считаем отключённым
                    if not stat.get("enable", True):
                        subs[sub_id]["enable"] = False

            return list(subs.values())
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

    def get_client_link(self, sub_id: str) -> Optional[str]:
        """Получить subscription ссылку для клиента по subId"""
        try:
            return f"{self.base_url}/sub/{sub_id}"
        except Exception as e:
            print(f"Ошибка получения ссылки: {e}")
            return None

    def get_email_by_name(self, name: str) -> Optional[str]:
        """Получить email клиента по имени (subId) — ищет по всем inbound'ам"""
        try:
            inbounds = self.get_all_inbounds()
            for inbound in inbounds:
                settings = json.loads(inbound.get("settings", "{}"))
                for client in settings.get("clients", []):
                    if client.get("subId") == name:
                        return client.get("email")
            return None
        except Exception as e:
            print(f"Ошибка поиска клиента: {e}")
            return None

    def get_client_uuid(self, name: str) -> Optional[str]:
        """Получить UUID клиента по имени (subId) — ищет по всем inbound'ам"""
        try:
            inbounds = self.get_all_inbounds()
            for inbound in inbounds:
                settings = json.loads(inbound.get("settings", "{}"))
                for client in settings.get("clients", []):
                    if client.get("subId") == name:
                        return client.get("id")
            return None
        except Exception as e:
            print(f"Ошибка получения UUID: {e}")
            return None

    def delete_client(self, identifier: str) -> bool:
        """Удалить клиента по email или subId"""
        try:
            if not self.login():
                print("Ошибка авторизации при удалении")
                return False

            url = f"{self.base_url}/panel/api/inbounds/{config.INBOUND_ID}/delClient/{identifier}"
            print(f"Удаление клиента: {url}")

            response = self.session.post(url)
            print(f"Ответ сервера: {response.text}")

            result = response.json()
            print(f"Результат: {result}")
            return result.get("success", False)
        except Exception as e:
            print(f"Ошибка удаления клиента: {e}")
            return False
