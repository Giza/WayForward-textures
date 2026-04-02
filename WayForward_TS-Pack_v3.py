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

def get_tile_flipped(tile_pixels, flip_type):
    """Возвращает перевёрнутую версию 8x8 тайла.
    flip_type: 0=нет, 1=горизонтально, 2=вертикально, 3=оба
    """
    rows = [tile_pixels[i*8:(i+1)*8] for i in range(8)]
    if flip_type == 1:
        rows = [list(reversed(row)) for row in rows]
    elif flip_type == 2:
        rows = list(reversed(rows))
    elif flip_type == 3:
        rows = [list(reversed(row)) for row in reversed(rows)]
    return tuple(p for row in rows for p in row)

def load_scene_palette(scene_name, raw_palette=True):
    """Загружает палитру из PAL/SCN файла.
    Возвращает список (R,G,B) кортежей для 256 записей.
    """
    pal_path = None
    if os.path.exists(scene_name + ".pal"):
        pal_path = scene_name + ".pal"
    elif os.path.exists(scene_name + ".scn"):
        pal_path = scene_name + ".scn"
    else:
        return None
    
    palette_rgb = []
    with open(pal_path, "rb") as f:
        for i in range(256):
            val = struct.unpack('<H', f.read(2))[0]
            r = ((val & 0x001F)) * 8
            g = ((val & 0x03E0) >> 5) * 8
            b = ((val & 0x7C00) >> 10) * 8
            if not raw_palette:
                r = r + (r + 1) // 32
                g = g + (g + 1) // 32
                b = b + (b + 1) // 32
            palette_rgb.append((r, g, b))
    
    return palette_rgb

def match_pixels_to_subpalette(tile_rgb_pixels, palette_rgb, hint_palette_row=None):
    """Сопоставляет RGB пиксели тайла 8x8 с правильной суб-палитрой.
    
    Для 16-цветного режима определяет, какая суб-палитра лучше подходит
    для всего тайла, затем сопоставляет каждый пиксель с ближайшим цветом
    в этой суб-палитре.
    
    hint_palette_row: подсказка от соседних тайлов в том же метатайле.
    Если указана и все пиксели можно разместить в этой суб-палитре — используется она.
    
    Возвращает (palette_row, low_nibble_pixels).
    """
    # Шаг 1: Для каждого пикселя найти ближайший индекс в полной палитре
    pixel_best_indices = []
    for r, g, b in tile_rgb_pixels:
        best_idx = 0
        best_dist = float('inf')
        for idx, (pr, pg, pb) in enumerate(palette_rgb):
            dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        pixel_best_indices.append(best_idx)
    
    # Шаг 2: Определить суб-палитру
    # Собираем кандидатов: для каждого ненулевого пикселя — все суб-палитры, 
    # которые содержат (точно или приближённо) его цвет
    subpal_scores = {}
    for i, (r, g, b) in enumerate(tile_rgb_pixels):
        idx = pixel_best_indices[i]
        if idx == 0 or (r, g, b) == palette_rgb[0]:
            continue  # Прозрачный пиксель
        
        # Для каждой суб-палитры: найти расстояние до ближайшего цвета
        for sp in range(16):
            sp_offset = sp * 16
            best_sp_dist = float('inf')
            for c in range(1, 16):  # Пропускаем прозрачный слот 0
                if sp_offset + c < len(palette_rgb):
                    pr, pg, pb = palette_rgb[sp_offset + c]
                    dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
                    if dist < best_sp_dist:
                        best_sp_dist = dist
            
            if best_sp_dist == 0:  # Точное совпадение
                subpal_scores[sp] = subpal_scores.get(sp, 0) + 2
            elif best_sp_dist <= 64:  # Очень близко (ошибка округления)
                subpal_scores[sp] = subpal_scores.get(sp, 0) + 1
    
    if hint_palette_row is not None and hint_palette_row in subpal_scores:
        # Если есть подсказка и она имеет ненулевой score — используем её
        palette_row = hint_palette_row
    elif subpal_scores:
        palette_row = max(subpal_scores, key=subpal_scores.get)
    else:
        palette_row = 0  # Полностью прозрачный тайл
    
    # Шаг 3: Переназначить пиксели в выбранную суб-палитру
    subpal_offset = palette_row * 16
    subpal_colors = [(palette_rgb[subpal_offset + c] if subpal_offset + c < len(palette_rgb) else (0,0,0)) for c in range(16)]
    
    low_nibble_pixels = []
    for i, (r, g, b) in enumerate(tile_rgb_pixels):
        # Проверяем прозрачность (индекс 0 глобальный)
        if pixel_best_indices[i] == 0 or (r, g, b) == palette_rgb[0]:
            low_nibble_pixels.append(0)
            continue
        
        # Ищем ближайший цвет в выбранной суб-палитре (пропуская индекс 0 = прозрачность)
        best_nibble = 0
        best_dist = float('inf')
        for c in range(1, 16):  # Начинаем с 1, 0 = прозрачность
            pr, pg, pb = subpal_colors[c]
            dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if dist < best_dist:
                best_dist = dist
                best_nibble = c
        low_nibble_pixels.append(best_nibble)
    
    return palette_row, low_nibble_pixels

def extract_tiles_from_metatile_png(png_path, forced_metatile_count=None, scene_palette_rgb=None):
    """Извлекает отдельные 8x8 тайлы из PNG метатайлов"""
    
    if not os.path.exists(png_path):
        print(f"Не найден файл: {png_path}")
        return None, None, None
    
    # Загружаем PNG
    img = Image.open(png_path)
    
    # Подготовка изображений для обоих режимов
    if scene_palette_rgb and not Use256Colors:
        # Режим с scene-палитрой: работаем с RGB
        img_rgb = img.convert('RGB')
        # Для совместимости оставляем img в палитровом режиме для palette extraction
        if img.mode != 'P':
            img = img.convert('P', palette=Image.ADAPTIVE, colors=256)
        print("Используется палитра из scene-файла для сопоставления цветов")
    else:
        img_rgb = None
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
    tile_data = []      # Пиксельные данные тайлов 8x8 (для 16-цветных - только низкие нибблы 0-15)
    tile_dict = {}      # Словарь для поиска дубликатов тайлов (включая перевёрнутые)
    
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
            # Используем двухпроходный подход:
            # 1-й проход: обработать чистые тайлы (одна суб-палитра), определить подсказку
            # 2-й проход: обработать смешанные тайлы с подсказкой от чистых
            
            tile_positions = [(0,0), (1,0), (0,1), (1,1)]  # tx, ty
            tile_results = [None, None, None, None]  # результаты для 4 позиций
            pending_mixed = []  # индексы тайлов с смешанными суб-палитрами
            clean_palette_rows = []  # суб-палитры чистых тайлов (для подсказки)
            
            for ti, (tx, ty) in enumerate(tile_positions):
                tile_x = metatile_x + tx * 8
                tile_y = metatile_y + ty * 8
                
                # Извлекаем тайл 8x8
                tile_img = img.crop((tile_x, tile_y, tile_x + 8, tile_y + 8))
                
                # Конвертируем пиксели в индексы палитры  
                if tile_img.mode != 'P':
                    tile_img = tile_img.convert('P', palette=Image.ADAPTIVE, colors=256)
                
                tile_pixels = list(tile_img.getdata())
                
                if Use256Colors:
                    # 256-цветный режим: палитра не разделяется на суб-палитры
                    tile_results[ti] = (tile_pixels, 0)
                else:
                    # 16-цветный режим: проверяем чистоту суб-палитры
                    sub_palettes_in_tile = set()
                    for p in tile_pixels:
                        if p != 0:
                            sub_palettes_in_tile.add(p >> 4)
                    
                    if len(sub_palettes_in_tile) <= 1:
                        # Чистый тайл
                        palette_row = sub_palettes_in_tile.pop() if sub_palettes_in_tile else 0
                        
                        tile_pixels_store = []
                        for p in tile_pixels:
                            if p == 0:
                                tile_pixels_store.append(0)
                            else:
                                tile_pixels_store.append(p & 0x0F)
                        
                        tile_results[ti] = (tile_pixels_store, palette_row)
                        clean_palette_rows.append(palette_row)
                    else:
                        # Смешанный тайл — отложить на 2-й проход
                        pending_mixed.append((ti, tile_x, tile_y, tile_pixels))
            
            # 2-й проход: обработать смешанные тайлы
            for ti, tile_x, tile_y, tile_pixels in pending_mixed:
                # Определяем подсказку от чистых соседей
                hint = None
                if clean_palette_rows:
                    # Берём наиболее часто встречающуюся суб-палитру среди чистых тайлов
                    from collections import Counter
                    hint = Counter(clean_palette_rows).most_common(1)[0][0]
                
                if scene_palette_rgb and img_rgb:
                    # Используем RGB matching с подсказкой
                    tile_img_rgb = img_rgb.crop((tile_x, tile_y, tile_x + 8, tile_y + 8))
                    tile_rgb_pixels = list(tile_img_rgb.getdata())
                    palette_row, tile_pixels_store = match_pixels_to_subpalette(tile_rgb_pixels, scene_palette_rgb, hint)
                    tile_results[ti] = (tile_pixels_store, palette_row)
                else:
                    # Без scene палитры — берём по первому ненулевому
                    palette_row = 0
                    for p in tile_pixels:
                        if p != 0:
                            palette_row = p >> 4
                            break
                    
                    tile_pixels_store = []
                    for p in tile_pixels:
                        if p == 0:
                            tile_pixels_store.append(0)
                        else:
                            tile_pixels_store.append(p & 0x0F)
                    
                    tile_results[ti] = (tile_pixels_store, palette_row)
            
            # Формируем результаты для всех 4 тайлов
            for ti in range(4):
                tile_pixels_store, tile_palette = tile_results[ti]
                
                # Проверяем дубликаты тайлов (включая перевёрнутые версии)
                tile_hash = tuple(tile_pixels_store)
                flip = 0
                
                if tile_hash in tile_dict:
                    tile_id = tile_dict[tile_hash]
                else:
                    # Проверяем перевёрнутые варианты
                    found_flip = False
                    for flip_type in [1, 2, 3]:
                        flipped = get_tile_flipped(tile_pixels_store, flip_type)
                        if flipped in tile_dict:
                            tile_id = tile_dict[flipped]
                            flip = flip_type
                            found_flip = True
                            break
                    
                    if not found_flip:
                        # Новый уникальный тайл
                        tile_id = len(tile_data)
                        tile_dict[tile_hash] = tile_id
                        tile_data.append(tile_pixels_store)
                
                # Добавляем информацию о тайле в метатайл
                metatile_tiles.append({
                    'tile_id': tile_id,
                    'flip': flip,
                    'palette': tile_palette  # palette_row (0-15) для 16-цветных
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
                    tile_palette = tile_info['palette'] << 28  # palette_row в биты 28-31
                    metatile_flags = tile_id | tile_flip | tile_palette
                    f.write(struct.pack('<L', metatile_flags))
                elif TSFormat == 4:
                    # Leapster формат - только ID тайла (флаги отдельно)
                    f.write(struct.pack('<H', tile_info['tile_id']))
                else:
                    # 2-байтовый формат для GBA
                    tile_id = tile_info['tile_id'] & 0x03FF
                    tile_flip = (tile_info['flip'] & 0x03) << 10
                    tile_palette = (tile_info['palette'] & 0x0F) << 12  # palette_row в биты 12-15
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
    parser.add_argument('--scene', '-s', default=None,
                        help='Имя SCN/PAL файла для палитры (для правильного сопоставления цветов отредактированных PNG)')
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
    scene_name = args.scene
    
    # Проверяем наличие входного файла
    if not os.path.exists(metatile_png):
        print(f"Не найден входной PNG файл: {metatile_png}")
        print("Убедитесь, что файл существует и укажите правильный путь")
        return
    
    # Загружаем палитру из scene-файла если указан
    scene_palette_rgb = None
    scene_palette_flat = None
    if scene_name:
        scene_palette_rgb = load_scene_palette(scene_name, raw_palette)
        if scene_palette_rgb:
            # Конвертируем в плоский список [R,G,B,R,G,B,...] для записи PAL файла
            scene_palette_flat = []
            for r, g, b in scene_palette_rgb:
                scene_palette_flat.extend([r, g, b])
            print(f"Загружена палитра из scene: {scene_name}")
        else:
            print(f"ВНИМАНИЕ: Не найден scene-файл '{scene_name}.scn' или '{scene_name}.pal'")
            print("Палитра будет извлечена из PNG (индексный режим)")
    
    print("=== WayForward TS4 упаковщик ===")
    print(f"Входной файл: {metatile_png}")
    print(f"Выходной файл: {tileset_name}.ts{'8' if use_256_colors else '4'}")
    print(f"Формат: TSFormat = {ts_format}")
    print(f"Цвета: {'256' if use_256_colors else '16'}")
    if forced_metatile_count:
        print(f"Указано количество метатайлов: {forced_metatile_count}")
    if scene_palette_rgb:
        print(f"Scene-палитра: {scene_name}")
    print()
    
    # Извлекаем данные из PNG
    metatile_data, tile_data, palette = extract_tiles_from_metatile_png(metatile_png, forced_metatile_count, scene_palette_rgb)
    
    # Если использовалась scene-палитра, заменяем палитру
    if scene_palette_flat:
        palette = scene_palette_flat
    
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
