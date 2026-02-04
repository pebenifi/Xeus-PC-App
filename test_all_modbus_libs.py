#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для запуска всех тестов Modbus библиотек
"""
import subprocess
import sys
import os

def run_test(test_file: str):
    """Запуск одного теста"""
    print(f"\n{'=' * 80}")
    print(f"Запуск теста: {test_file}")
    print('=' * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=False,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"❌ Тест {test_file} превысил таймаут")
        return False
    except Exception as e:
        print(f"❌ Ошибка при запуске {test_file}: {e}")
        return False

def main():
    """Запуск всех тестов"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ РАЗЛИЧНЫХ MODBUS БИБЛИОТЕК")
    print("Проверка: какая библиотека не ломает соединение при чтении пустого регистра")
    print("=" * 80)
    
    tests = [
        "test_pymodbus.py",
        "test_minimalmodbus.py",
        "test_modbus_tk.py",
        "test_pyserial_manual.py",
    ]
    
    results = {}
    
    for test_file in tests:
        if os.path.exists(test_file):
            results[test_file] = run_test(test_file)
        else:
            print(f"⚠️  Файл {test_file} не найден, пропускаем")
            results[test_file] = None
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    for test_file, result in results.items():
        if result is None:
            status = "⚠️  НЕ ЗАПУЩЕН"
        elif result:
            status = "✅ НЕ ЛОМАЕТ соединение"
        else:
            status = "❌ ЛОМАЕТ соединение"
        print(f"{test_file:30s} : {status}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
