#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import struct
from PIL import Image

# WayForward LYR упаковщик - создает LYR файлы из PNG карт
# Обратная операция для WayForward_LYR-Extract.py

LYRFormat = 2  # Формат как в распаковщике
ScreenName = "STATUS"  # Имя выходного LYR файла (без расширения)
MapPNG = "STATUS/Full.png"  # Входной PNG файл полной карты
MetatilePNG = "STATUS_metatile.png"  # PNG файл с метатайлами
TilesetID = 1  # ID тайлсета для записи в заголовок

def load_metatiles(metatile_path):
    """Загружает метатайлы из PNG и создает словарь для поиска"""
    
    if not os.path.exists(metatile_path):
        print(f"Не найден файл метатайлов: {metatile_path}")
        return None
    
    img = Image.open(metatile_path)
    width, height = img.size
    
    # Вычисляем количество метатайлов (каждый 16x16)
    metatiles_x = width // 16
    metatiles_y = height // 16
    
    print(f"Загружено метатайлов: {metatiles_x}x{metatiles_y} = {metatiles_x * metatiles_y}")
    
    # Извлекаем все метатайлы
    metatiles = {}  # hash -> metatile_id
    metatile_id = 0
    
    for my in range(metatiles_y):
        for mx in range(metatiles_x):
            # Извлекаем метатайл 16x16
            left = mx * 16
            top = my * 16
            metatile_img = img.crop((left, top, left + 16, top + 16))
            
            # Создаем хеш из пикселей для поиска
            if metatile_img.mode != 'RGB':
                metatile_img = metatile_img.convert('RGB')
            
            pixels = tuple(metatile_img.getdata())
            metatiles[pixels] = metatile_id
            metatile_id += 1
    
    return metatiles, img

def find_metatile_id(metatile_img, metatiles_dict):
    """Находит ID метатайла в словаре"""
    
    if metatile_img.mode != 'RGB':
        metatile_img = metatile_img.convert('RGB')
    
    pixels = tuple(metatile_img.getdata())
    
    if pixels in metatiles_dict:
        return metatiles_dict[pixels]
    
    # Если не найден, возвращаем 0 (пустой метатайл)
    return 0

def process_map_image(map_path, metatiles_dict, metatiles_img):
    """Обрабатывает PNG карту и извлекает экраны"""
    
    if not os.path.exists(map_path):
        print(f"Не найден файл карты: {map_path}")
        return None, None, None, None
    
    map_img = Image.open(map_path)
    map_width, map_height = map_img.size
    
    # Вычисляем размеры карты в экранах (каждый экран 256x256)
    screens_wide = map_width // 256
    screens_tall = map_height // 256
    
    if map_width % 256 != 0 or map_height % 256 != 0:
        print(f"ВНИМАНИЕ: Размер карты {map_width}x{map_height} не кратен 256!")
        print(f"Будет обрезана до {screens_wide * 256}x{screens_tall * 256}")
    
    print(f"Карта: {map_width}x{map_height} пикселей")
    print(f"Экранов: {screens_wide}x{screens_tall} = {screens_wide * screens_tall}")
    
    # Извлекаем все экраны и ищем уникальные
    screen_map = []  # Какой экран в какой позиции карты
    unique_screens = {}  # hash -> screen_id
    screen_data = []  # Данные уникальных экранов (метатайлы)
    
    for sy in range(screens_tall):
        for sx in range(screens_wide):
            # Извлекаем экран 256x256
            left = sx * 256
            top = sy * 256
            screen_img = map_img.crop((left, top, left + 256, top + 256))
            
            # Разбиваем экран на метатайлы 16x16
            screen_metatiles = []
            
            for my in range(16):  # 256/16 = 16 метатайлов по вертикали
                for mx in range(16):  # 256/16 = 16 метатайлов по горизонтали
                    # Извлекаем метатайл 16x16
                    meta_left = mx * 16
                    meta_top = my * 16
                    metatile_img = screen_img.crop((meta_left, meta_top, meta_left + 16, meta_top + 16))
                    
                    # Находим ID метатайла
                    metatile_id = find_metatile_id(metatile_img, metatiles_dict)
                    screen_metatiles.append(metatile_id)
            
            # Проверяем, есть ли уже такой экран
            screen_hash = tuple(screen_metatiles)
            
            if screen_hash in unique_screens:
                screen_id = unique_screens[screen_hash]
            else:
                screen_id = len(screen_data)
                unique_screens[screen_hash] = screen_id
                screen_data.append(screen_metatiles)
            
            screen_map.append(screen_id)
    
    print(f"Уникальных экранов: {len(screen_data)}")
    
    return screens_wide, screens_tall, screen_map, screen_data

def write_lyr_file(output_path, screens_wide, screens_tall, screen_map, screen_data):
    """Записывает LYR файл"""
    
    screen_count = len(screen_data)
    
    print(f"Записываем LYR: {screens_wide}x{screens_tall} экранов, {screen_count} уникальных")
    
    with open(output_path, 'wb') as f:
        # Заголовок
        screen_flags = 0x0010  # Базовые флаги
        
        f.write(struct.pack('<H', screen_flags))   # ScreenFlags
        f.write(struct.pack('<H', screens_wide))   # ScreenWidth  
        f.write(struct.pack('<H', screens_tall))   # ScreenHeight
        f.write(struct.pack('<H', screen_count))   # ScreenCount
        
        # Дополнительные поля заголовка в зависимости от формата
        if LYRFormat == 0:
            f.write(struct.pack('<H', 0))        # ScreenUnkA
            f.write(struct.pack('<H', 0))        # ScreenTypesID  
            f.write(struct.pack('<H', TilesetID)) # ScreenTilesetID
            f.write(struct.pack('<H', 0xCCCC))   # ScreenUnkD
        elif LYRFormat == 1:
            f.write(struct.pack('<H', 0))        # ScreenUnkA
            f.write(struct.pack('<H', 0))        # ScreenTypesID
            f.write(struct.pack('<H', 0))        # ScreenUnkC
            f.write(struct.pack('<H', TilesetID)) # ScreenTilesetID
        else:  # LYRFormat >= 2
            f.write(struct.pack('<H', 0))        # ScreenUnkCountA
            f.write(struct.pack('<H', 0))        # ScreenUnkCountB
            f.write(struct.pack('<H', 0))        # ScreenUnkCountC
            f.write(struct.pack('<H', 0))        # ScreenTypesID
            f.write(struct.pack('<H', 0))        # ScreenUnkIDB
            f.write(struct.pack('<H', TilesetID)) # ScreenTilesetID
        
        # Карта экранов (индексы того, какой экран в какой позиции)
        for screen_id in screen_map:
            f.write(struct.pack('<H', screen_id))
        
        # Выравнивание для формата 0
        if LYRFormat == 0:
            if f.tell() % 4 != 0:
                f.write(struct.pack('<H', 0))  # Дополнительные 2 байта для выравнивания
        
        # Дополнительные данные для формата 3+
        if LYRFormat > 2:
            # Вторичные и третичные индексы (пока заполняем нулями)
            for _ in range(screens_wide * screens_tall):
                f.write(struct.pack('<H', 0))  # ScreenID2
            
            for _ in range(screens_wide * screens_tall):
                f.write(struct.pack('<H', 0))  # ScreenID3
            
            # Блоки неизвестных данных (пропускаем, так как счетчики = 0)
        
        # Данные экранов (метатайлы для каждого уникального экрана)
        for screen_metatiles in screen_data:
            for metatile_id in screen_metatiles:  # 256 метатайлов на экран (16x16)
                # Применяем маску в зависимости от флагов
                if screen_flags == 0x0010 or screen_flags == 0x0020:
                    masked_id = metatile_id & 0x03FF  # 1024 метатайла максимум
                elif screen_flags == 0x0040:
                    masked_id = metatile_id & 0x0FFF  # 4096 метатайлов максимум
                else:
                    masked_id = metatile_id & 0x07FF  # 2048 метатайлов максимум
                
                f.write(struct.pack('<H', masked_id))

def main():
    print("=== WayForward LYR упаковщик ===")
    print(f"Карта: {MapPNG}")
    print(f"Метатайлы: {MetatilePNG}")
    print(f"Выходной файл: {ScreenName}.lyr")
    print(f"Формат: LYRFormat = {LYRFormat}")
    print()
    
    # Загружаем метатайлы
    metatiles_result = load_metatiles(MetatilePNG)
    if metatiles_result is None:
        return
    
    metatiles_dict, metatiles_img = metatiles_result
    
    # Обрабатываем карту
    result = process_map_image(MapPNG, metatiles_dict, metatiles_img)
    if result[0] is None:
        return
    
    screens_wide, screens_tall, screen_map, screen_data = result
    
    # Записываем LYR файл
    output_path = ScreenName + '.lyr'
    write_lyr_file(output_path, screens_wide, screens_tall, screen_map, screen_data)
    
    print(f"Упаковка завершена: {output_path}")
    print(f"Размер карты: {screens_wide}x{screens_tall} экранов")
    print(f"Уникальных экранов: {len(screen_data)}")
    
    # Статистика сжатия
    total_screens = screens_wide * screens_tall
    compression_ratio = (1.0 - len(screen_data) / total_screens) * 100 if total_screens > 0 else 0
    print(f"Сжатие: {compression_ratio:.1f}% ({total_screens} -> {len(screen_data)} экранов)")

if __name__ == "__main__":
    main()
