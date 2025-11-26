#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket, time

IP   = "192.168.4.1"
PORT = 503
UNIT_ID = 1

def hex_dump(label, data: bytes):
    print(f"{label}: {' '.join(f'{b:02X}' for b in data)}")

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

def build_read_frame(function: int, address: int, unit_id: int = UNIT_ID) -> bytes:
    """Формирование Modbus RTU фрейма для чтения (функция 04)"""
    # Адрес регистра в байтах (старший и младший)
    addr_high = (address >> 8) & 0xFF
    addr_low = address & 0xFF
    
    # Количество регистров для чтения (1 регистр)
    quantity = 1
    qty_high = (quantity >> 8) & 0xFF
    qty_low = quantity & 0xFF
    
    # Формируем фрейм без CRC
    frame = bytes([unit_id, function, addr_high, addr_low, qty_high, qty_low])
    
    # Добавляем CRC16
    crc = crc16_modbus(frame)
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF
    
    return frame + bytes([crc_low, crc_high])

def build_write_frame(function: int, address: int, value: int, unit_id: int = UNIT_ID) -> bytes:
    """Формирование Modbus RTU фрейма для записи (функция 06)"""
    # Адрес регистра в байтах (старший и младший)
    addr_high = (address >> 8) & 0xFF
    addr_low = address & 0xFF
    
    # Значение для записи (2 байта)
    value_high = (value >> 8) & 0xFF
    value_low = value & 0xFF
    
    # Формируем фрейм без CRC
    frame = bytes([unit_id, function, addr_high, addr_low, value_high, value_low])
    
    # Добавляем CRC16
    crc = crc16_modbus(frame)
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF
    
    return frame + bytes([crc_low, crc_high])

def connect_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect((IP, PORT))
    return s

def parse_read_response(resp: bytes) -> dict:
    """Расшифровка ответа на запрос чтения (функция 04)"""
    if len(resp) < 5:
        return None
    
    unit_id = resp[0]
    function = resp[1]
    byte_count = resp[2]
    
    if function != 4:
        return None
    
    # Извлекаем значение регистра (2 байта)
    if byte_count >= 2 and len(resp) >= 5:
        value_high = resp[3]
        value_low = resp[4]
        value = (value_high << 8) | value_low
        
        # Проверяем CRC (последние 2 байта)
        if len(resp) >= 7:
            received_crc = (resp[-1] << 8) | resp[-2]  # CRC в little-endian
            data_for_crc = resp[:-2]  # Все кроме CRC
            calculated_crc = crc16_modbus(data_for_crc)
            
            return {
                'unit_id': unit_id,
                'function': function,
                'byte_count': byte_count,
                'value': value,
                'value_hex': f"0x{value:04X}",
                'crc_valid': received_crc == calculated_crc,
                'received_crc': f"0x{received_crc:04X}",
                'calculated_crc': f"0x{calculated_crc:04X}"
            }
    
    return None

def parse_write_response(resp: bytes) -> dict:
    """Расшифровка ответа на запрос записи (функция 06)"""
    if len(resp) < 8:
        return None
    
    unit_id = resp[0]
    function = resp[1]
    
    if function != 6:
        return None
    
    # Извлекаем адрес и значение
    addr_high = resp[2]
    addr_low = resp[3]
    address = (addr_high << 8) | addr_low
    
    value_high = resp[4]
    value_low = resp[5]
    value = (value_high << 8) | value_low
    
    # Проверяем CRC (последние 2 байта)
    if len(resp) >= 8:
        received_crc = (resp[-1] << 8) | resp[-2]  # CRC в little-endian
        data_for_crc = resp[:-2]  # Все кроме CRC
        calculated_crc = crc16_modbus(data_for_crc)
        
        return {
            'unit_id': unit_id,
            'function': function,
            'address': address,
            'value': value,
            'value_hex': f"0x{value:04X}",
            'crc_valid': received_crc == calculated_crc,
            'received_crc': f"0x{received_crc:04X}",
            'calculated_crc': f"0x{calculated_crc:04X}"
        }
    
    return None

def send_frame(sock, frame: bytes, is_write: bool = False, return_parsed: bool = False):
    """Отправка фрейма и получение ответа
    
    Args:
        sock: Сокет
        frame: Фрейм для отправки
        is_write: True если это запись, False если чтение
        return_parsed: Если True, возвращает распарсенный ответ вместо вывода
    
    Returns:
        dict или None - распарсенный ответ, если return_parsed=True
    """
    try:
        hex_dump("TX", frame)
        sock.sendall(frame)
        
        time.sleep(0.1)
        
        try:
            resp = sock.recv(256)
            if resp:
                hex_dump("RX", resp)
                
                if is_write:
                    # Расшифровываем ответ на запись
                    parsed = parse_write_response(resp)
                    if return_parsed:
                        return parsed
                    if parsed:
                        print(f"\n  Расшифровка ответа:")
                        print(f"    Unit ID: {parsed['unit_id']}")
                        print(f"    Функция: {parsed['function']:02d} (Write Single Register)")
                        print(f"    Адрес регистра: {parsed['address']}")
                        print(f"    Записанное значение: {parsed['value']} (десятичное)")
                        print(f"    Записанное значение: {parsed['value_hex']} (шестнадцатеричное)")
                        
                        # Бинарное представление
                        low_byte = parsed['value'] & 0xFF
                        high_byte = (parsed['value'] >> 8) & 0xFF
                        binary_low = format(low_byte, '08b')
                        binary_high = format(high_byte, '08b')
                        print(f"    Младший байт: {low_byte} (0x{low_byte:02X}) = {binary_low}")
                        print(f"    Старший байт: {high_byte} (0x{high_byte:02X}) = {binary_high}")
                        
                        # Проверка CRC
                        if parsed['crc_valid']:
                            print(f"    CRC: ✓ Валиден ({parsed['received_crc']})")
                        else:
                            print(f"    CRC: ✗ Ошибка! Получен {parsed['received_crc']}, ожидался {parsed['calculated_crc']}")
                    else:
                        print("  Не удалось расшифровать ответ")
                else:
                    # Расшифровываем ответ на чтение
                    parsed = parse_read_response(resp)
                    if return_parsed:
                        return parsed
                    if parsed:
                        print(f"\n  Расшифровка ответа:")
                        print(f"    Unit ID: {parsed['unit_id']}")
                        print(f"    Функция: {parsed['function']:02d} (Read Input Registers)")
                        print(f"    Количество байт данных: {parsed['byte_count']}")
                        print(f"    Значение регистра: {parsed['value']} (десятичное)")
                        print(f"    Значение регистра: {parsed['value_hex']} (шестнадцатеричное)")
                        
                        # Бинарное представление
                        low_byte = parsed['value'] & 0xFF
                        high_byte = (parsed['value'] >> 8) & 0xFF
                        binary_low = format(low_byte, '08b')
                        binary_high = format(high_byte, '08b')
                        print(f"    Младший байт: {low_byte} (0x{low_byte:02X}) = {binary_low}")
                        print(f"    Старший байт: {high_byte} (0x{high_byte:02X}) = {binary_high}")
                        
                        # Проверка CRC
                        if parsed['crc_valid']:
                            print(f"    CRC: ✓ Валиден ({parsed['received_crc']})")
                        else:
                            print(f"    CRC: ✗ Ошибка! Получен {parsed['received_crc']}, ожидался {parsed['calculated_crc']}")
                    else:
                        print("  Не удалось расшифровать ответ")
            else:
                print("RX: (empty)")
                return None
        except socket.timeout:
            print("RX: (timeout)")
            return None
    except (ConnectionError, OSError) as e:
        # Ошибки соединения (Connection reset by peer и т.д.)
        if return_parsed:
            raise  # Пробрасываем исключение, чтобы обработать его на уровне выше
        else:
            print(f"Ошибка соединения: {e}")
            return None

def main():
    print("=== Modbus RTU over TCP ===")
    print(f"Подключение к {IP}:{PORT}...")
    
    sock = None
    try:
        sock = connect_socket()
        print("✓ Подключено успешно!")
        time.sleep(0.2)  # Задержка после подключения
        
        while True:
            try:
                cmd = input("\nmodbus> ").strip()
                if not cmd:
                    continue
                
                if cmd.lower() in ['quit', 'q', 'exit']:
                    break
                
                # Парсим команду: функция адрес [реле]
                parts = cmd.split()
                if len(parts) < 2:
                    print("Использование:")
                    print("  Чтение: 04 <адрес>")
                    print("  Запись: 06 <адрес> <номер_реле>")
                    print("Примеры:")
                    print("  04 1021  - прочитать регистр 1021")
                    print("  06 1021 2  - включить реле номер 2 в регистре 1021")
                    continue
                
                function = int(parts[0])
                address = int(parts[1])
                
                if function == 4:
                    # Чтение регистра
                    frame = build_read_frame(function, address)
                    
                    # Отправляем 2 раза
                    print(f"\nОтправка запроса (функция {function:02d}, адрес {address})...")
                    for i in range(2):
                        print(f"\n--- Попытка {i+1} ---")
                        send_frame(sock, frame, is_write=False)
                        if i < 1:  # Не ждем после последней отправки
                            time.sleep(0.5)
                
                elif function == 6:
                    # Запись регистра
                    if len(parts) < 3:
                        print("Для записи укажите номер реле: 06 <адрес> <номер_реле>")
                        print("Пример: 06 1021 2")
                        continue
                    
                    relay_num = int(parts[2])
                    if relay_num < 1 or relay_num > 8:
                        print("Номер реле должен быть от 1 до 8")
                        continue
                    
                    # Сначала читаем текущее состояние (отправляем 2 раза, так как первый пакет теряется)
                    print(f"\nШаг 1: Чтение текущего состояния регистра {address}...")
                    read_frame = build_read_frame(4, address)
                    parsed = None
                    
                    # Отправляем 2 раза, берем результат из второго запроса
                    # Первая попытка может потерять пакет и разорвать соединение - это нормально
                    for i in range(2):
                        try:
                            print(f"  Попытка чтения {i+1}...")
                            parsed = send_frame(sock, read_frame, is_write=False, return_parsed=True)
                            # Если первая попытка не удалась, это нормально - продолжаем
                            if parsed or i == 1:  # Если получили ответ или это вторая попытка
                                break
                        except Exception as e:
                            # При первой попытке ошибка ожидаема - игнорируем
                            if i == 0:
                                print(f"  Первая попытка не удалась (это нормально): {e}")
                                # Переподключаемся если соединение разорвано
                                try:
                                    if sock:
                                        sock.close()
                                except:
                                    pass
                                sock = connect_socket()
                                time.sleep(0.2)
                            else:
                                # При второй попытке ошибка критична
                                raise
                        
                        if i < 1:  # Не ждем после последней отправки
                            time.sleep(0.5)
                    
                    if not parsed:
                        print("Ошибка: не удалось прочитать текущее состояние после 2 попыток")
                        continue
                    
                    current_value = parsed['value']
                    current_low_byte = current_value & 0xFF
                    
                    print(f"\n  Текущее состояние младшего байта: {current_low_byte} (0x{current_low_byte:02X}) = {format(current_low_byte, '08b')}")
                    
                    # Устанавливаем бит для реле (реле 1 = бит 0, реле 2 = бит 1, и т.д.)
                    bit_position = relay_num - 1  # Реле 1 -> бит 0, реле 2 -> бит 1
                    new_low_byte = current_low_byte | (1 << bit_position)
                    
                    # Формируем новое значение (старший байт оставляем как есть)
                    new_value = (current_value & 0xFF00) | new_low_byte
                    
                    print(f"  Включаем реле {relay_num} (бит {bit_position})")
                    print(f"  Новое значение младшего байта: {new_low_byte} (0x{new_low_byte:02X}) = {format(new_low_byte, '08b')}")
                    print(f"  Новое значение регистра: {new_value} (0x{new_value:04X})")
                    
                    # Записываем новое значение
                    print(f"\nШаг 2: Запись нового значения в регистр {address}...")
                    write_frame = build_write_frame(6, address, new_value)
                    
                    for i in range(2):
                        print(f"\n--- Попытка записи {i+1} ---")
                        send_frame(sock, write_frame, is_write=True)
                        if i < 1:
                            time.sleep(0.5)
                
                else:
                    print(f"Поддерживаются функции: 04 (чтение), 06 (запись)")
                    continue
                
            except ValueError:
                print("Ошибка: неверный формат числа")
            except KeyboardInterrupt:
                print("\nВыход...")
                break
            except Exception as e:
                print(f"Ошибка: {e}")
                # При ошибке переподключаемся
                if sock:
                    sock.close()
                sock = None
                print("Переподключение...")
                time.sleep(1)
                sock = connect_socket()
                time.sleep(0.2)
    
    finally:
        if sock:
            sock.close()
        print("\nОтключено.")

if __name__ == "__main__":
    main()