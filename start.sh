#!/bin/bash
cd ~/Проекты/vpn-bot
source venv/bin/activate

# Используем только HTTP прокси, отключаем SOCKS
export http_proxy="http://127.0.0.1:2080"
export https_proxy="http://127.0.0.1:2080"
unset all_proxy
unset ALL_PROXY

python bot.py
