"""
Модуль для работы с 3x-ui API
"""

import requests
import json
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
                json={"username": self.username, "password": self.password}
            )
            return response.json().get("success", False)
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
            return data.get("obj", []) if data.get("success") else []
        except Exception as e:
            print(f"Ошибка получения inbounds: {e}")
            return []

    def get_clients(self) -> List[Dict]:
        """Получить статистику по всем подпискам со всех inbound'ов"""
        try:
            inbounds = self.get_all_inbounds()
            if not inbounds:
                return []

            subs: Dict[str, Dict] = {}

            for inbound in inbounds:
                for stat in inbound.get("clientStats", []):
                    sub_id = stat.get("subId") or stat.get("email", "")
                    if not sub_id:
                        continue

                    if sub_id not in subs:
                        subs[sub_id] = {
                            "subId": sub_id,
                            "enable": stat.get("enable", True),
                            "allTime": 0,
                            "total": stat.get("total", 0),
                            "inbounds": []
                        }

                    subs[sub_id]["allTime"] += stat.get("up", 0) + stat.get("down", 0)
                    subs[sub_id]["inbounds"].append(inbound.get("remark", f"inbound {inbound['id']}"))

                    if not stat.get("enable", True):
                        subs[sub_id]["enable"] = False

            return list(subs.values())
        except Exception as e:
            print(f"Ошибка получения клиентов: {e}")
            return []

    def get_client_link(self, sub_id: str) -> Optional[str]:
        """Получить subscription ссылку по subId"""
        return f"{self.base_url}/sub/{sub_id}"
