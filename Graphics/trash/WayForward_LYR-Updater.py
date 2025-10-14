#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import struct
from PIL import Image
import json

# Обновлятор LYR файлов WayForward - обновляет ссылки на метатайлы после изменений
# Создает новый LYR файл с правильными ID метатайлов

# Настройки
LYRFormat = 2                    # Формат как в LYR-Extract
ScreenName = "STATUS"            # Имя LYR файла
OldMetatiles = "STATUS_metatile_old.png"   # Старый файл метатайлов
NewMetatiles = "STATUS_metatile.png"       # Новый файл метатайлов  
OutputLYR = "STATUS_updated.lyr"           # Выходной LYR файл

def extract_metatiles_from_sheet(sheet_path):
    """Извлекает все метатайлы из листа как отдельные изображения"""
    
    if not os.path.exists(sheet_path):
        print(f"Не найден файл: {sheet_path}")
        return None
    
    img = Image.open(sheet_path)
    width, height = img.size
    
    metatiles_x = width // 16
    metatiles_y = height // 16
    
    metatiles = {}  # id -> PIL Image
    
    for my in range(metatiles_y):
        for mx in range(metatiles_x):
            metatile_id = my * metatiles_x + mx
            
            x = mx * 16
            y = my * 16
            
            metatile_img = img.crop((x, y, x + 16, y + 16))
            metatiles[metatile_id] = metatile_img
    
    print(f"Извлечено {len(metatiles)} метатайлов из {sheet_path}")
    return metatiles

def find_metatile_matches(old_metatiles, new_metatiles):
    """Находит соответствия между старыми и новыми метатайлами"""
    
    print("Поиск соответствий между метатайлами...")
    
    # Создаем хеши для быстрого поиска
    old_hashes = {}  # hash -> old_id
    for old_id, img in old_metatiles.items():
        pixels = tuple(img.getdata())
        img_hash = hash(pixels)
        old_hashes[img_hash] = old_id
    
    # Ищем соответствия
    id_mapping = {}  # old_id -> new_id
    unmatched_old = set(old_metatiles.keys())
    unmatched_new = set(new_metatiles.keys())
    
    for new_id, new_img in new_metatiles.items():
        pixels = tuple(new_img.getdata())
        img_hash = hash(pixels)
        
        if img_hash in old_hashes:
            old_id = old_hashes[img_hash]
            id_mapping[old_id] = new_id
            unmatched_old.discard(old_id)
            unmatched_new.discard(new_id)
    
    print(f"Найдено соответствий: {len(id_mapping)}")
    print(f"Старых метатайлов без пары: {len(unmatched_old)}")
    print(f"Новых метатайлов без пары: {len(unmatched_new)}")
    
    if unmatched_old:
        print(f"Удаленные метатайлы (старые ID): {sorted(unmatched_old)}")
    
    if unmatched_new:
        print(f"Новые метатайлы (новые ID): {sorted(unmatched_new)}")
    
    return id_mapping

def update_lyr_file(input_lyr, output_lyr, id_mapping):
    """Обновляет LYR файл с новыми ID метатайлов"""
    
    if not os.path.exists(input_lyr):
        print(f"Не найден LYR файл: {input_lyr}")
        return False
    
    print(f"Обновляю LYR файл: {input_lyr} -> {output_lyr}")
    
    with open(input_lyr, 'rb') as input_file:
        with open(output_lyr, 'wb') as output_file:
            
            # Копируем заголовок без изменений
            ScreenFlags = struct.unpack('<H', input_file.read(2))[0]
            ScreenWidth = struct.unpack('<H', input_file.read(2))[0]
            ScreenHeight = struct.unpack('<H', input_file.read(2))[0]
            ScreenCount = struct.unpack('<H', input_file.read(2))[0]
            
            output_file.write(struct.pack('<H', ScreenFlags))
            output_file.write(struct.pack('<H', ScreenWidth))
            output_file.write(struct.pack('<H', ScreenHeight))
            output_file.write(struct.pack('<H', ScreenCount))
            
            print(f"Карта: {ScreenWidth}x{ScreenHeight}, экранов: {ScreenCount}")
            
            # Копируем дополнительные поля заголовка
            if LYRFormat == 0:
                header_data = input_file.read(8)  # 4 поля по 2 байта
                output_file.write(header_data)
            elif LYRFormat == 1:
                header_data = input_file.read(8)  # 4 поля по 2 байта
                output_file.write(header_data)
            else:
                header_data = input_file.read(12)  # 6 полей по 2 байта
                output_file.write(header_data)
            
            # Копируем индексы экранов без изменений
            screen_map_data = input_file.read(ScreenWidth * ScreenHeight * 2)
            output_file.write(screen_map_data)
            
            # Выравнивание для формата 0
            if LYRFormat == 0:
                if input_file.tell() % 4 != 0:
                    padding = input_file.read(2)
                    output_file.write(padding)
            
            # Дополнительные данные для формата 3+
            if LYRFormat > 2:
                # Копируем дополнительные блоки
                extra_data1 = input_file.read(ScreenWidth * ScreenHeight * 2)
                extra_data2 = input_file.read(ScreenWidth * ScreenHeight * 2)
                output_file.write(extra_data1)
                output_file.write(extra_data2)
                
                # Неизвестные блоки (размеры нужно прочитать из заголовка)
                # Для простоты пропускаем, так как счетчики в наших тестах = 0
            
            # Обновляем данные экранов
            updated_metatiles = 0
            unchanged_metatiles = 0
            
            for screen_id in range(ScreenCount):
                print(f"Обрабатываю экран {screen_id + 1}/{ScreenCount}...", end='\r')
                
                for pos in range(256):  # 16x16 метатайлов на экран
                    # Читаем старый ID метатайла
                    metatile_raw = struct.unpack('<H', input_file.read(2))[0]
                    
                    # Извлекаем ID с учетом флагов
                    if ScreenFlags == 0x0010 or ScreenFlags == 0x0020:
                        old_metatile_id = metatile_raw & 0x03FF
                        flags_mask = metatile_raw & 0xFC00
                    elif ScreenFlags == 0x0040:
                        old_metatile_id = metatile_raw & 0x0FFF
                        flags_mask = metatile_raw & 0xF000
                    else:
                        old_metatile_id = metatile_raw & 0x07FF
                        flags_mask = metatile_raw & 0xF800
                    
                    # Ищем новый ID
                    if old_metatile_id in id_mapping:
                        new_metatile_id = id_mapping[old_metatile_id]
                        updated_metatiles += 1
                    else:
                        # Метатайл не найден - оставляем 0 (пустой)
                        new_metatile_id = 0
                        if old_metatile_id != 0:  # Не считаем замены 0->0
                            updated_metatiles += 1
                    
                    if old_metatile_id == new_metatile_id:
                        unchanged_metatiles += 1
                    
                    # Создаем новое значение с сохранением флагов
                    new_metatile_raw = new_metatile_id | flags_mask
                    
                    # Записываем обновленное значение
                    output_file.write(struct.pack('<H', new_metatile_raw))
            
            print(f"\nОбновлено метатайлов: {updated_metatiles}")
            print(f"Без изменений: {unchanged_metatiles}")
    
    return True

def create_mapping_report(id_mapping, old_count, new_count, output_path):
    """Создает отчет о переназначении ID"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=== Отчет о переназначении метатайлов ===\n\n")
        f.write(f"Старых метатайлов: {old_count}\n")
        f.write(f"Новых метатайлов: {new_count}\n")
        f.write(f"Найдено соответствий: {len(id_mapping)}\n\n")
        
        f.write("Переназначения (Старый ID -> Новый ID):\n")
        f.write("Старый | Позиция старая | Новый | Позиция новая\n")
        f.write("-------|----------------|-------|---------------\n")
        
        for old_id, new_id in sorted(id_mapping.items()):
            old_x = (old_id % 16) * 16
            old_y = (old_id // 16) * 16
            new_x = (new_id % 16) * 16  
            new_y = (new_id // 16) * 16
            
            f.write(f"{old_id:6} | ({old_x:3},{old_y:3})        | {new_id:5} | ({new_x:3},{new_y:3})\n")
        
        # Показываем удаленные метатайлы
        all_old_ids = set(range(old_count))
        mapped_old_ids = set(id_mapping.keys())
        removed_ids = all_old_ids - mapped_old_ids
        
        if removed_ids:
            f.write(f"\nУдаленные метатайлы (будут заменены на 0):\n")
            for old_id in sorted(removed_ids):
                old_x = (old_id % 16) * 16
                old_y = (old_id // 16) * 16
                f.write(f"ID {old_id:3} (позиция {old_x:3},{old_y:3})\n")
    
    print(f"Отчет сохранен: {output_path}")

def main():
    print("=== Обновлятор LYR файлов WayForward ===")
    print(f"Старые метатайлы: {OldMetatiles}")
    print(f"Новые метатайлы: {NewMetatiles}")
    print(f"Входной LYR: {ScreenName}.lyr")
    print(f"Выходной LYR: {OutputLYR}")
    print()
    
    # Проверяем наличие файлов
    input_lyr = f"{ScreenName}.lyr"
    
    if not os.path.exists(input_lyr):
        print(f"ОШИБКА: Не найден LYR файл: {input_lyr}")
        return
    
    if not os.path.exists(OldMetatiles):
        print(f"ОШИБКА: Не найден старый файл метатайлов: {OldMetatiles}")
        print("Переименуйте оригинальный STATUS_metatile.png в STATUS_metatile_old.png")
        return
        
    if not os.path.exists(NewMetatiles):
        print(f"ОШИБКА: Не найден новый файл метатайлов: {NewMetatiles}")
        return
    
    # Извлекаем метатайлы из листов
    old_metatiles = extract_metatiles_from_sheet(OldMetatiles)
    new_metatiles = extract_metatiles_from_sheet(NewMetatiles)
    
    if old_metatiles is None or new_metatiles is None:
        return
    
    # Находим соответствия между метатайлами
    id_mapping = find_metatile_matches(old_metatiles, new_metatiles)
    
    # Обновляем LYR файл
    success = update_lyr_file(input_lyr, OutputLYR, id_mapping)
    
    if success:
        # Создаем отчет
        report_path = f"{ScreenName}_mapping_report.txt"
        create_mapping_report(id_mapping, len(old_metatiles), len(new_metatiles), report_path)
        
        print()
        print("=== Обновление завершено ===")
        print(f"Новый LYR файл: {OutputLYR}")
        print(f"Отчет: {report_path}")
        print()
        print("Теперь можете:")
        print("1. Протестировать новый LYR файл")
        print("2. Переименовать его в оригинальное имя если всё работает")
    else:
        print("Ошибка при обновлении LYR файла")

if __name__ == "__main__":
    main()
