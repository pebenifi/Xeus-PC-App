#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест библиотеки pymodbus для проверки чтения пустого регистра
"""
from pymodbus.client import ModbusTcpClient
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IP = "192.168.4.1"
PORT = 503
UNIT_ID = 1

def test_pymodbus():
    """Тест pymodbus: читаем 1021, потом 102 (пустой), потом снова 1021"""
    print("=" * 60)
    print("Тест библиотеки: pymodbus")
    print("=" * 60)
    
    client = ModbusTcpClient(host=IP, port=PORT, framer='rtu')
    
    try:
        # Подключаемся
        print(f"\n1. Подключение к {IP}:{PORT}...")
        if not client.connect():
            print("❌ Ошибка подключения")
            return
        print("✅ Подключено успешно")
        
        # Читаем регистр 1021 (существующий)
        print("\n2. Чтение регистра 1021 (существующий)...")
        result = client.read_input_registers(1021, 1, unit=UNIT_ID)
        if result.isError():
            print(f"❌ Ошибка чтения: {result}")
        else:
            print(f"✅ Значение регистра 1021: {result.registers[0]}")
        
        time.sleep(0.5)
        
        # Читаем регистр 102 (пустой/несуществующий)
        print("\n3. Чтение регистра 102 (пустой/несуществующий)...")
        result = client.read_input_registers(102, 1, unit=UNIT_ID)
        if result.isError():
            print(f"❌ Ошибка чтения: {result}")
        else:
            print(f"✅ Значение регистра 102: {result.registers[0]}")
        
        time.sleep(0.5)
        
        # Снова читаем регистр 1021 (проверяем, что соединение не сломалось)
        print("\n4. Повторное чтение регистра 1021 (проверка соединения)...")
        result = client.read_input_registers(1021, 1, unit=UNIT_ID)
        if result.isError():
            print(f"❌ ОШИБКА: Соединение сломалось! {result}")
        else:
            print(f"✅ Соединение работает! Значение регистра 1021: {result.registers[0]}")
        
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ: pymodbus " + ("✅ НЕ ЛОМАЕТ" if not result.isError() else "❌ ЛОМАЕТ") + " соединение")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Исключение: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("\nСоединение закрыто")

if __name__ == "__main__":
    test_pymodbus()
