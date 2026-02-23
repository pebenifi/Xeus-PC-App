#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import time

from modbus_client import ModbusClient

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

def build_read_multiple_registers_frame(function: int, address: int, quantity: int, unit_id: int = UNIT_ID) -> bytes:
    """Формирование Modbus RTU фрейма для чтения нескольких регистров (функция 04)"""
    # Адрес регистра в байтах (старший и младший)
    addr_high = (address >> 8) & 0xFF
    addr_low = address & 0xFF
    
    # Количество регистров для чтения
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
    
    # Проверяем на ошибку Modbus (функция с установленным битом 0x80)
    if function & 0x80:
        error_code = resp[2] if len(resp) > 2 else 0
        error_messages = {
            1: "Illegal Function",
            2: "Illegal Data Address",
            3: "Illegal Data Value",
            4: "Slave Device Failure",
            5: "Acknowledge",
            6: "Slave Device Busy",
            8: "Memory Parity Error"
        }
        error_msg = error_messages.get(error_code, f"Unknown error ({error_code})")
        
        # Проверяем CRC
        if len(resp) >= 5:
            received_crc = (resp[-1] << 8) | resp[-2]
            data_for_crc = resp[:-2]
            calculated_crc = crc16_modbus(data_for_crc)
            
            return {
                'is_error': True,
                'unit_id': unit_id,
                'function': function & 0x7F,  # Убираем бит ошибки
                'error_code': error_code,
                'error_message': error_msg,
                'crc_valid': received_crc == calculated_crc
            }
        return None
    
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

def find_modbus_frame_start(data: bytes) -> int:
    """Находит начало Modbus фрейма в данных (может быть мусор в начале)"""
    # Ищем паттерн: unit_id (обычно 01) + функция (04 для чтения, 84 для ошибки)
    for i in range(len(data) - 4):
        if data[i] == UNIT_ID and (data[i+1] == 4 or data[i+1] == 0x84):
            return i
    return 0  # Если не нашли, возвращаем 0

def parse_modbus_error(resp: bytes) -> dict:
    """Парсинг ответа с ошибкой Modbus"""
    if len(resp) < 5:
        return None
    
    unit_id = resp[0]
    function = resp[1]
    
    # Если функция с установленным битом ошибки (0x80)
    if function & 0x80:
        error_code = resp[2]
        error_messages = {
            1: "Illegal Function",
            2: "Illegal Data Address",
            3: "Illegal Data Value",
            4: "Slave Device Failure",
            5: "Acknowledge",
            6: "Slave Device Busy",
            8: "Memory Parity Error"
        }
        error_msg = error_messages.get(error_code, f"Unknown error ({error_code})")
        
        # Проверяем CRC
        if len(resp) >= 5:
            received_crc = (resp[-1] << 8) | resp[-2]
            data_for_crc = resp[:-2]
            calculated_crc = crc16_modbus(data_for_crc)
            
            return {
                'is_error': True,
                'unit_id': unit_id,
                'function': function & 0x7F,  # Убираем бит ошибки
                'error_code': error_code,
                'error_message': error_msg,
                'crc_valid': received_crc == calculated_crc
            }
    
    return None

def parse_multiple_registers_response(resp: bytes) -> dict:
    """Расшифровка ответа на запрос чтения нескольких регистров (функция 04)"""
    if len(resp) < 5:
        return None
    
    # Находим начало фрейма (может быть мусор в начале)
    start_idx = find_modbus_frame_start(resp)
    if start_idx > 0:
        print(f"⚠️  Найден мусор в начале ответа ({start_idx} байт), пропускаем...")
        resp = resp[start_idx:]
    
    if len(resp) < 5:
        return None
    
    # Сначала проверяем на ошибку
    error = parse_modbus_error(resp)
    if error:
        return error
    
    unit_id = resp[0]
    function = resp[1]
    
    if function != 4:
        return None
    
    byte_count = resp[2]
    
    # Проверяем минимальную длину ответа
    # Заголовок: 3 байта (unit_id, function, byte_count)
    # Данные: byte_count байт
    # CRC: 2 байта
    min_length = 3 + byte_count + 2
    if len(resp) < min_length:
        print(f"⚠️  Ответ обрезан: получено {len(resp)} байт, ожидалось минимум {min_length}")
        # Пробуем обработать то, что есть
        available_bytes = len(resp) - 5  # -3 для заголовка, -2 для CRC
        if available_bytes < 0:
            return None
        byte_count = min(byte_count, available_bytes)
    
    # Извлекаем все регистры
    registers = []
    for i in range(0, byte_count, 2):
        data_idx = 3 + i
        if data_idx + 1 < len(resp) - 2:  # Убеждаемся, что есть оба байта и место для CRC
            value_high = resp[data_idx]
            value_low = resp[data_idx + 1]
            value = (value_high << 8) | value_low
            registers.append(value)
    
    # Проверяем CRC (последние 2 байта)
    if len(resp) >= 5:
        received_crc = (resp[-1] << 8) | resp[-2]  # CRC в little-endian
        data_for_crc = resp[:-2]  # Все кроме CRC
        calculated_crc = crc16_modbus(data_for_crc)
        
        return {
            'unit_id': unit_id,
            'function': function,
            'byte_count': byte_count,
            'registers': registers,
            'register_count': len(registers),
            'crc_valid': received_crc == calculated_crc,
            'received_crc': f"0x{received_crc:04X}",
            'calculated_crc': f"0x{calculated_crc:04X}"
        }
    
    return None

def registers_to_float(registers: list, index: int) -> float:
    """Преобразование двух регистров (uint16) в float (IEEE 754)"""
    if index + 1 >= len(registers):
        return 0.0
    
    # Объединяем два регистра в 32-битное значение
    high = registers[index]
    low = registers[index + 1]
    combined = (high << 16) | low
    
    # Преобразуем в float
    import struct
    # Преобразуем uint32 в bytes (big-endian)
    bytes_val = struct.pack('>I', combined)
    # Преобразуем bytes в float
    float_val = struct.unpack('>f', bytes_val)[0]
    
    return float_val

def registers_to_float_ir(registers: list, index: int) -> float:
    """Преобразование двух регистров (uint16) в float (IEEE 754) с перестановкой байтов для IR режима
    
    Перестановка: первый байт со вторым, третий с четвертым
    Было: [byte1, byte2, byte3, byte4]
    Стало: [byte2, byte1, byte4, byte3]
    """
    if index + 1 >= len(registers):
        return 0.0
    
    # Получаем два регистра
    reg1 = registers[index]      # Первый регистр (high)
    reg2 = registers[index + 1]  # Второй регистр (low)
    
    # Извлекаем байты из регистров
    # reg1: [high_byte1, low_byte1]
    # reg2: [high_byte2, low_byte2]
    byte1 = (reg1 >> 8) & 0xFF  # Старший байт первого регистра
    byte2 = reg1 & 0xFF         # Младший байт первого регистра
    byte3 = (reg2 >> 8) & 0xFF  # Старший байт второго регистра
    byte4 = reg2 & 0xFF         # Младший байт второго регистра
    
    # Переставляем: первый со вторым, третий с четвертым
    # [byte2, byte1, byte4, byte3]
    swapped_bytes = bytes([byte2, byte1, byte4, byte3])
    
    # Преобразуем в float
    import struct
    float_val = struct.unpack('>f', swapped_bytes)[0]
    
    return float_val


def _decode_ir_registers(meta, data_regs):
    """
    Декодирование IR метаданных и данных.
    meta: 15 регистров (400-414), data_regs: 58 регистров (420-477).
    """
    import math
    import struct

    status = int(meta[0])

    def _float_variants_from_regs(reg1: int, reg2: int) -> dict:
        """Декодируем float из двух uint16 во всех популярных Modbus byte/word order."""
        A = (reg1 >> 8) & 0xFF
        B = reg1 & 0xFF
        C = (reg2 >> 8) & 0xFF
        D = reg2 & 0xFF
        orders = {
            "ABCD": bytes([A, B, C, D]),
            "BADC": bytes([B, A, D, C]),
            "CDAB": bytes([C, D, A, B]),
            "DCBA": bytes([D, C, B, A]),
        }
        out: dict[str, float] = {}
        for k, bb in orders.items():
            try:
                v = float(struct.unpack(">f", bb)[0])
            except Exception:
                continue
            if math.isfinite(v):
                out[k] = v
        return out

    def _float_from_regs_with_key(reg1: int, reg2: int, key: str) -> float:
        vmap = _float_variants_from_regs(reg1, reg2)
        return float(vmap.get(key, float("nan")))

    xmin_r1, xmin_r2 = int(meta[1]), int(meta[2])
    xmax_r1, xmax_r2 = int(meta[3]), int(meta[4])
    x_min_variants = _float_variants_from_regs(xmin_r1, xmin_r2)
    x_max_variants = _float_variants_from_regs(xmax_r1, xmax_r2)
    common_keys = sorted(set(x_min_variants.keys()) & set(x_max_variants.keys()))

    meta_float_key = None
    x_min = float("nan")
    x_max = float("nan")
    candidates = []
    for k in common_keys:
        xv0 = float(x_min_variants[k])
        xv1 = float(x_max_variants[k])
        if not (math.isfinite(xv0) and math.isfinite(xv1)):
            continue
        if xv1 <= xv0:
            continue
        if abs(xv0) > 1e6 or abs(xv1) > 1e6:
            continue
        rng = xv1 - xv0
        if rng <= 0 or rng > 1e6:
            continue
        score = abs(rng - 6.0) + 0.1 * abs(xv0 - 792.0) + 0.1 * abs(xv1 - 798.0)
        candidates.append((score, k, xv0, xv1))

    if candidates:
        candidates.sort(key=lambda t: t[0])
        _, meta_float_key, x_min, x_max = candidates[0]
        print(f"✓ Определен формат float: {meta_float_key}, x_min={x_min:.6f}, x_max={x_max:.6f}")
    else:
        x_min = 792.0
        x_max = 798.0
        print(f"⚠️  Не удалось определить формат, используем fallback: x_min={x_min}, x_max={x_max}")

    y_min_meta = float("nan")
    y_max_meta = float("nan")
    res_freq = float("nan")
    freq = float("nan")
    integral = float("nan")

    y_min_r1, y_min_r2 = int(meta[5]), int(meta[6])
    y_max_r1, y_max_r2 = int(meta[7]), int(meta[8])
    res_r1, res_r2 = int(meta[9]), int(meta[10])
    freq_r1, freq_r2 = int(meta[11]), int(meta[12])
    int_r1, int_r2 = int(meta[13]), int(meta[14])

    if meta_float_key:
        y_min_meta = _float_from_regs_with_key(y_min_r1, y_min_r2, meta_float_key)
        y_max_meta = _float_from_regs_with_key(y_max_r1, y_max_r2, meta_float_key)
        res_freq = _float_from_regs_with_key(res_r1, res_r2, meta_float_key)
        freq = _float_from_regs_with_key(freq_r1, freq_r2, meta_float_key)
        integral = _float_from_regs_with_key(int_r1, int_r2, meta_float_key)

        def _pick_any_in_range(reg1: int, reg2: int, lo: float, hi: float) -> float:
            vmap = _float_variants_from_regs(reg1, reg2)
            in_range = [v for v in vmap.values() if lo <= v <= hi]
            if not in_range:
                return float("nan")
            mid = (lo + hi) / 2.0
            in_range.sort(key=lambda v: abs(v - mid))
            return float(in_range[0])

        if not (math.isfinite(res_freq) and x_min <= res_freq <= x_max):
            rf2 = _pick_any_in_range(res_r1, res_r2, x_min, x_max)
            if math.isfinite(rf2):
                res_freq = rf2
        if not (math.isfinite(freq) and x_min <= freq <= x_max):
            f2 = _pick_any_in_range(freq_r1, freq_r2, x_min, x_max)
            if math.isfinite(f2):
                freq = f2
    else:
        y_min_meta = registers_to_float_ir(meta, 5)
        y_max_meta = registers_to_float_ir(meta, 7)

        def _pick_variant_in_range(variants: dict, lo: float, hi: float) -> float:
            if not variants:
                return float("nan")
            in_range = [(k, v) for k, v in variants.items() if lo <= v <= hi]
            if not in_range:
                return float("nan")
            mid = (lo + hi) / 2.0
            in_range.sort(key=lambda kv: abs(kv[1] - mid))
            return float(in_range[0][1])

        res_variants = _float_variants_from_regs(res_r1, res_r2)
        freq_variants = _float_variants_from_regs(freq_r1, freq_r2)
        res_freq = _pick_variant_in_range(res_variants, x_min, x_max)
        freq = _pick_variant_in_range(freq_variants, x_min, x_max)
        if not math.isfinite(res_freq):
            res_freq = registers_to_float_ir(meta, 9)
        if not math.isfinite(freq):
            freq = registers_to_float_ir(meta, 11)
        integral = registers_to_float_ir(meta, 13)

    y_min = float(y_min_meta) if math.isfinite(y_min_meta) else 0.0
    y_max = float(y_max_meta) if math.isfinite(y_max_meta) else 1.0

    y_values_raw_u16 = [int(v) for v in data_regs[:58]]
    if not y_values_raw_u16:
        print("⚠️  Предупреждение: y_values пустые")

    # Шаг 1: Преобразуем uint16 в float (умножаем на 100, делим на 65535)
    points_float = [float(v) * 100.0 / 65535.0 for v in y_values_raw_u16]
    n = len(points_float)
    n_avg = int(n * 0.2)
    if n_avg == 0:
        n_avg = 1

    m = 0.0
    for i in range(n_avg):
        m += points_float[i]
    m /= float(n_avg)

    print(f"  Baseline correction: n={n}, n_avg={n_avg}, baseline={m:.6f}")

    max_val = 0.0
    imax = 0
    for i in range(n):
        f = points_float[i] - m
        points_float[i] = f
        if f > max_val:
            max_val = f
            imax = i

    # На устройстве значения от -40 до 60, у нас после baseline correction примерно -0.1 до 0.13
    scale_factor = 460.0  # Подбираем для получения диапазона -40 до 60
    y_values = [v * scale_factor for v in points_float]
    max_scaled = max_val * scale_factor

    print(f"  After baseline correction: max={max_val:.6f} at index={imax}")
    print(f"  After scaling (factor={scale_factor}): max={max_scaled:.6f}, range=[{min(y_values):.6f}, {max(y_values):.6f}]")

    y_values_raw_i16 = y_values_raw_u16

    if y_values:
        y_min = float(min(y_values))
        y_max = float(max(y_values))

    points = []
    if len(y_values) >= 2 and x_max != x_min:
        step = (x_max - x_min) / float(len(y_values) - 1)
        for i, y in enumerate(y_values):
            points.append({"x": x_min + step * i, "y": float(y)})
    else:
        for i, y in enumerate(y_values):
            points.append({"x": float(i), "y": float(y)})

    print(f"\n✓ IR спектр декодирован:")
    print(f"  Статус: {status}")
    print(f"  X диапазон: [{x_min:.6f}, {x_max:.6f}]")
    print(f"  Y диапазон: [{y_min:.6f}, {y_max:.6f}]")
    print(f"  Res freq: {res_freq:.6f}")
    print(f"  Freq: {freq:.6f}")
    print(f"  Integral: {integral:.6f}")
    print(f"  Точек: {len(points)}")
    print(f"  Raw u16 диапазон: [{min(y_values_raw_u16) if y_values_raw_u16 else 'n/a'}, {max(y_values_raw_u16) if y_values_raw_u16 else 'n/a'}]")
    print(f"  Raw i16 диапазон: [{min(y_values_raw_i16) if y_values_raw_i16 else 'n/a'}, {max(y_values_raw_i16) if y_values_raw_i16 else 'n/a'}]")
    print(f"  Scaled y диапазон: [{y_min:.6f}, {y_max:.6f}]")
    print(f"  Первые 10 значений данных: {y_values[:10]}")
    print(f"  Последние 10 значений данных: {y_values[-10:]}")
    print(f"\n  Все 58 значений Y (после baseline correction):")
    for i, y_val in enumerate(y_values):
        print(f"    [{i:2d}] = {y_val:.6f}")
    print()

    return {
        "status": status,
        "x_min": float(x_min),
        "x_max": float(x_max),
        "y_min": float(y_min),
        "y_max": float(y_max),
        "res_freq": float(res_freq),
        "freq": float(freq),
        "integral": float(integral),
        "meta_float_key": meta_float_key,
        "data_raw_u16": y_values_raw_u16,
        "data_raw_i16": y_values_raw_i16,
        "data": y_values,
        "points": points,
    }


def read_ir_data_direct():
    """
    Чтение IR данных через ModbusClient (без сокетов в test_modbus).
    Регистры 400-414 (метаданные), 420-477 (данные).
    """
    print(f"\n=== Чтение IR данных (ModbusClient) ===")

    client = ModbusClient(host=IP, port=PORT, unit_id=UNIT_ID)
    if not client.connect():
        print("❌ Ошибка подключения к устройству")
        return None

    try:
        meta = client.read_input_registers_direct(400, 15, max_chunk=15)
        if not meta or len(meta) < 15:
            print(f"❌ Ошибка чтения метаданных: получено {len(meta) if meta else 0} регистров вместо 15")
            return None

        # Читаем все 58 регистров одним запросом (как сокет) — чанки по 10 дают нули для индексов 10-57
        data_regs = client.read_input_registers_direct(420, 58, max_chunk=58)
        if not data_regs or len(data_regs) < 58:
            print(f"❌ Ошибка чтения данных: получено {len(data_regs) if data_regs else 0} регистров вместо 58")
            return None

        print(f"Метаданные [0..4]: {meta[0:5]} (hex: {[hex(int(x)) for x in meta[0:5]]})")
        print(f"Данные первые 10: {data_regs[0:10]}, последние 3: {data_regs[-3:]}")

        return _decode_ir_registers(meta, data_regs)
    finally:
        client.disconnect()


def read_ir_data(sock):
    """
    Чтение IR данных через сокет (legacy).
    Регистры 400-414 (метаданные), 420-477 (данные).
    """
    print(f"\n=== Чтение IR данных (сокет) ===")
    
    # Варианты для проверки (если первый не сработает)
    address_variants = [400, 399, 0]  # 400, 399 (0-based), 0 (относительная адресация)
    
    # Читаем регистры частями
    # Согласно описанию:
    # - 400-414: метаданные (15 регистров)
    # - 420-477: данные (58 регистров)
    # Между 414 и 420 есть пропуск!
    read_ranges = [
        (0, 15),      # 0-14 (15 регистров) - метаданные (400-414)
        (20, 58),     # 20-77 (58 регистров) - данные (420-477)
    ]
    
    # Пробуем первый вариант адресации
    address_base = address_variants[0]
    print(f"Попытка чтения с базовым адресом {address_base}...")
    
    # Словарь для хранения прочитанных регистров по их реальным адресам
    registers_dict = {}
    
    for start_offset, quantity in read_ranges:
        start_addr = address_base + start_offset
        print(f"Чтение регистров {start_addr}-{start_addr + quantity - 1} ({quantity} регистров)...")
        
        frame = build_read_multiple_registers_frame(4, start_addr, quantity)
        
        try:
            hex_dump("TX", frame)
            sock.sendall(frame)
            
            time.sleep(0.1)
            
            # Читаем ответ с таймаутом
            resp = b''
            try:
                # Читаем все доступные данные
                sock.settimeout(0.5)
                while True:
                    chunk = sock.recv(512)
                    if not chunk:
                        break
                    resp += chunk
                    # Если получили достаточно данных, проверяем, не закончился ли фрейм
                    if len(resp) >= 5:
                        # Проверяем, есть ли полный фрейм
                        start_idx = find_modbus_frame_start(resp)
                        if start_idx >= 0:
                            frame_start = resp[start_idx:]
                            if len(frame_start) >= 3:
                                byte_count = frame_start[2]
                                expected_length = 3 + byte_count + 2
                                if len(frame_start) >= expected_length:
                                    # Полный фрейм получен
                                    break
            except socket.timeout:
                pass  # Таймаут - возможно, все данные уже получены
            finally:
                sock.settimeout(2.0)  # Возвращаем обычный таймаут
            
            if resp:
                hex_dump("RX", resp)
                
                parsed = parse_multiple_registers_response(resp)
                if not parsed:
                    print("Ошибка: не удалось распарсить ответ")
                    print(f"   Длина ответа: {len(resp)} байт")
                    start_idx = find_modbus_frame_start(resp)
                    if start_idx >= 0 and start_idx < len(resp):
                        print(f"   Начало фрейма на позиции: {start_idx}")
                        if len(resp) > start_idx + 2:
                            print(f"   Unit ID: {resp[start_idx]:02X}, Function: {resp[start_idx+1]:02X}, Byte count: {resp[start_idx+2]}")
                            byte_count = resp[start_idx+2]
                            expected_length = start_idx + 3 + byte_count + 2
                            print(f"   Ожидаемая длина: {expected_length} байт, получено: {len(resp)} байт")
                    return None
                
                # Проверяем на ошибку Modbus
                if parsed.get('is_error'):
                    error_msg = parsed['error_message']
                    error_code = parsed['error_code']
                    print(f"❌ Ошибка Modbus: {error_msg} (код {error_code})")
                    print(f"   Функция: {parsed['function']:02d}")
                    print(f"   Адрес: {start_addr}")
                    
                    # Если это ошибка адреса, пробуем другие варианты
                    if error_code == 2 and address_base == address_variants[0]:
                        print(f"\n⚠️  Пробуем альтернативный адрес...")
                        # Пробуем адрес 399 (0-based адресация)
                        address_base = address_variants[1]
                        print(f"Повторная попытка с базовым адресом {address_base}...")
                        registers_dict = {}  # Сбрасываем накопленные данные
                        # Перезапускаем цикл с новым адресом
                        for retry_offset, retry_quantity in read_ranges:
                            retry_addr = address_base + retry_offset
                            print(f"Чтение регистров {retry_addr}-{retry_addr + retry_quantity - 1} ({retry_quantity} регистров)...")
                            retry_frame = build_read_multiple_registers_frame(4, retry_addr, retry_quantity)
                            hex_dump("TX", retry_frame)
                            sock.sendall(retry_frame)
                            time.sleep(0.1)
                            retry_resp = sock.recv(512)
                            if retry_resp:
                                hex_dump("RX", retry_resp)
                                retry_parsed = parse_multiple_registers_response(retry_resp)
                                if retry_parsed and not retry_parsed.get('is_error'):
                                    retry_registers = retry_parsed.get('registers', [])
                                    # Сохраняем регистры в словарь по их реальным адресам
                                    for j, reg_value in enumerate(retry_registers):
                                        real_addr = retry_addr + j
                                        registers_dict[real_addr] = reg_value
                                    print(f"✓ Прочитано {len(retry_registers)} регистров")
                                else:
                                    print(f"❌ Ошибка при чтении регистров {retry_addr}")
                                    return None
                        break  # Выходим из основного цикла, так как уже прочитали все
                    else:
                        return None
                
                if not parsed.get('crc_valid', True):
                    print(f"⚠️  Предупреждение: CRC не валиден!")
                
                registers = parsed.get('registers', [])
                if len(registers) < quantity:
                    print(f"⚠️  Предупреждение: получено только {len(registers)} регистров вместо {quantity}")
                    return None
                
                # Сохраняем регистры в словарь по их реальным адресам
                for i, reg_value in enumerate(registers):
                    real_addr = start_addr + i
                    registers_dict[real_addr] = reg_value
                
                print(f"✓ Прочитано {len(registers)} регистров")
                
            else:
                print("RX: (empty)")
                return None
        except socket.timeout:
            print("RX: (timeout)")
            return None
        except (ConnectionError, OSError) as e:
            print(f"Ошибка соединения: {e}")
            return None
    
    # Проверяем, что получили все необходимые регистры
    # Нужно: 15 регистров (400-414) + 58 регистров (420-477) = 73 регистра
    expected_count = 15 + 58  # 73 регистра
    if len(registers_dict) < expected_count:
        print(f"❌ Ошибка: получено только {len(registers_dict)} регистров вместо {expected_count}")
        return None
    
    # Создаем полный массив с пропуском между 414 и 420
    # Индексы: 0-14 (400-414), затем пропуск 15-19, затем 20-77 (420-477)
    full_registers = [0] * 78  # 400-477 включительно = 78 регистров
    # Заполняем первые 15 регистров (400-414)
    for i in range(400, 415):
        if i in registers_dict:
            full_registers[i - 400] = registers_dict[i]
    # Заполняем регистры 420-477 (индексы 20-77 в полном массиве)
    for i in range(420, 478):
        if i in registers_dict:
            full_registers[i - 400] = registers_dict[i]
    
    # Используем full_registers
    all_registers = full_registers
    
    meta = all_registers[0:15]  # Метаданные (400-414)
    data_regs = all_registers[20:78]  # Данные (420-477)
    
    return _decode_ir_registers(meta, data_regs)


def read_ir_data_int(sock):
    """
    Чтение IR данных как int значений (использует те же регистры, что и read_ir_data):
    - Регистры 400-414: метаданные (15 регистров)
    - Регистры 420-477: данные (58 регистров)
    
    Отличие от read_ir_data: данные преобразуются в int16 напрямую, без деления на 100.0
    """
    import math
    import struct
    
    print(f"\n=== Чтение IR данных как int (регистры 400-414, 420-477) ===")
    
    # Варианты для проверки (если первый не сработает)
    address_variants = [400, 399, 0]  # 400, 399 (0-based), 0 (относительная адресация)
    
    # Читаем регистры частями (те же, что и в read_ir_data)
    read_ranges = [
        (0, 15),      # 0-14 (15 регистров) - метаданные (400-414)
        (20, 58),     # 20-77 (58 регистров) - данные (420-477)
    ]
    
    # Пробуем первый вариант адресации
    address_base = address_variants[0]
    print(f"Попытка чтения с базовым адресом {address_base}...")
    
    # Словарь для хранения прочитанных регистров по их реальным адресам
    registers_dict = {}
    
    for start_offset, quantity in read_ranges:
        start_addr = address_base + start_offset
        print(f"Чтение регистров {start_addr}-{start_addr + quantity - 1} ({quantity} регистров)...")
        
        frame = build_read_multiple_registers_frame(4, start_addr, quantity)
        
        try:
            hex_dump("TX", frame)
            sock.sendall(frame)
            
            time.sleep(0.1)
            
            # Читаем ответ с таймаутом
            resp = b''
            try:
                sock.settimeout(0.5)
                while True:
                    chunk = sock.recv(512)
                    if not chunk:
                        break
                    resp += chunk
                    if len(resp) >= 5:
                        start_idx = find_modbus_frame_start(resp)
                        if start_idx >= 0:
                            frame_start = resp[start_idx:]
                            if len(frame_start) >= 3:
                                byte_count = frame_start[2]
                                expected_length = 3 + byte_count + 2
                                if len(frame_start) >= expected_length:
                                    break
            except socket.timeout:
                pass
            finally:
                sock.settimeout(2.0)
            
            if resp:
                hex_dump("RX", resp)
                
                parsed = parse_multiple_registers_response(resp)
                if not parsed:
                    print("Ошибка: не удалось распарсить ответ")
                    return None
                
                # Проверяем на ошибку Modbus
                if parsed.get('is_error'):
                    error_msg = parsed['error_message']
                    error_code = parsed['error_code']
                    print(f"❌ Ошибка Modbus: {error_msg} (код {error_code})")
                    print(f"   Функция: {parsed['function']:02d}")
                    print(f"   Адрес: {start_addr}")
                    
                    # Если это ошибка адреса, пробуем другие варианты
                    if error_code == 2 and address_base == address_variants[0]:
                        print(f"\n⚠️  Пробуем альтернативный адрес...")
                        address_base = address_variants[1]
                        print(f"Повторная попытка с базовым адресом {address_base}...")
                        registers_dict = {}
                        for retry_offset, retry_quantity in read_ranges:
                            retry_addr = address_base + retry_offset
                            print(f"Чтение регистров {retry_addr}-{retry_addr + retry_quantity - 1} ({retry_quantity} регистров)...")
                            retry_frame = build_read_multiple_registers_frame(4, retry_addr, retry_quantity)
                            hex_dump("TX", retry_frame)
                            sock.sendall(retry_frame)
                            time.sleep(0.1)
                            retry_resp = sock.recv(512)
                            if retry_resp:
                                hex_dump("RX", retry_resp)
                                retry_parsed = parse_multiple_registers_response(retry_resp)
                                if retry_parsed and not retry_parsed.get('is_error'):
                                    retry_registers = retry_parsed.get('registers', [])
                                    for j, reg_value in enumerate(retry_registers):
                                        real_addr = retry_addr + j
                                        registers_dict[real_addr] = reg_value
                                    print(f"✓ Прочитано {len(retry_registers)} регистров")
                                else:
                                    print(f"❌ Ошибка при чтении регистров {retry_addr}")
                                    return None
                        break
                    else:
                        return None
                
                if not parsed.get('crc_valid', True):
                    print(f"⚠️  Предупреждение: CRC не валиден!")
                
                registers = parsed.get('registers', [])
                if len(registers) < quantity:
                    print(f"⚠️  Предупреждение: получено только {len(registers)} регистров вместо {quantity}")
                    return None
                
                # Сохраняем регистры в словарь по их реальным адресам
                for i, reg_value in enumerate(registers):
                    real_addr = start_addr + i
                    registers_dict[real_addr] = reg_value
                
                print(f"✓ Прочитано {len(registers)} регистров")
                
            else:
                print("RX: (empty)")
                return None
        except socket.timeout:
            print("RX: (timeout)")
            return None
        except (ConnectionError, OSError) as e:
            print(f"Ошибка соединения: {e}")
            return None
    
    # Проверяем, что получили все необходимые регистры
    expected_count = 15 + 58  # 73 регистра
    if len(registers_dict) < expected_count:
        print(f"❌ Ошибка: получено только {len(registers_dict)} регистров вместо {expected_count}")
        return None
    
    # Создаем полный массив с пропуском между 414 и 420
    full_registers = [0] * 78  # 400-477 включительно = 78 регистров
    for i in range(400, 415):
        if i in registers_dict:
            full_registers[i - 400] = registers_dict[i]
    for i in range(420, 478):
        if i in registers_dict:
            full_registers[i - 400] = registers_dict[i]
    
    all_registers = full_registers
    meta = all_registers[0:15]  # Метаданные (400-414)
    data_regs = all_registers[20:78]  # Данные (420-477)
    
    print(f"Метаданные [0..4]: {meta[0:5]} (hex: {[hex(int(x)) for x in meta[0:5]]})")
    print(f"Данные первые 10: {data_regs[0:10]}, последние 3: {data_regs[-3:]}")
    
    status = int(meta[0])
    
    # Преобразуем данные из uint16 в int16 (two's complement) БЕЗ деления на 100.0
    def _to_int16(u16: int) -> int:
        return u16 - 65536 if u16 >= 32768 else u16
    
    int_values = [_to_int16(int(v)) for v in data_regs[:58]]
    
    print(f"\n✓ IR данные прочитаны как int:")
    print(f"  Статус: {status}")
    print(f"  Всего значений данных: {len(int_values)}")
    print(f"  Диапазон значений: [{min(int_values)}, {max(int_values)}]")
    print(f"  Первые 10 значений: {int_values[:10]}")
    print(f"  Последние 10 значений: {int_values[-10:]}")
    print(f"\n  Все {len(int_values)} значений int (регистры 420-477):")
    for i, val in enumerate(int_values):
        addr = 420 + i
        print(f"    Регистр {addr:4d} [{i:2d}]: {val:6d}")
    print()
    
    return {
        "status": status,
        "start_address": 420,
        "end_address": 477,
        "total_registers": len(int_values),
        "values": int_values,
        "min_value": min(int_values),
        "max_value": max(int_values),
    }

def read_nmr_data(sock):
    """Чтение всех NMR данных за один раз
    
    Читает регистры:
    - 100: samples
    - 101-102: x_min (float)
    - 103-104: x_max (float)
    - 105-106: y_min (float)
    - 107-108: y_max (float)
    - 109-110: freq (float)
    - 111-112: ampl (float)
    - 113-114: int (float)
    - 115-116: t2 (float)
    - 120-375: data (ushort) - 256 регистров
    
    Всего: 100-116 (17 регистров) + 120-375 (256 регистров) = 273 регистра
    """
    import math
    import struct
    
    print(f"\n=== Чтение NMR данных ===")
    
    # Варианты для проверки (если первый не сработает)
    address_variants = [100, 99, 0]  # 100, 99 (0-based), 0 (относительная адресация)
    
    # Читаем регистры частями
    # Согласно описанию:
    # - 100-116: метаданные (17 регистров)
    # - 120-375: данные (256 регистров)
    # Между 116 и 120 есть пропуск (регистры 117-119 не существуют)!
    # Разбиваем на части по 30 регистров для надежности (максимум обычно 125, но устройство может ограничивать)
    read_ranges = [
        (0, 17),      # 0-16 (17 регистров) - метаданные (100-116)
        (20, 30),     # 20-49 (30 регистров) - первая часть данных (120-149)
        (50, 30),     # 50-79 (30 регистров) - вторая часть данных (150-179)
        (80, 30),     # 80-109 (30 регистров) - третья часть данных (180-209)
        (110, 30),    # 110-139 (30 регистров) - четвертая часть данных (210-239)
        (140, 30),    # 140-169 (30 регистров) - пятая часть данных (240-269)
        (170, 30),    # 170-199 (30 регистров) - шестая часть данных (270-299)
        (200, 30),    # 200-229 (30 регистров) - седьмая часть данных (300-329)
        (230, 30),    # 230-259 (30 регистров) - восьмая часть данных (330-359)
        (260, 16),    # 260-275 (16 регистров) - последняя часть данных (360-375)
    ]
    
    # Пробуем первый вариант адресации
    address_base = address_variants[0]
    print(f"Попытка чтения с базовым адресом {address_base}...")
    
    # Словарь для хранения прочитанных регистров по их реальным адресам
    registers_dict = {}
    
    for start_offset, quantity in read_ranges:
        start_addr = address_base + start_offset
        print(f"Чтение регистров {start_addr}-{start_addr + quantity - 1} ({quantity} регистров)...")
        
        frame = build_read_multiple_registers_frame(4, start_addr, quantity)
        
        try:
            hex_dump("TX", frame)
            sock.sendall(frame)
            
            time.sleep(0.1)
            
            # Читаем ответ с таймаутом, собирая все данные
            resp = b''
            try:
                sock.settimeout(0.5)
                while True:
                    chunk = sock.recv(512)
                    if not chunk:
                        break
                    resp += chunk
                    # Если получили достаточно данных, проверяем, не закончился ли фрейм
                    if len(resp) >= 5:
                        start_idx = find_modbus_frame_start(resp)
                        if start_idx >= 0:
                            frame_start = resp[start_idx:]
                            if len(frame_start) >= 3:
                                byte_count = frame_start[2]
                                expected_length = 3 + byte_count + 2
                                if len(frame_start) >= expected_length:
                                    # Полный фрейм получен
                                    break
            except socket.timeout:
                pass  # Таймаут - возможно, все данные уже получены
            finally:
                sock.settimeout(2.0)  # Возвращаем обычный таймаут
            
            if resp:
                hex_dump("RX", resp)
                
                parsed = parse_multiple_registers_response(resp)
                if not parsed:
                    print("Ошибка: не удалось распарсить ответ")
                    print(f"   Длина ответа: {len(resp)} байт")
                    start_idx = find_modbus_frame_start(resp)
                    if start_idx >= 0 and start_idx < len(resp):
                        print(f"   Начало фрейма на позиции: {start_idx}")
                        if len(resp) > start_idx + 2:
                            print(f"   Unit ID: {resp[start_idx]:02X}, Function: {resp[start_idx+1]:02X}, Byte count: {resp[start_idx+2]}")
                            byte_count = resp[start_idx+2]
                            expected_length = start_idx + 3 + byte_count + 2
                            print(f"   Ожидаемая длина: {expected_length} байт, получено: {len(resp)} байт")
                    return None
                
                # Проверяем на ошибку Modbus
                if parsed.get('is_error'):
                    error_msg = parsed['error_message']
                    error_code = parsed['error_code']
                    print(f"❌ Ошибка Modbus: {error_msg} (код {error_code})")
                    print(f"   Функция: {parsed['function']:02d}")
                    print(f"   Адрес: {start_addr}")
                    
                    # Если это ошибка для регистров данных (120+), пропускаем их
                    if start_addr >= 120 and (error_code == 2 or error_code == 3):
                        print(f"⚠️  Регистры {start_addr}-{start_addr + quantity - 1} недоступны, пропускаем...")
                        # Продолжаем чтение следующих диапазонов
                        continue
                    
                    # Если это ошибка адреса для метаданных, пробуем другие варианты
                    if error_code == 2 and address_base == address_variants[0] and start_addr < 120:
                        print(f"\n⚠️  Пробуем альтернативный адрес...")
                        # Пробуем адрес 99 (0-based адресация)
                        address_base = address_variants[1]
                        print(f"Повторная попытка с базовым адресом {address_base}...")
                        registers_dict = {}  # Сбрасываем накопленные данные
                        # Перезапускаем цикл с новым адресом
                        for retry_offset, retry_quantity in read_ranges:
                            retry_addr = address_base + retry_offset
                            print(f"Чтение регистров {retry_addr}-{retry_addr + retry_quantity - 1} ({retry_quantity} регистров)...")
                            retry_frame = build_read_multiple_registers_frame(4, retry_addr, retry_quantity)
                            hex_dump("TX", retry_frame)
                            sock.sendall(retry_frame)
                            time.sleep(0.1)
                            retry_resp = sock.recv(512)
                            if retry_resp:
                                hex_dump("RX", retry_resp)
                                retry_parsed = parse_multiple_registers_response(retry_resp)
                                if retry_parsed and not retry_parsed.get('is_error'):
                                    retry_registers = retry_parsed.get('registers', [])
                                    # Сохраняем регистры в словарь по их реальным адресам
                                    for j, reg_value in enumerate(retry_registers):
                                        real_addr = retry_addr + j
                                        registers_dict[real_addr] = reg_value
                                    print(f"✓ Прочитано {len(retry_registers)} регистров")
                                else:
                                    # Если это регистры данных (120+), пропускаем
                                    if retry_addr >= 120:
                                        print(f"⚠️  Регистры {retry_addr} недоступны, пропускаем...")
                                        continue
                                    print(f"❌ Ошибка при чтении регистров {retry_addr}")
                                    return None
                        break  # Выходим из основного цикла, так как уже прочитали все
                    elif start_addr < 120:
                        # Ошибка для метаданных - критично
                        return None
                    else:
                        # Для регистров данных просто пропускаем
                        continue
                
                if not parsed.get('crc_valid', True):
                    print(f"⚠️  Предупреждение: CRC не валиден!")
                
                registers = parsed.get('registers', [])
                if len(registers) < quantity:
                    print(f"⚠️  Предупреждение: получено только {len(registers)} регистров вместо {quantity}")
                    return None
                
                # Сохраняем регистры в словарь по их реальным адресам
                for i, reg_value in enumerate(registers):
                    real_addr = start_addr + i
                    registers_dict[real_addr] = reg_value
                
                print(f"✓ Прочитано {len(registers)} регистров")
                
            else:
                print("RX: (empty)")
                return None
        except socket.timeout:
            print("RX: (timeout)")
            return None
        except (ConnectionError, OSError) as e:
            print(f"Ошибка соединения: {e}")
            return None
    
    # Проверяем, что получили метаданные (обязательно)
    if len([k for k in registers_dict.keys() if 100 <= k <= 116]) < 17:
        print(f"❌ Ошибка: не удалось прочитать метаданные (регистры 100-116)")
        return None
    
    # Проверяем данные (могут быть недоступны)
    data_registers = [k for k in registers_dict.keys() if 120 <= k <= 375]
    if len(data_registers) == 0:
        print(f"⚠️  Предупреждение: регистры данных (120-375) недоступны")
        print(f"   Будут возвращены только метаданные")
    else:
        print(f"✓ Прочитано {len(data_registers)} регистров данных из 256")
    
    # Создаем полный массив с пропуском между 116 и 120
    # Индексы: 0-16 (100-116), затем пропуск 17-19, затем 20-275 (120-375)
    full_registers = [0] * 276  # 100-375 включительно = 276 регистров
    # Заполняем первые 17 регистров (100-116) - обязательно должны быть
    for i in range(100, 117):
        if i in registers_dict:
            full_registers[i - 100] = registers_dict[i]
        else:
            print(f"⚠️  Предупреждение: регистр {i} не прочитан")
    # Заполняем регистры 120-375 (индексы 20-275 в полном массиве) - могут отсутствовать
    for i in range(120, 376):
        if i in registers_dict:
            full_registers[i - 100] = registers_dict[i]
    
    # Используем full_registers
    all_registers = full_registers
    meta = all_registers[0:17]  # Метаданные (100-116)
    data_regs = all_registers[20:276]  # Данные (120-375)
    
    print(f"Метаданные [0..4]: {meta[0:5]} (hex: {[hex(int(x)) for x in meta[0:5]]})")
    print(f"Данные первые 10: {data_regs[0:10]}, последние 3: {data_regs[-3:]}")
    
    samples = int(meta[0])  # Регистр 100
    
    # Функция для декодирования float из двух uint16 во всех вариантах порядка байтов
    def _float_variants_from_regs(reg1: int, reg2: int) -> dict:
        """Декодируем float из двух uint16 во всех популярных Modbus byte/word order.
        A,B = bytes of reg1 (hi,lo); C,D = bytes of reg2 (hi,lo)
        Variants: ABCD, BADC (swap bytes in words), CDAB (swap words), DCBA (full reverse)
        """
        A = (reg1 >> 8) & 0xFF
        B = reg1 & 0xFF
        C = (reg2 >> 8) & 0xFF
        D = reg2 & 0xFF
        orders = {
            "ABCD": bytes([A, B, C, D]),
            "BADC": bytes([B, A, D, C]),
            "CDAB": bytes([C, D, A, B]),
            "DCBA": bytes([D, C, B, A]),
        }
        out: dict[str, float] = {}
        for k, bb in orders.items():
            try:
                v = float(struct.unpack(">f", bb)[0])
            except Exception:
                continue
            if math.isfinite(v):
                out[k] = v
        return out
    
    def _float_from_regs_with_key(reg1: int, reg2: int, key: str) -> float:
        vmap = _float_variants_from_regs(reg1, reg2)
        return float(vmap.get(key, float("nan")))
    
    # Используем формат CDAB для всех float значений в NMR данных
    # Диапазон x_min/x_max и freq: 38000-44000
    
    meta_float_key = "CDAB"  # Фиксированный формат для NMR
    
    # Извлекаем регистры для всех float полей
    xmin_r1, xmin_r2 = int(meta[1]), int(meta[2])
    xmax_r1, xmax_r2 = int(meta[3]), int(meta[4])
    y_min_r1, y_min_r2 = int(meta[5]), int(meta[6])
    y_max_r1, y_max_r2 = int(meta[7]), int(meta[8])
    freq_r1, freq_r2 = int(meta[9]), int(meta[10])
    ampl_r1, ampl_r2 = int(meta[11]), int(meta[12])
    int_r1, int_r2 = int(meta[13]), int(meta[14])
    t2_r1, t2_r2 = int(meta[15]), int(meta[16])
    
    # Декодируем все float значения используя формат CDAB
    x_min = _float_from_regs_with_key(xmin_r1, xmin_r2, meta_float_key)
    x_max = _float_from_regs_with_key(xmax_r1, xmax_r2, meta_float_key)
    y_min = _float_from_regs_with_key(y_min_r1, y_min_r2, meta_float_key)
    y_max = _float_from_regs_with_key(y_max_r1, y_max_r2, meta_float_key)
    freq = _float_from_regs_with_key(freq_r1, freq_r2, meta_float_key)
    ampl = _float_from_regs_with_key(ampl_r1, ampl_r2, meta_float_key)
    integral = _float_from_regs_with_key(int_r1, int_r2, meta_float_key)
    t2 = _float_from_regs_with_key(t2_r1, t2_r2, meta_float_key)
    
    print(f"✓ Используется формат float: {meta_float_key}")
    
    # Выводим результаты
    print(f"\n✓ NMR данные декодированы:")
    print(f"  Samples (100): {samples} (0x{samples:04X})")
    print(f"  X min (101-102): {x_min:.6f}")
    print(f"  X max (103-104): {x_max:.6f}")
    print(f"  Y min (105-106): {y_min:.6f}")
    print(f"  Y max (107-108): {y_max:.6f}")
    print(f"  Freq (109-110): {freq:.6f}")
    print(f"  Ampl (111-112): {ampl:.6f}")
    print(f"  Integral (113-114): {integral:.6f}")
    print(f"  T2 (115-116): {t2:.6f}")
    print(f"  Data (120-375): {len(data_regs)} значений")
    if len(data_regs) > 0:
        print(f"    Первые 10 значений: {data_regs[:10]}")
        print(f"    Последние 10 значений: {data_regs[-10:]}")
    
    return {
        'samples': samples,
        'x_min': float(x_min),
        'x_max': float(x_max),
        'y_min': float(y_min),
        'y_max': float(y_max),
        'freq': float(freq),
        'ampl': float(ampl),
        'int': float(integral),
        't2': float(t2),
        'meta_float_key': meta_float_key,
        'data': data_regs
    }

def read_pxe_data(sock):
    """Чтение PXE данных
    
    Читает регистры:
    - 500: sample_n (uint16)
    - 501: fit (uint16)
    - 520-519+n*2: data x и data y (n*2 регистров, где n = sample_n)
    
    Данные читаются попарно: data_x[0], data_y[0], data_x[1], data_y[1], ...
    """
    import math
    import struct
    
    print(f"\n=== Чтение PXE данных ===")
    
    # Читаем sample_n и fit (регистры 500-501)
    print(f"Чтение регистров 500-501 (sample_n, fit)...")
    frame = build_read_multiple_registers_frame(4, 500, 2)
    
    try:
        hex_dump("TX", frame)
        sock.sendall(frame)
        time.sleep(0.1)
        
        resp = b''
        try:
            sock.settimeout(0.5)
            while True:
                chunk = sock.recv(512)
                if not chunk:
                    break
                resp += chunk
                if len(resp) >= 5:
                    start_idx = find_modbus_frame_start(resp)
                    if start_idx >= 0:
                        frame_start = resp[start_idx:]
                        if len(frame_start) >= 3:
                            byte_count = frame_start[2]
                            expected_length = 3 + byte_count + 2
                            if len(frame_start) >= expected_length:
                                break
        except socket.timeout:
            pass
        finally:
            sock.settimeout(2.0)
        
        if resp:
            hex_dump("RX", resp)
            parsed = parse_multiple_registers_response(resp)
            if parsed is None:
                print(f"⚠️  Ошибка: parse_multiple_registers_response вернул None")
                return None
            if 'is_error' in parsed and parsed['is_error']:
                print(f"⚠️  Ошибка Modbus: {parsed.get('error_message', 'unknown')}")
                return None
            if 'registers' in parsed and len(parsed['registers']) >= 2:
                sample_n = int(parsed['registers'][0])
                fit = int(parsed['registers'][1])
                print(f"✓ sample_n (регистр 500): {sample_n}")
                print(f"✓ fit (регистр 501): {fit}")
                
                if sample_n == 0:
                    print(f"⚠️  sample_n = 0, возможно регистры пустые или данные еще не записаны")
                    return {
                        'sample_n': 0,
                        'fit': fit,
                        'array_size': 0,
                        'data_x': [],
                        'data_y': [],
                        'data_raw': []
                    }
            else:
                print(f"⚠️  Ошибка: не удалось прочитать регистры 500-501")
                print(f"   parsed: {parsed}")
                if parsed and 'registers' in parsed:
                    print(f"   registers length: {len(parsed['registers'])}")
                return None
        else:
            print(f"⚠️  Ошибка: нет ответа от устройства")
            return None
    except Exception as e:
        print(f"⚠️  Ошибка при чтении регистров 500-501: {e}")
        return None
    
    if sample_n <= 0:
        print(f"⚠️  Предупреждение: sample_n = {sample_n}, должно быть > 0")
        return None
    
    # Вычисляем размер массива данных: n * 2
    array_size = sample_n * 2
    print(f"✓ array_size: {array_size} (sample_n * 2)")
    
    # Читаем данные начиная с регистра 520
    # Читаем частями по 30 регистров для надежности
    print(f"Чтение данных (регистры 520-{519+array_size})...")
    registers_dict = {}
    
    # Разбиваем на части по 30 регистров
    for offset in range(0, array_size, 30):
        chunk_size = min(30, array_size - offset)
        start_addr = 520 + offset
        print(f"  Чтение регистров {start_addr}-{start_addr + chunk_size - 1} ({chunk_size} регистров)...")
        
        frame = build_read_multiple_registers_frame(4, start_addr, chunk_size)
        
        try:
            hex_dump("TX", frame)
            sock.sendall(frame)
            time.sleep(0.1)
            
            resp = b''
            try:
                sock.settimeout(0.5)
                while True:
                    chunk = sock.recv(512)
                    if not chunk:
                        break
                    resp += chunk
                    if len(resp) >= 5:
                        start_idx = find_modbus_frame_start(resp)
                        if start_idx >= 0:
                            frame_start = resp[start_idx:]
                            if len(frame_start) >= 3:
                                byte_count = frame_start[2]
                                expected_length = 3 + byte_count + 2
                                if len(frame_start) >= expected_length:
                                    break
            except socket.timeout:
                pass
            finally:
                sock.settimeout(2.0)
            
            if resp:
                hex_dump("RX", resp)
                parsed = parse_multiple_registers_response(resp)
                if parsed and 'values' in parsed:
                    for i, val in enumerate(parsed['values']):
                        registers_dict[start_addr + i] = val
        except Exception as e:
            print(f"  ⚠️  Ошибка при чтении регистров {start_addr}-{start_addr + chunk_size - 1}: {e}")
    
    # Собираем данные в массив
    data_regs = []
    for addr in range(520, 520 + array_size):
        if addr in registers_dict:
            data_regs.append(registers_dict[addr])
        else:
            print(f"⚠️  Предупреждение: регистр {addr} не прочитан")
            data_regs.append(0)
    
    if len(data_regs) < array_size:
        print(f"⚠️  Ошибка: не удалось прочитать все данные (регистры 520-{519+array_size})")
        print(f"   Ожидалось: {array_size} регистров, получено: {len(data_regs)}")
        return None
    
    print(f"✓ Прочитано {len(data_regs)} регистров данных (регистры 520-{519+array_size})")
    
    # Разделяем данные на data_x и data_y
    # Данные идут попарно: data_x[0], data_y[0], data_x[1], data_y[1], ...
    data_x = []
    data_y = []
    for i in range(sample_n):
        if i * 2 + 1 < len(data_regs):
            data_x.append(int(data_regs[i * 2]))
            data_y.append(int(data_regs[i * 2 + 1]))
        else:
            print(f"⚠️  Предупреждение: недостаточно данных для пары {i}")
            break
    
    print(f"✓ Разделено на data_x и data_y: {len(data_x)} пар")
    if len(data_x) > 0:
        print(f"  data_x первые 5: {data_x[:5]}")
        print(f"  data_x последние 5: {data_x[-5:]}")
        print(f"  data_y первые 5: {data_y[:5]}")
        print(f"  data_y последние 5: {data_y[-5:]}")
    
    return {
        'sample_n': sample_n,
        'fit': fit,
        'array_size': array_size,
        'data_x': data_x,
        'data_y': data_y,
        'data_raw': data_regs[:array_size]  # Raw данные для отладки
    }

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

def read_float_value(sock, address: int):
    """Чтение float значения из двух регистров (address и address+1)"""
    print(f"\n=== Чтение float значения ===")
    print(f"Чтение регистров {address} и {address+1}...")
    
    # Читаем два регистра
    frame = build_read_multiple_registers_frame(4, address, 2)
    
    try:
        hex_dump("TX", frame)
        sock.sendall(frame)
        
        time.sleep(0.1)
        
        # Читаем ответ
        resp = b''
        try:
            sock.settimeout(0.5)
            while True:
                chunk = sock.recv(512)
                if not chunk:
                    break
                resp += chunk
                if len(resp) >= 5:
                    start_idx = find_modbus_frame_start(resp)
                    if start_idx >= 0:
                        frame_start = resp[start_idx:]
                        if len(frame_start) >= 3:
                            byte_count = frame_start[2]
                            expected_length = 3 + byte_count + 2
                            if len(frame_start) >= expected_length:
                                break
        except socket.timeout:
            pass
        finally:
            sock.settimeout(2.0)
        
        if resp:
            hex_dump("RX", resp)
            
            parsed = parse_multiple_registers_response(resp)
            if not parsed:
                print("Ошибка: не удалось распарсить ответ")
                return None
            
            # Проверяем на ошибку Modbus
            if parsed.get('is_error'):
                error_msg = parsed['error_message']
                error_code = parsed['error_code']
                print(f"❌ Ошибка Modbus: {error_msg} (код {error_code})")
                return None
            
            registers = parsed.get('registers', [])
            if len(registers) < 2:
                print(f"❌ Ошибка: получено только {len(registers)} регистров вместо 2")
                return None
            
            # Меняем местами регистры: первый становится вторым, второй становится первым
            # FF DF 44 45 -> 44 45 FF DF
            swapped_registers = [registers[1], registers[0]]
            
            print(f"  Исходные регистры: {registers[0]:04X} {registers[1]:04X}")
            print(f"  После перестановки регистров: {swapped_registers[0]:04X} {swapped_registers[1]:04X}")
            
            # Преобразуем в float
            float_val = registers_to_float(swapped_registers, 0)
            
            print(f"\n✓ Данные успешно прочитаны!")
            print(f"\nРезультаты:")
            print(f"  Регистр {address}: {registers[0]} (0x{registers[0]:04X})")
            print(f"  Регистр {address+1}: {registers[1]} (0x{registers[1]:04X})")
            print(f"  Float значение: {float_val:.6f}")
            print(f"  Float значение (научная нотация): {float_val:.6e}")
            
            return float_val
        else:
            print("RX: (empty)")
            return None
    except socket.timeout:
        print("RX: (timeout)")
        return None
    except (ConnectionError, OSError) as e:
        print(f"Ошибка соединения: {e}")
    return None

def read_int_value(sock, address: int):
    """Чтение int значения из одного регистра (16-битное знаковое целое)"""
    print(f"\n=== Чтение int значения ===")
    print(f"Чтение регистра {address}...")
    
    # Читаем один регистр
    frame = build_read_frame(4, address)
    
    try:
        hex_dump("TX", frame)
        sock.sendall(frame)
        
        time.sleep(0.1)
        
        # Читаем ответ
        resp = b''
        try:
            sock.settimeout(0.5)
            while True:
                chunk = sock.recv(512)
                if not chunk:
                    break
                resp += chunk
                if len(resp) >= 7:  # Минимальная длина ответа: unit_id(1) + function(1) + byte_count(1) + data(2) + CRC(2) = 7
                    start_idx = find_modbus_frame_start(resp)
                    if start_idx >= 0:
                        frame_start = resp[start_idx:]
                        if len(frame_start) >= 7:
                            break
        except socket.timeout:
            pass
        finally:
            sock.settimeout(2.0)
        
        if resp:
            hex_dump("RX", resp)
            
            # Находим начало фрейма (может быть мусор в начале)
            start_idx = find_modbus_frame_start(resp)
            if start_idx > 0:
                print(f"⚠️  Найден мусор в начале ответа ({start_idx} байт), пропускаем...")
                resp = resp[start_idx:]
            
            # Сначала проверяем на ошибку Modbus
            error = parse_modbus_error(resp)
            if error:
                error_msg = error.get('error_message', 'Unknown error')
                error_code = error.get('error_code', 0)
                print(f"❌ Ошибка Modbus: {error_msg} (код {error_code})")
                return None
            
            parsed = parse_read_response(resp)
            if not parsed:
                print("Ошибка: не удалось распарсить ответ")
                return None
            
            # Проверяем CRC
            if not parsed.get('crc_valid', False):
                print(f"⚠️  Предупреждение: CRC не совпадает!")
                print(f"   Получен CRC: {parsed.get('received_crc')}")
                print(f"   Вычислен CRC: {parsed.get('calculated_crc')}")
            
            # Получаем значение как uint16
            uint16_value = parsed.get('value', 0)
            
            # Преобразуем uint16 в int16 (two's complement)
            # Если значение >= 32768, это отрицательное число
            if uint16_value >= 32768:
                int16_value = uint16_value - 65536
            else:
                int16_value = uint16_value
            
            print(f"\n✓ Данные успешно прочитаны!")
            print(f"\nРезультаты:")
            print(f"  Регистр {address}: {uint16_value} (0x{uint16_value:04X})")
            print(f"  Int значение (int16): {int16_value}")
            print(f"  Uint значение (uint16): {uint16_value}")
            
            return int16_value
        else:
            print("RX: (empty)")
            return None
    except socket.timeout:
        print("RX: (timeout)")
        return None
    except (ConnectionError, OSError) as e:
        print(f"Ошибка соединения: {e}")
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
        try:
            sock.sendall(frame)
        except (ConnectionError, OSError) as e:
            # Если соединение разорвано, пробрасываем исключение наверх
            if return_parsed:
                raise
            else:
                raise
        
        time.sleep(0.1)
        
        try:
            # Пробуем читать ответ с несколькими попытками и увеличенным таймаутом
            resp = b''
            sock.settimeout(1.0)  # Увеличиваем таймаут до 1 секунды
            try:
                # Читаем все доступные данные
                while True:
                    chunk = sock.recv(256)
                    if not chunk:
                        break
                    resp += chunk
                    # Если получили достаточно данных, проверяем, не закончился ли фрейм
                    if len(resp) >= 5:
                        # Проверяем, есть ли полный фрейм (минимум 7 байт для ответа на чтение)
                        if len(resp) >= 7:
                            # Проверяем, может быть это полный фрейм
                            byte_count = resp[2] if len(resp) > 2 else 0
                            expected_length = 3 + byte_count + 2  # unit_id + function + byte_count + data + CRC
                            if len(resp) >= expected_length:
                                # Полный фрейм получен
                                break
            except socket.timeout:
                # Таймаут - возможно, все данные уже получены
                pass
            finally:
                sock.settimeout(2.0)  # Возвращаем обычный таймаут
            
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
                        # Проверяем на ошибку Modbus
                        if parsed.get('is_error'):
                            error_msg = parsed.get('error_message', 'Unknown error')
                            error_code = parsed.get('error_code', 0)
                            print(f"\n  ❌ Ошибка Modbus:")
                            print(f"    Код ошибки: {error_code}")
                            print(f"    Сообщение: {error_msg}")
                            if parsed.get('crc_valid'):
                                print(f"    CRC: ✓ Валиден")
                            else:
                                print(f"    CRC: ✗ Ошибка!")
                        else:
                            print(f"\n  Расшифровка ответа:")
                            print(f"    Unit ID: {parsed['unit_id']}")
                            print(f"    Функция: {parsed['function']:02d} (Read Input Registers)")
                            print(f"    Количество байт данных: {parsed['byte_count']}")
                            print(f"    Значение регистра: {parsed['value']} (десятичное)")
                            print(f"    Значение регистра: {parsed['value_hex']} (шестнадцатеричное)")
                            
                            # Предупреждение, если значение 0 (может быть признаком несуществующего регистра)
                            if parsed['value'] == 0:
                                print(f"    ⚠️  Предупреждение: значение регистра равно 0. Возможно, регистр не существует.")
                            
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
                        print(f"  Сырые данные ответа: {resp.hex(' ').upper()}")
                        print(f"  Длина ответа: {len(resp)} байт")
                        # Пробуем найти начало фрейма
                        start_idx = find_modbus_frame_start(resp)
                        if start_idx > 0:
                            print(f"  ⚠️  Найден мусор в начале ответа ({start_idx} байт)")
                            print(f"  Данные после мусора: {resp[start_idx:].hex(' ').upper()}")
            else:
                print("RX: (empty)")
                print("  ⚠️  Нет ответа от устройства. Возможные причины:")
                print("     - Устройство не отвечает на этот адрес")
                print("     - Таймаут слишком короткий")
                print("     - Проблема с соединением")
                return None
        except socket.timeout:
            print("RX: (timeout)")
            print("  ⚠️  Таймаут при чтении ответа. Возможные причины:")
            print("     - Устройство не отвечает на этот адрес")
            print("     - Таймаут слишком короткий")
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
                
                # Специальная команда для чтения IR данных как int (регистры 4201-4701)
                if cmd.lower() in ['ir int', 'ir_int', 'read_ir_int']:
                    read_ir_data_int(sock)
                    continue
                
                # Специальная команда для чтения IR данных (ModbusClient, без сокета)
                if cmd.lower() in ['ir', 'read_ir']:
                    read_ir_data_direct()
                    continue
                # IR через сокет (legacy, для сравнения)
                if cmd.lower() in ['ir sock', 'ir_sock', 'ir socket']:
                    read_ir_data(sock)
                    continue

                # Специальная команда для чтения NMR данных
                if cmd.lower() in ['nmr', 'read_nmr']:
                    read_nmr_data(sock)
                    continue
                
                # Специальная команда для чтения PXE данных
                if cmd.lower() in ['pxe', 'read_pxe']:
                    read_pxe_data(sock)
                    continue
                
                # Команда для чтения float значения
                parts = cmd.split()
                if len(parts) >= 2 and parts[0].lower() == 'float':
                    try:
                        address = int(parts[1])
                        read_float_value(sock, address)
                    except ValueError:
                        print("Ошибка: неверный адрес. Использование: float <адрес>")
                    continue
                
                # Команда для чтения int значения
                if len(parts) >= 2 and parts[0].lower() == 'int':
                    try:
                        address = int(parts[1])
                        read_int_value(sock, address)
                    except ValueError:
                        print("Ошибка: неверный адрес. Использование: int <адрес>")
                    continue
                
                # Команда для чтения регистров 4201 и 4701 как int
                if cmd.lower() in ['read_int_regs', 'int_regs']:
                    print("\n=== Чтение регистров 4201 и 4701 как int ===")
                    print("\nРегистр 4201:")
                    val1 = read_int_value(sock, 4201)
                    time.sleep(0.2)
                    print("\nРегистр 4701:")
                    val2 = read_int_value(sock, 4701)
                    if val1 is not None and val2 is not None:
                        print(f"\n=== Итоговые результаты ===")
                        print(f"  Регистр 4201: {val1}")
                        print(f"  Регистр 4701: {val2}")
                    continue
                
                # Парсим команду: функция адрес [реле]
                if len(parts) < 2:
                    print("Использование:")
                    print("  Чтение: 03 <адрес>  или  04 <адрес>")
                    print("    (03 = Read Holding Registers, 04 = Read Input Registers)")
                    print("  Запись: 06 <адрес> <номер_реле>")
                    print("  Float: float <адрес>  - прочитать float из двух регистров")
                    print("  Int: int <адрес>  - прочитать int (16-битное знаковое) из одного регистра")
                    print("  IR данные: ir  или  read_ir  - прочитать IR через ModbusClient (регистры 400-414, 420-477)")
                    print("  IR через сокет: ir sock  - прочитать IR через сокет (legacy)")
                    print("  IR данные int: ir int  или  ir_int  - прочитать IR данные как int (регистры 4201-4701)")
                    print("  NMR данные: nmr  или  read_nmr")
                    print("  PXE данные: pxe  или  read_pxe  - прочитать PXE данные (регистры 500-501, 520-519+n*2)")
                    print("  Int регистры: int_regs  или  read_int_regs  - прочитать регистры 4201 и 4701")
                    print("Примеры:")
                    print("  04 102  - прочитать регистр 102")
                    print("  04 1021  - прочитать регистр 1021")
                    print("  06 102 2  - включить реле номер 2 в регистре 102")
                    print("  float 401  - прочитать float из регистров 401-402")
                    print("  int 4201  - прочитать int из регистра 4201")
                    print("  int_regs  - прочитать регистры 4201 и 4701 как int")
                    print("  ir  - прочитать все IR данные как float (регистры 400-414, 420-477)")
                    print("  ir int  - прочитать все IR данные как int (регистры 4201-4701)")
                    print("  nmr  - прочитать все NMR данные (регистры 100-116, 120-375)")
                    print("  pxe  - прочитать все PXE данные (регистры 500-501, 520-519+n*2)")
                    continue
                
                function = int(parts[0])
                address = int(parts[1])
                
                if function == 3 or function == 4:
                    # Чтение регистра (функция 03 = Read Holding Registers, 04 = Read Input Registers)
                    frame = build_read_frame(function, address)
                    
                    func_name = "Read Holding Registers" if function == 3 else "Read Input Registers"
                    # Отправляем 2 раза
                    print(f"\nОтправка запроса (функция {function:02d} - {func_name}, адрес {address})...")
                    print(f"  Адрес в hex: 0x{address:04X} ({address:04d})")
                    print(f"  Старший байт адреса: 0x{(address >> 8) & 0xFF:02X}, младший байт: 0x{address & 0xFF:02X}")
                    for i in range(2):
                        print(f"\n--- Попытка {i+1} ---")
                        max_retries = 3
                        retry_count = 0
                        success = False
                        
                        while retry_count < max_retries and not success:
                            try:
                                send_frame(sock, frame, is_write=False)
                                success = True
                            except (ConnectionError, OSError) as e:
                                retry_count += 1
                                print(f"  ⚠️  Ошибка соединения: {e}")
                                if retry_count < max_retries:
                                    print(f"  Переподключение (попытка {retry_count}/{max_retries-1})...")
                                    try:
                                        sock.close()
                                    except:
                                        pass
                                    try:
                                        sock = connect_socket()
                                        time.sleep(0.3)  # Увеличиваем задержку после переподключения
                                        print(f"  ✓ Переподключено, повтор запроса...")
                                    except Exception as e2:
                                        print(f"  ❌ Ошибка переподключения: {e2}")
                                        if retry_count >= max_retries:
                                            raise
                                else:
                                    print(f"  ❌ Не удалось переподключиться после {max_retries} попыток")
                                    raise
                            except Exception as e:
                                # Другие ошибки пробрасываем наверх
                                raise
                        
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
                        max_retries = 3
                        retry_count = 0
                        success = False
                        
                        while retry_count < max_retries and not success:
                            try:
                                send_frame(sock, write_frame, is_write=True)
                                success = True
                            except (ConnectionError, OSError) as e:
                                retry_count += 1
                                print(f"  ⚠️  Ошибка соединения: {e}")
                                if retry_count < max_retries:
                                    print(f"  Переподключение (попытка {retry_count}/{max_retries-1})...")
                                    try:
                                        sock.close()
                                    except:
                                        pass
                                    try:
                                        sock = connect_socket()
                                        time.sleep(0.3)
                                        print(f"  ✓ Переподключено, повтор запроса...")
                                    except Exception as e2:
                                        print(f"  ❌ Ошибка переподключения: {e2}")
                                        if retry_count >= max_retries:
                                            raise
                                else:
                                    print(f"  ❌ Не удалось переподключиться после {max_retries} попыток")
                                    raise
                            except Exception as e:
                                raise
                        
                        if i < 1:
                            time.sleep(0.5)
                
                else:
                    print(f"Поддерживаются функции: 03 (Read Holding Registers), 04 (Read Input Registers), 06 (запись)")
                    continue
                
            except ValueError:
                print("Ошибка: неверный формат числа")
            except KeyboardInterrupt:
                print("\nВыход...")
                break
            except (ConnectionError, OSError) as e:
                print(f"⚠️  Ошибка соединения: {e}")
                # При ошибке соединения переподключаемся
                try:
                    if sock:
                        sock.close()
                except:
                    pass
                sock = None
                print("Переподключение...")
                try:
                    time.sleep(1)
                    sock = connect_socket()
                    time.sleep(0.2)
                    print("✓ Переподключено успешно!")
                except Exception as e2:
                    print(f"❌ Ошибка переподключения: {e2}")
                    sock = None
            except Exception as e:
                print(f"Ошибка: {e}")
                import traceback
                traceback.print_exc()
                # При других ошибках тоже пробуем переподключиться
                try:
                    if sock:
                        sock.close()
                except:
                    pass
                sock = None
                print("Переподключение...")
                try:
                    time.sleep(1)
                    sock = connect_socket()
                    time.sleep(0.2)
                    print("✓ Переподключено успешно!")
                except Exception as e2:
                    print(f"❌ Ошибка переподключения: {e2}")
                    sock = None
    
    finally:
        if sock:
            sock.close()
        print("\nОтключено.")

if __name__ == "__main__":
    main()