#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для последовательной проверки всех Modbus библиотек
Проверяет: какая библиотека не ломает соединение при чтении пустого регистра
"""
import subprocess
import sys
import os
import time

def run_test(test_file: str):
    """Запуск одного теста"""
    print(f"\n{'=' * 80}")
    print(f"Запуск теста: {test_file}")
    print('=' * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Выводим результат
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        # Парсим результат из вывода
        output = result.stdout + result.stderr
        if "✅ НЕ ЛОМАЕТ" in output:
            return True
        elif "❌ ЛОМАЕТ" in output:
            return False
        else:
            # Если не нашли явный результат, считаем по коду возврата
            return result.returncode == 0
            
    except subprocess.TimeoutExpired:
        print(f"❌ Тест {test_file} превысил таймаут (30 секунд)")
        return False
    except Exception as e:
        print(f"❌ Ошибка при запуске {test_file}: {e}")
        return False

def main():
    """Запуск всех тестов"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ РАЗЛИЧНЫХ MODBUS БИБЛИОТЕК")
    print("Проверка: какая библиотека не ломает соединение при чтении пустого регистра")
    print("Тестовая последовательность:")
    print("  1. Чтение регистра 1021 (существующий)")
    print("  2. Чтение регистра 102 (пустой/несуществующий)")
    print("  3. Повторное чтение регистра 1021 (проверка соединения)")
    print("=" * 80)
    
    tests = [
        ("test_pymodbus.py", "pymodbus"),
        ("test_minimalmodbus.py", "minimalmodbus (ручная реализация)"),
        ("test_modbus_tk.py", "modbus-tk"),
        ("test_pyserial_manual.py", "pyserial/socket (ручная реализация)"),
    ]
    
    results = {}
    
    for test_file, lib_name in tests:
        if os.path.exists(test_file):
            print(f"\n\n{'#' * 80}")
            print(f"# Тестирование библиотеки: {lib_name}")
            print(f"{'#' * 80}")
            results[lib_name] = run_test(test_file)
            time.sleep(1)  # Небольшая пауза между тестами
        else:
            print(f"\n⚠️  Файл {test_file} не найден, пропускаем")
            results[lib_name] = None
    
    # Итоги
    print("\n\n" + "=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    
    for lib_name, result in results.items():
        if result is None:
            status = "⚠️  НЕ ЗАПУЩЕН"
        elif result:
            status = "✅ НЕ ЛОМАЕТ соединение"
        else:
            status = "❌ ЛОМАЕТ соединение"
        print(f"{lib_name:45s} : {status}")
    
    print("=" * 80)
    
    # Подсчет результатов
    working_libs = [name for name, res in results.items() if res is True]
    broken_libs = [name for name, res in results.items() if res is False]
    
    print(f"\n📊 Статистика:")
    print(f"   ✅ Библиотеки, которые НЕ ЛОМАЮТ соединение: {len(working_libs)}")
    if working_libs:
        for lib in working_libs:
            print(f"      - {lib}")
    print(f"   ❌ Библиотеки, которые ЛОМАЮТ соединение: {len(broken_libs)}")
    if broken_libs:
        for lib in broken_libs:
            print(f"      - {lib}")
    print("=" * 80)

if __name__ == "__main__":
    main()
