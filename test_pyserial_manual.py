#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест ручной реализации Modbus RTU over TCP (через pyserial/socket)
для проверки чтения пустого регистра
"""
import socket
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IP = "192.168.4.1"
PORT = 503
UNIT_ID = 1

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

def read_register(sock: socket.socket, address: int) -> tuple:
    """Чтение регистра через TCP socket с обработкой ошибок"""
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
        
        # Читаем ответ с таймаутом
        resp = b''
        sock.settimeout(1.0)
        try:
            # Читаем все доступные данные
            while True:
                chunk = sock.recv(256)
                if not chunk:
                    break
                resp += chunk
                # Проверяем, не закончился ли фрейм
                if len(resp) >= 5:
                    # Проверяем на Modbus exception (3 байта минимум)
                    if resp[1] & 0x80:
                        if len(resp) >= 5:  # unit_id + function + error_code + CRC(2)
                            break
                    # Проверяем на нормальный ответ
                    elif len(resp) >= 3:
                        byte_count = resp[2]
                        expected_length = 3 + byte_count + 2
                        if len(resp) >= expected_length:
                            break
        except socket.timeout:
            pass
        finally:
            sock.settimeout(2.0)
        
        if len(resp) < 5:
            return (None, "Короткий ответ")
        
        # Проверяем на ошибку Modbus
        if resp[1] & 0x80:
            error_code = resp[2] if len(resp) > 2 else 0
            error_messages = {
                1: "Illegal Function",
                2: "Illegal Data Address",
                3: "Illegal Data Value",
            }
            error_msg = error_messages.get(error_code, f"Unknown error ({error_code})")
            return (None, f"Modbus exception: {error_msg} (code={error_code})")
        
        if resp[0] != UNIT_ID or resp[1] != 4:
            return (None, "Неправильный ответ")
        
        if len(resp) < 7:
            return (None, "Недостаточно данных")
        
        value = (resp[3] << 8) | resp[4]
        
        # Проверяем CRC
        received_crc = (resp[-1] << 8) | resp[-2]
        data_for_crc = resp[:-2]
        calculated_crc = crc16_modbus(data_for_crc)
        
        if received_crc != calculated_crc:
            return (None, f"CRC не совпадает: получен {received_crc:04X}, ожидался {calculated_crc:04X}")
        
        return (value, None)
    except socket.timeout:
        return (None, "Таймаут")
    except (ConnectionError, OSError) as e:
        return (None, f"Ошибка соединения: {e}")
    except Exception as e:
        return (None, f"Ошибка: {e}")

def test_pyserial_manual():
    """Тест ручной реализации: читаем 1021, потом 102 (пустой), потом снова 1021"""
    print("=" * 60)
    print("Тест библиотеки: pyserial/socket (ручная реализация Modbus RTU)")
    print("=" * 60)
    
    sock = None
    try:
        # Подключаемся
        print(f"\n1. Подключение к {IP}:{PORT}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((IP, PORT))
        print("✅ Подключено успешно")
        
        # Читаем регистр 1021 (существующий)
        print("\n2. Чтение регистра 1021 (существующий)...")
        value, error = read_register(sock, 1021)
        if error:
            print(f"❌ Ошибка чтения: {error}")
        else:
            print(f"✅ Значение регистра 1021: {value}")
        
        time.sleep(0.5)
        
        # Читаем регистр 102 (пустой/несуществующий)
        print("\n3. Чтение регистра 102 (пустой/несуществующий)...")
        value, error = read_register(sock, 102)
        if error:
            print(f"❌ Ошибка чтения: {error}")
        else:
            print(f"✅ Значение регистра 102: {value}")
        
        time.sleep(0.5)
        
        # Снова читаем регистр 1021 (проверяем, что соединение не сломалось)
        print("\n4. Повторное чтение регистра 1021 (проверка соединения)...")
        value, error = read_register(sock, 1021)
        if error:
            print(f"❌ ОШИБКА: Соединение сломалось! {error}")
            result_ok = False
        else:
            print(f"✅ Соединение работает! Значение регистра 1021: {value}")
            result_ok = True
        
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТ: pyserial/socket (ручная реализация) " + ("✅ НЕ ЛОМАЕТ" if result_ok else "❌ ЛОМАЕТ") + " соединение")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Исключение: {e}")
        import traceback
        traceback.print_exc()
        result_ok = False
    finally:
        if sock:
            sock.close()
            print("\nСоединение закрыто")
    
    return result_ok

if __name__ == "__main__":
    test_pyserial_manual()
