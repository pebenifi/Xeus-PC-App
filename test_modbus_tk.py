#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест библиотеки modbus-tk для проверки чтения пустого регистра
"""
import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IP = "192.168.4.1"
PORT = 503
UNIT_ID = 1

def test_modbus_tk():
    """Тест modbus-tk: читаем 1021, потом 102 (пустой), потом снова 1021"""
    print("=" * 60)
    print("Тест библиотеки: modbus-tk")
    print("=" * 60)
    
    try:
        # Подключаемся
        print(f"\n1. Подключение к {IP}:{PORT}...")
        master = modbus_tcp.TcpMaster(host=IP, port=PORT)
        master.set_timeout(2.0)
        print("✅ Подключено успешно")
        
        # Читаем регистр 1021 (существующий)
        print("\n2. Чтение регистра 1021 (существующий)...")
        try:
            result = master.execute(UNIT_ID, cst.READ_INPUT_REGISTERS, 1021, 1)
            print(f"✅ Значение регистра 1021: {result[0]}")
        except Exception as e:
            print(f"❌ Ошибка чтения: {e}")
        
        time.sleep(0.5)
        
        # Читаем регистр 102 (пустой/несуществующий)
        print("\n3. Чтение регистра 102 (пустой/несуществующий)...")
        try:
            result = master.execute(UNIT_ID, cst.READ_INPUT_REGISTERS, 102, 1)
            print(f"✅ Значение регистра 102: {result[0]}")
        except Exception as e:
            print(f"❌ Ошибка чтения: {e}")
        
        time.sleep(0.5)
        
        # Снова читаем регистр 1021 (проверяем, что соединение не сломалось)
        print("\n4. Повторное чтение регистра 1021 (проверка соединения)...")
        try:
            result = master.execute(UNIT_ID, cst.READ_INPUT_REGISTERS, 1021, 1)
            print(f"✅ Соединение работает! Значение регистра 1021: {result[0]}")
            result_ok = True
        except Exception as e:
            print(f"❌ ОШИБКА: Соединение сломалось! {e}")
            result_ok = False
        
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ: modbus-tk " + ("✅ НЕ ЛОМАЕТ" if result_ok else "❌ ЛОМАЕТ") + " соединение")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Исключение: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            master.close()
            print("\nСоединение закрыто")
        except:
            pass

if __name__ == "__main__":
    test_modbus_tk()
