#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import struct
import argparse
from PIL import Image

# WayForward TS4/TS8 упаковщик - создает TS4 файлы из PNG метатайлов
# Обратная операция для WayForward_TS-Extract.py

# Значения по умолчанию (могут быть переопределены аргументами командной строки)
TSFormat = 1
TilesetName = "STATUS"
MetatilePNG = "STATUS_metatile.png"
PaletteName = "STATUS"
Use256Colors = False
RawPalette = True

def extract_tiles_from_metatile_png(png_path, forced_metatile_count=None):
    """Извлекает отдельные 8x8 тайлы из PNG метатайлов"""
    
    if not os.path.exists(png_path):
        print(f"Не найден файл: {png_path}")
        return None, None, None
    
    # Загружаем PNG
    img = Image.open(png_path)
    
    # Конвертируем в палитровый режим если нужно
    if img.mode != 'P':
        # Для простоты используем 256-цветную палитру
        img = img.convert('P', palette=Image.ADAPTIVE, colors=256)
    
    width, height = img.size
    
    # Вычисляем количество метатайлов (каждый 16x16)
    metatiles_x = width // 16
    metatiles_y = height // 16
    metatile_count_from_image = metatiles_x * metatiles_y
    
    # Используем принудительное значение если указано
    if forced_metatile_count is not None:
        metatile_count = forced_metatile_count
        print(f"Размер изображения: {width}x{height}")
        print(f"Метатайлов на изображении: {metatile_count_from_image} ({metatiles_x}x{metatiles_y})")
        print(f"Используется указанное количество: {metatile_count}")
        
        if metatile_count > metatile_count_from_image:
            print(f"ВНИМАНИЕ: Указано больше метатайлов ({metatile_count}) чем есть на изображении ({metatile_count_from_image})")
            print(f"Будет использовано: {metatile_count_from_image}")
            metatile_count = metatile_count_from_image
    else:
        metatile_count = metatile_count_from_image
        print(f"Размер изображения: {width}x{height}")
        print(f"Метатайлов: {metatile_count} ({metatiles_x}x{metatiles_y})")
    
    # Извлекаем палитру
    if img.mode == 'P':
        palette_data = img.getpalette()
        if palette_data:
            # Конвертируем RGB палитру в формат игры (RGB555)
            palette = []
            for i in range(0, min(len(palette_data), 768), 3):  # 256 цветов * 3 компонента
                r = palette_data[i] if i < len(palette_data) else 0
                g = palette_data[i+1] if i+1 < len(palette_data) else 0  
                b = palette_data[i+2] if i+2 < len(palette_data) else 0
                
                # Конвертируем в RGB555 (5 бит на компонент)
                r5 = r >> 3
                g5 = g >> 3  
                b5 = b >> 3
                
                if RawPalette:
                    # "Сырые" значения (умножаем на 8)
                    palette.extend([r5 * 8, g5 * 8, b5 * 8])
                else:
                    # Нормализованные значения (0-255)
                    r_norm = r5 * 8 + (r5 * 8 + 1) // 32
                    g_norm = g5 * 8 + (g5 * 8 + 1) // 32  
                    b_norm = b5 * 8 + (b5 * 8 + 1) // 32
                    palette.extend([r_norm, g_norm, b_norm])
            
            # Дополняем палитру до 256 цветов
            while len(palette) < 768:
                palette.extend([0, 0, 0])
        else:
            # Создаем серую палитру по умолчанию
            palette = []
            for i in range(256):
                palette.extend([i, i, i])
    else:
        # Создаем серую палитру по умолчанию
        palette = []
        for i in range(256):
            palette.extend([i, i, i])
    
    # Извлекаем метатайлы и разбиваем их на 8x8 тайлы
    metatile_data = []  # Данные о составе метатайлов (4 тайла на метатайл)
    tile_data = []      # Пиксельные данные тайлов 8x8
    tile_dict = {}      # Словарь для поиска дубликатов тайлов
    
    processed_count = 0
    for my in range(metatiles_y):
        for mx in range(metatiles_x):
            # Проверяем не превысили ли мы нужное количество
            if processed_count >= metatile_count:
                break
            
            # Извлекаем метатайл 16x16
            metatile_x = mx * 16
            metatile_y = my * 16
            
            metatile_tiles = []  # 4 тайла для этого метатайла
            
            # Каждый метатайл состоит из 4 тайлов 8x8 (верхний-левый, верхний-правый, нижний-левый, нижний-правый)
            for ty in range(2):
                for tx in range(2):
                    tile_x = metatile_x + tx * 8
                    tile_y = metatile_y + ty * 8
                    
                    # Извлекаем тайл 8x8
                    tile_img = img.crop((tile_x, tile_y, tile_x + 8, tile_y + 8))
                    
                    # Конвертируем пиксели в индексы палитры  
                    if tile_img.mode != 'P':
                        tile_img = tile_img.convert('P', palette=Image.ADAPTIVE, colors=256)
                    
                    tile_pixels = list(tile_img.getdata())
                    
                    # Проверяем, есть ли уже такой тайл (для оптимизации)
                    tile_hash = tuple(tile_pixels)
                    if tile_hash in tile_dict:
                        tile_id = tile_dict[tile_hash]
                    else:
                        tile_id = len(tile_data)
                        tile_dict[tile_hash] = tile_id
                        tile_data.append(tile_pixels)
                    
                    # Добавляем информацию о тайле в метатайл (ID, флаги поворота, палитра)
                    metatile_tiles.append({
                        'tile_id': tile_id,
                        'flip': 0,  # Пока без поворотов
                        'palette': 0  # Первая палитра
                    })
            
            metatile_data.append(metatile_tiles)
            processed_count += 1
        
        # Выход из внешнего цикла если достигли нужного количества
        if processed_count >= metatile_count:
            break
    
    print(f"Обработано метатайлов: {processed_count}")
    print(f"Извлечено уникальных тайлов: {len(tile_data)}")
    
    return metatile_data, tile_data, palette

def write_ts4_file(output_path, metatile_data, tile_data, palette):
    """Записывает TS4 файл"""
    
    metatile_count = len(metatile_data)
    tile_count = len(tile_data)
    
    print(f"Записываем TS4: {metatile_count} метатайлов, {tile_count} тайлов")
    
    with open(output_path, 'wb') as f:
        # Заголовок
        tileset_flags = 0x0001 if Use256Colors else 0x0000
        f.write(struct.pack('<H', tileset_flags))  # TilesetFlags
        f.write(struct.pack('<H', metatile_count)) # MetatileCount  
        f.write(struct.pack('<H', tile_count))     # TileCount
        
        if TSFormat > 0:
            f.write(struct.pack('<H', 0))  # MetatileUnk
        
        # Данные метатайлов
        for metatile in metatile_data:
            for tile_info in metatile:  # 4 тайла на метатайл
                if TSFormat == 2 or TSFormat == 3:
                    # 4-байтовый формат для DS/Didj
                    tile_id = tile_info['tile_id']
                    tile_flip = tile_info['flip'] << 26  
                    tile_palette = tile_info['palette'] << 24
                    metatile_flags = tile_id | tile_flip | tile_palette
                    f.write(struct.pack('<L', metatile_flags))
                elif TSFormat == 4:
                    # Leapster формат - только ID тайла (флаги отдельно)
                    f.write(struct.pack('<H', tile_info['tile_id']))
                else:
                    # 2-байтовый формат для GBA
                    tile_id = tile_info['tile_id'] & 0x03FF
                    tile_flip = (tile_info['flip'] & 0x03) << 10
                    tile_palette = (tile_info['palette'] & 0x0F) << 8
                    metatile_flags = tile_id | tile_flip | tile_palette  
                    f.write(struct.pack('<H', metatile_flags))
        
        # Дополнительные данные для Leapster (флаги поворота)
        if TSFormat == 4:
            for metatile in metatile_data:
                for tile_info in metatile:
                    flip_byte = (tile_info['flip'] & 0x03) << 2
                    f.write(struct.pack('<B', flip_byte))
        
        # Данные тайлов
        for tile_pixels in tile_data:
            if Use256Colors:
                if TSFormat == 4:
                    # Leapster ARGB4444 (2 байта на пиксель) 
                    for pixel in tile_pixels:
                        # Простое преобразование индекса в ARGB4444
                        alpha = 0xF  # Непрозрачный
                        r = (pixel >> 5) & 0x7  # 3 бита красного
                        g = (pixel >> 2) & 0x7  # 3 бита зеленого
                        b = pixel & 0x3          # 2 бита синего
                        argb = (alpha << 12) | (r << 8) | (g << 4) | b
                        f.write(struct.pack('<H', argb))
                else:
                    # 256-цветный формат (1 байт на пиксель)
                    for pixel in tile_pixels:
                        f.write(struct.pack('<B', pixel))
            else:
                # 16-цветный формат (4 бита на пиксель, 2 пикселя в байте)
                for i in range(0, 64, 2):  # 64 пикселя в тайле, по 2 за раз
                    pixel1 = tile_pixels[i] & 0x0F
                    pixel2 = tile_pixels[i+1] & 0x0F if i+1 < 64 else 0
                    byte_val = pixel1 | (pixel2 << 4)
                    f.write(struct.pack('<B', byte_val))

def write_palette_file(output_path, palette):
    """Записывает палитру в PAL файл"""
    
    with open(output_path, 'wb') as f:
        # Конвертируем RGB палитру в RGB555 формат
        for i in range(0, len(palette), 3):
            r = palette[i] if i < len(palette) else 0
            g = palette[i+1] if i+1 < len(palette) else 0
            b = palette[i+2] if i+2 < len(palette) else 0
            
            # Конвертируем в 5-битные значения
            if RawPalette:
                r5 = r // 8
                g5 = g // 8
                b5 = b // 8
            else:
                # Обратное преобразование из нормализованных значений
                r5 = min(31, r // 8)
                g5 = min(31, g // 8) 
                b5 = min(31, b // 8)
            
            # Упаковываем в RGB555 формат (15 бит)
            rgb555 = (b5 << 10) | (g5 << 5) | r5
            f.write(struct.pack('<H', rgb555))

def auto_int(x):
    """Конвертирует строку в int, поддерживает десятичные и шестнадцатеричные (0x) значения"""
    return int(x, 0)

def parse_arguments():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(
        description='WayForward TS4/TS8 упаковщик метатайлов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  tool.exe STATUS_metatile.png
  tool.exe LEVEL2_metatile.png --output LEVEL2 --format 2
  tool.exe texture.png --output MYTEX --format 1 --palette MYTEX
  tool.exe STATUS_metatile.png --metatile-count 257
  tool.exe STATUS_metatile.png --metatile-count 0x101
        '''
    )
    
    parser.add_argument('input', nargs='?', default=MetatilePNG,
                        help='Входной PNG файл с метатайлами (по умолчанию: STATUS_metatile.png)')
    parser.add_argument('--output', '-o', default=None,
                        help='Имя выходного TS4 файла без расширения (по умолчанию: имя входного файла)')
    parser.add_argument('--format', '-f', type=int, default=TSFormat,
                        help='Формат TS (0-4, по умолчанию: 1)')
    parser.add_argument('--palette', '-p', default=None,
                        help='Имя палитры SCN/PAL (по умолчанию: имя выходного файла)')
    parser.add_argument('--ts8', action='store_true',
                        help='Создать TS8 (256 цветов) вместо TS4 (16 цветов)')
    parser.add_argument('--metatile-count', type=auto_int, default=None,
                        help='Точное количество метатайлов (поддерживает 0x для hex). Если не указано, определяется по размеру PNG')
    parser.add_argument('--raw-palette', action='store_true', default=RawPalette,
                        help='Использовать сырые значения палитры')
    parser.add_argument('--no-raw-palette', dest='raw_palette', action='store_false',
                        help='Нормализовать значения палитры')
    
    args = parser.parse_args()
    
    return args

def main():
    # Парсим аргументы командной строки
    args = parse_arguments()
    
    # Применяем аргументы
    metatile_png = args.input
    
    # Если не указан выходной файл, используем имя входного без _metatile
    if args.output:
        tileset_name = args.output
    else:
        # Убираем расширение и суффикс _metatile
        base_name = os.path.splitext(os.path.basename(metatile_png))[0]
        if base_name.endswith('_metatile'):
            tileset_name = base_name[:-9]  # Убираем "_metatile"
        else:
            tileset_name = base_name
    
    ts_format = args.format
    palette_name = args.palette if args.palette else tileset_name
    use_256_colors = args.ts8
    raw_palette = args.raw_palette
    forced_metatile_count = args.metatile_count
    
    # Проверяем наличие входного файла
    if not os.path.exists(metatile_png):
        print(f"Не найден входной PNG файл: {metatile_png}")
        print("Убедитесь, что файл существует и укажите правильный путь")
        return
    
    print("=== WayForward TS4 упаковщик ===")
    print(f"Входной файл: {metatile_png}")
    print(f"Выходной файл: {tileset_name}.ts{'8' if use_256_colors else '4'}")
    print(f"Формат: TSFormat = {ts_format}")
    print(f"Цвета: {'256' if use_256_colors else '16'}")
    if forced_metatile_count:
        print(f"Указано количество метатайлов: {forced_metatile_count}")
    print()
    
    # Извлекаем данные из PNG
    metatile_data, tile_data, palette = extract_tiles_from_metatile_png(metatile_png, forced_metatile_count)
    
    if metatile_data is None:
        return
    
    # Записываем TS4 файл
    output_ext = '.ts8' if use_256_colors else '.ts4'
    output_path = tileset_name + output_ext
    
    # Временно устанавливаем глобальные переменные для функций записи
    global TSFormat, Use256Colors, RawPalette
    TSFormat = ts_format
    Use256Colors = use_256_colors
    RawPalette = raw_palette
    
    write_ts4_file(output_path, metatile_data, tile_data, palette)
    
    # Записываем палитру если нужно
    if palette_name and ts_format != 4:  # Leapster не использует отдельные палитры
        palette_path = palette_name + '.pal'
        write_palette_file(palette_path, palette)
        print(f"Палитра сохранена: {palette_path}")
    
    print(f"Упаковка завершена: {output_path}")
    print(f"Метатайлов: {len(metatile_data)}")
    print(f"Уникальных тайлов: {len(tile_data)}")

if __name__ == "__main__":
    main()
