#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест библиотеки minimalmodbus для проверки чтения пустого регистра
"""
import minimalmodbus
import serial
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IP = "192.168.4.1"
PORT = 503
UNIT_ID = 1

def test_minimalmodbus():
    """Тест minimalmodbus: читаем 1021, потом 102 (пустой), потом снова 1021"""
    print("=" * 60)
    print("Тест библиотеки: minimalmodbus")
    print("=" * 60)
    
    # minimalmodbus работает через последовательный порт, но можно использовать TCP через pyserial
    # Для TCP/IP нужно использовать специальный адаптер или обертку
    print("\n⚠️  minimalmodbus работает только с последовательными портами")
    print("   Для TCP/IP нужна обертка или другой подход")
    print("   Пропускаем этот тест")
    
    # Попробуем через TCP socket обертку
    try:
        import socket
        
        # Создаем TCP сокет
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((IP, PORT))
        
        # minimalmodbus не поддерживает TCP напрямую, поэтому используем ручную реализацию
        print("\nИспользуем ручную реализацию Modbus RTU over TCP для minimalmodbus...")
        
        def crc16_modbus(data: bytes) -> int:
            """Расчет CRC16 для Modbus RTU"""
            crc = 0xFFFF
            for byte in data:
                crc ^= byte
                for _ in range(8):
                    if crc & 0x0001:
                        crc >>= 1
                        crc ^= 0xA001
                    else:
                        crc >>= 1
            return crc
        
        def read_register(address: int) -> tuple:
            """Чтение регистра через TCP socket"""
            addr_high = (address >> 8) & 0xFF
            addr_low = address & 0xFF
            frame = bytes([UNIT_ID, 4, addr_high, addr_low, 0x00, 0x01])
            crc = crc16_modbus(frame)
            crc_low = crc & 0xFF
            crc_high = (crc >> 8) & 0xFF
            frame_with_crc = frame + bytes([crc_low, crc_high])
            
            try:
                sock.sendall(frame_with_crc)
                time.sleep(0.1)
                resp = sock.recv(256)
                
                if len(resp) < 7:
                    return (None, "Короткий ответ")
                
                # Проверяем на ошибку Modbus
                if resp[1] & 0x80:
                    error_code = resp[2] if len(resp) > 2 else 0
                    return (None, f"Modbus exception code={error_code}")
                
                if resp[0] != UNIT_ID or resp[1] != 4:
                    return (None, "Неправильный ответ")
                
                value = (resp[3] << 8) | resp[4]
                return (value, None)
            except Exception as e:
                return (None, str(e))
        
        # Читаем регистр 1021 (существующий)
        print("\n2. Чтение регистра 1021 (существующий)...")
        value, error = read_register(1021)
        if error:
            print(f"❌ Ошибка чтения: {error}")
        else:
            print(f"✅ Значение регистра 1021: {value}")
        
        time.sleep(0.5)
        
        # Читаем регистр 102 (пустой/несуществующий)
        print("\n3. Чтение регистра 102 (пустой/несуществующий)...")
        value, error = read_register(102)
        if error:
            print(f"❌ Ошибка чтения: {error}")
        else:
            print(f"✅ Значение регистра 102: {value}")
        
        time.sleep(0.5)
        
        # Снова читаем регистр 1021 (проверяем, что соединение не сломалось)
        print("\n4. Повторное чтение регистра 1021 (проверка соединения)...")
        value, error = read_register(1021)
        if error:
            print(f"❌ ОШИБКА: Соединение сломалось! {error}")
            result_ok = False
        else:
            print(f"✅ Соединение работает! Значение регистра 1021: {value}")
            result_ok = True
        
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ: minimalmodbus (ручная реализация) " + ("✅ НЕ ЛОМАЕТ" if result_ok else "❌ ЛОМАЕТ") + " соединение")
        print("=" * 60)
        
        sock.close()
        
    except Exception as e:
        print(f"❌ Исключение: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_minimalmodbus()
