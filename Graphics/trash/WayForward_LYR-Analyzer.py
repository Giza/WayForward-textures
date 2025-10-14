#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import struct
from PIL import Image
import json

# Анализатор LYR файлов WayForward - показывает связи между метатайлами и картами
# Создает файлы с данными для редактирования

# Настройки
LYRFormat = 2                    # Формат как в LYR-Extract
ScreenName = "STATUS"            # Имя LYR файла
MetatilesName = "STATUS"         # Имя PNG метатайлов
CreateDataFiles = True           # Создавать JSON файлы с данными

def analyze_metatile_usage(lyr_path, metatiles_path):
    """Анализирует какие метатайлы где используются в LYR файле"""
    
    if not os.path.exists(lyr_path):
        print(f"Не найден LYR файл: {lyr_path}")
        return None
        
    if not os.path.exists(metatiles_path):
        print(f"Не найден файл метатайлов: {metatiles_path}")
        return None
    
    print(f"=== Анализ LYR файла: {lyr_path} ===")
    
    # Загружаем информацию о метатайлах
    metatiles_img = Image.open(metatiles_path)
    mt_width, mt_height = metatiles_img.size
    max_metatiles = (mt_width // 16) * (mt_height // 16)
    
    print(f"Файл метатайлов: {metatiles_path}")
    print(f"Размер листа: {mt_width}x{mt_height}")
    print(f"Максимум метатайлов: {max_metatiles}")
    print()
    
    # Читаем LYR файл
    with open(lyr_path, 'rb') as f:
        # Заголовок 
        ScreenFlags = struct.unpack('<H', f.read(2))[0]
        ScreenWidth = struct.unpack('<H', f.read(2))[0]  
        ScreenHeight = struct.unpack('<H', f.read(2))[0]
        ScreenCount = struct.unpack('<H', f.read(2))[0]
        
        print(f"Размер карты: {ScreenWidth}x{ScreenHeight} экранов")
        print(f"Уникальных экранов: {ScreenCount}")
        print(f"Флаги экрана: 0x{ScreenFlags:04X}")
        
        # Читаем дополнительные поля заголовка
        if LYRFormat == 0:
            ScreenUnkA = struct.unpack('<H', f.read(2))[0]
            ScreenTypesID = struct.unpack('<H', f.read(2))[0]
            ScreenTilesetID = struct.unpack('<H', f.read(2))[0]
            ScreenUnkD = struct.unpack('<H', f.read(2))[0]
        elif LYRFormat == 1:
            ScreenUnkA = struct.unpack('<H', f.read(2))[0]
            ScreenTypesID = struct.unpack('<H', f.read(2))[0]
            ScreenUnkC = struct.unpack('<H', f.read(2))[0]
            ScreenTilesetID = struct.unpack('<H', f.read(2))[0]
        else:
            ScreenUnkCountA = struct.unpack('<H', f.read(2))[0]
            ScreenUnkCountB = struct.unpack('<H', f.read(2))[0]
            ScreenUnkCountC = struct.unpack('<H', f.read(2))[0]
            ScreenTypesID = struct.unpack('<H', f.read(2))[0]
            ScreenUnkIDB = struct.unpack('<H', f.read(2))[0]
            ScreenTilesetID = struct.unpack('<H', f.read(2))[0]
        
        # Читаем индексы экранов (какой экран где на карте)
        screen_map = []
        for x in range(ScreenWidth * ScreenHeight):
            screen_id = struct.unpack('<H', f.read(2))[0]
            screen_map.append(screen_id)
        
        # Выравнивание для формата 0
        if LYRFormat == 0:
            if f.tell() % 4 != 0:
                f.read(2)
        
        # Дополнительные данные для формата 3+
        if LYRFormat > 2:
            # Пропускаем дополнительные блоки
            for x in range(ScreenWidth * ScreenHeight):
                struct.unpack('<H', f.read(2))[0]
            for x in range(ScreenWidth * ScreenHeight):
                struct.unpack('<H', f.read(2))[0]
            f.seek((ScreenUnkCountA * 20), 1)
            f.seek((ScreenUnkCountB * 8), 1)
            f.seek((ScreenUnkCountC * 16), 1)
        
        # Анализируем данные экранов
        metatile_usage = {}  # metatile_id -> [(screen_id, position), ...]
        screen_data = []     # Данные каждого экрана
        
        print(f"Анализирую экраны...")
        
        for screen_id in range(ScreenCount):
            screen_metatiles = []
            
            # Читаем 256 метатайлов для этого экрана (16x16)
            for pos in range(256):
                metatile_raw = struct.unpack('<H', f.read(2))[0]
                
                # Применяем маски как в оригинале
                if ScreenFlags == 0x0010 or ScreenFlags == 0x0020:
                    metatile_id = metatile_raw & 0x03FF
                elif ScreenFlags == 0x0040:
                    metatile_id = metatile_raw & 0x0FFF
                else:
                    metatile_id = metatile_raw & 0x07FF
                
                screen_metatiles.append({
                    'metatile_id': metatile_id,
                    'raw_value': metatile_raw,
                    'position': pos
                })
                
                # Записываем использование метатайла
                if metatile_id not in metatile_usage:
                    metatile_usage[metatile_id] = []
                
                metatile_usage[metatile_id].append({
                    'screen_id': screen_id,
                    'position': pos,
                    'x': pos % 16,
                    'y': pos // 16
                })
            
            screen_data.append(screen_metatiles)
    
    # Анализируем статистику
    used_metatiles = set(metatile_usage.keys())
    unused_metatiles = set(range(max_metatiles)) - used_metatiles
    
    print()
    print(f"=== Статистика использования метатайлов ===")
    print(f"Всего метатайлов в листе: {max_metatiles}")
    print(f"Используется в LYR: {len(used_metatiles)}")
    print(f"Не используется: {len(unused_metatiles)}")
    
    # Показываем самые используемые метатайлы
    usage_count = [(mt_id, len(usage)) for mt_id, usage in metatile_usage.items()]
    usage_count.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nТоп-10 самых используемых метатайлов:")
    for i, (mt_id, count) in enumerate(usage_count[:10]):
        pos_x = (mt_id % 16) * 16
        pos_y = (mt_id // 16) * 16
        print(f"  {i+1:2}. ID {mt_id:3} (позиция {pos_x:3},{pos_y:3}) - использован {count:4} раз")
    
    return {
        'lyr_info': {
            'screen_width': ScreenWidth,
            'screen_height': ScreenHeight, 
            'screen_count': ScreenCount,
            'screen_flags': ScreenFlags,
            'format': LYRFormat
        },
        'metatiles_info': {
            'max_count': max_metatiles,
            'sheet_size': (mt_width, mt_height)
        },
        'screen_map': screen_map,
        'screen_data': screen_data,
        'metatile_usage': metatile_usage,
        'statistics': {
            'used_metatiles': len(used_metatiles),
            'unused_metatiles': len(unused_metatiles),
            'usage_ranking': usage_count
        }
    }

def create_metatile_coordinate_map(metatiles_path):
    """Создает карту координат метатайлов в листе"""
    
    if not os.path.exists(metatiles_path):
        return None
    
    img = Image.open(metatiles_path)
    width, height = img.size
    
    metatiles_x = width // 16
    metatiles_y = height // 16
    
    coord_map = {}
    
    for my in range(metatiles_y):
        for mx in range(metatiles_x):
            metatile_id = my * metatiles_x + mx
            coord_map[metatile_id] = {
                'id': metatile_id,
                'x': mx * 16,
                'y': my * 16,
                'grid_x': mx,
                'grid_y': my
            }
    
    return coord_map

def save_analysis_files(analysis_data, coord_map, base_name):
    """Сохраняет файлы с результатами анализа"""
    
    if not CreateDataFiles:
        return
    
    # Основной файл анализа
    analysis_file = f"{base_name}_analysis.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
    print(f"Анализ сохранен: {analysis_file}")
    
    # Карта координат метатайлов
    if coord_map:
        coord_file = f"{base_name}_coordinates.json"
        with open(coord_file, 'w', encoding='utf-8') as f:
            json.dump(coord_map, f, indent=2, ensure_ascii=False)
        print(f"Координаты сохранены: {coord_file}")
    
    # Упрощенный файл использования
    usage_file = f"{base_name}_usage.txt"
    with open(usage_file, 'w', encoding='utf-8') as f:
        f.write(f"=== Использование метатайлов в {base_name}.lyr ===\n\n")
        
        metatile_usage = analysis_data['metatile_usage']
        usage_ranking = analysis_data['statistics']['usage_ranking']
        
        f.write("ID | Позиция   | Использований | Экраны\n")
        f.write("---|-----------|---------------|--------\n")
        
        for mt_id, count in usage_ranking:
            pos_x = (mt_id % 16) * 16
            pos_y = (mt_id // 16) * 16
            
            screens = set()
            for usage in metatile_usage[mt_id]:
                screens.add(usage['screen_id'])
            
            screens_str = ','.join(map(str, sorted(screens)))
            if len(screens_str) > 30:
                screens_str = screens_str[:27] + "..."
                
            f.write(f"{mt_id:3} | ({pos_x:3},{pos_y:3}) | {count:13} | {screens_str}\n")
    
    print(f"Отчет сохранен: {usage_file}")

def main():
    print("=== Анализатор LYR файлов WayForward ===")
    print(f"LYR файл: {ScreenName}.lyr")
    print(f"Метатайлы: {MetatilesName}_metatile.png")
    print(f"LYR формат: {LYRFormat}")
    print()
    
    # Анализируем LYR файл
    lyr_file = f"{ScreenName}.lyr"
    metatiles_file = f"{MetatilesName}_metatile.png"
    
    analysis_data = analyze_metatile_usage(lyr_file, metatiles_file)
    if analysis_data is None:
        return
    
    # Создаем карту координат
    coord_map = create_metatile_coordinate_map(metatiles_file)
    
    # Сохраняем файлы
    save_analysis_files(analysis_data, coord_map, ScreenName)
    
    print()
    print("=== Результаты анализа ===")
    print("Теперь вы можете:")
    print("1. Просмотреть файлы *_analysis.json, *_coordinates.json, *_usage.txt")
    print("2. Отредактировать STATUS_metatile.png")  
    print("3. Использовать данные для обновления LYR файла")
    print()
    print("ВАЖНО: Если вы переставите метатайлы в STATUS_metatile.png,")
    print("       ID метатайлов изменятся и LYR файл нужно будет обновить!")

if __name__ == "__main__":
    main()
