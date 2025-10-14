#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import struct
import argparse
from PIL import Image

# Генератор метатайлов WayForward - ОБНОВЛЯЕТ оригинальный лист метатайлов
# Анализирует Full.png и обновляет соответствующие метатайлы в оригинальном листе
# Сохраняет неиспользуемые метатайлы на их оригинальных позициях

# Значения по умолчанию (могут быть переопределены аргументами командной строки)
MapPNG = "STATUS/Full.png"
OriginalMetatiles = "STATUS_metatile.png"
OutputMetatile = "STATUS_metatile_updated.png"
LYRFile = "STATUS.lyr"
LYRFormat = 2
TSFormat = 1

def read_used_metatile_ids_from_lyr(lyr_path):
    """Читает LYR файл и возвращает список всех используемых ID метатайлов"""
    
    if not os.path.exists(lyr_path):
        print(f"Не найден LYR файл: {lyr_path}")
        return None
    
    print(f"Анализируем используемые метатайлы в: {lyr_path}")
    
    used_metatile_ids = set()
    
    with open(lyr_path, 'rb') as f:
        # Читаем заголовок
        ScreenFlags = struct.unpack('<H', f.read(2))[0]
        ScreenWidth = struct.unpack('<H', f.read(2))[0]  
        ScreenHeight = struct.unpack('<H', f.read(2))[0]
        ScreenCount = struct.unpack('<H', f.read(2))[0]
        
        print(f"LYR: {ScreenWidth}x{ScreenHeight} экранов, {ScreenCount} уникальных")
        
        # Пропускаем дополнительные поля заголовка
        if LYRFormat == 0:
            f.read(8)  # 4 поля по 2 байта
        elif LYRFormat == 1:
            f.read(8)  # 4 поля по 2 байта
        else:
            f.read(12)  # 6 полей по 2 байта
        
        # Пропускаем карту экранов
        f.read(ScreenWidth * ScreenHeight * 2)
        
        # Выравнивание для формата 0
        if LYRFormat == 0:
            if f.tell() % 4 != 0:
                f.read(2)
        
        # Пропускаем дополнительные данные для формата 3+
        if LYRFormat > 2:
            f.read(ScreenWidth * ScreenHeight * 2)  # ScreenID2
            f.read(ScreenWidth * ScreenHeight * 2)  # ScreenID3
            # Неизвестные блоки пропускаем (счетчики в наших тестах = 0)
        
        # Читаем данные экранов и собираем используемые ID метатайлов
        for screen_id in range(ScreenCount):
            for pos in range(256):  # 16x16 метатайлов на экран
                metatile_raw = struct.unpack('<H', f.read(2))[0]
                
                # Извлекаем ID с учетом флагов
                if ScreenFlags == 0x0010 or ScreenFlags == 0x0020:
                    metatile_id = metatile_raw & 0x03FF
                elif ScreenFlags == 0x0040:
                    metatile_id = metatile_raw & 0x0FFF
                else:
                    metatile_id = metatile_raw & 0x07FF
                
                used_metatile_ids.add(metatile_id)
    
    print(f"Найдено используемых ID метатайлов: {len(used_metatile_ids)}")
    return sorted(list(used_metatile_ids))

def load_original_metatiles(metatiles_path):
    """Загружает оригинальный лист метатайлов и извлекает каждый метатайл"""
    
    if not os.path.exists(metatiles_path):
        print(f"Не найден оригинальный файл метатайлов: {metatiles_path}")
        return None, None
    
    print(f"Загружаем оригинальный лист: {metatiles_path}")
    
    original_img = Image.open(metatiles_path)
    width, height = original_img.size
    
    print(f"Размер листа: {width}x{height}, режим: {original_img.mode}")
    
    # Показываем информацию о палитре
    if original_img.mode == 'P':
        palette = original_img.getpalette()
        if palette:
            print(f"Палитра: {len(palette)//3} цветов")
        else:
            print("Палитра: отсутствует")
    
    # Извлекаем все метатайлы из оригинального листа
    metatiles_x = width // 16
    metatiles_y = height // 16
    
    original_metatiles = {}  # id -> PIL Image
    
    for my in range(metatiles_y):
        for mx in range(metatiles_x):
            metatile_id = my * metatiles_x + mx
            
            x = mx * 16
            y = my * 16
            
            metatile_img = original_img.crop((x, y, x + 16, y + 16))
            original_metatiles[metatile_id] = metatile_img.copy()
    
    print(f"Загружено {len(original_metatiles)} оригинальных метатайлов")
    
    return original_img, original_metatiles

def create_metatile_mapping_from_lyr_and_map(lyr_path, map_path, original_metatiles):
    """Создает сопоставление: используемые в LYR ID -> метатайлы из соответствующих позиций карты"""
    
    if not os.path.exists(map_path):
        print(f"Не найден файл карты: {map_path}")
        return None
    
    print(f"Создаем сопоставление LYR -> карта...")
    
    # Загружаем карту
    map_img = Image.open(map_path)
    map_width, map_height = map_img.size
    
    print(f"Размер карты: {map_width}x{map_height} пикселей")
    print(f"Режим карты: {map_img.mode}")
    
    # Проверяем размер
    if map_width % 16 != 0 or map_height % 16 != 0:
        print("ВНИМАНИЕ: Размер карты не кратен 16 пикселям!")
        map_width = (map_width // 16) * 16
        map_height = (map_height // 16) * 16
        map_img = map_img.crop((0, 0, map_width, map_height))
        print(f"Обрезано до: {map_width}x{map_height}")
    
    # Читаем LYR файл чтобы узнать как строится карта
    if not os.path.exists(lyr_path):
        print(f"Не найден LYR файл: {lyr_path}")
        return None
    
    screen_to_metatile_mapping = {}  # screen_id -> [256 metatile_ids]
    screen_map = []  # Какой экран где на карте
    
    with open(lyr_path, 'rb') as f:
        # Читаем заголовок
        ScreenFlags = struct.unpack('<H', f.read(2))[0]
        ScreenWidth = struct.unpack('<H', f.read(2))[0]  
        ScreenHeight = struct.unpack('<H', f.read(2))[0]
        ScreenCount = struct.unpack('<H', f.read(2))[0]
        
        # Пропускаем дополнительные поля заголовка
        if LYRFormat == 0:
            f.read(8)
        elif LYRFormat == 1:
            f.read(8)
        else:
            f.read(12)
        
        # Читаем карту экранов
        for i in range(ScreenWidth * ScreenHeight):
            screen_id = struct.unpack('<H', f.read(2))[0]
            screen_map.append(screen_id)
        
        # Выравнивание для формата 0
        if LYRFormat == 0:
            if f.tell() % 4 != 0:
                f.read(2)
        
        # Пропускаем дополнительные данные для формата 3+
        if LYRFormat > 2:
            f.read(ScreenWidth * ScreenHeight * 2)
            f.read(ScreenWidth * ScreenHeight * 2)
        
        # Читаем данные экранов
        for screen_id in range(ScreenCount):
            screen_metatiles = []
            for pos in range(256):
                metatile_raw = struct.unpack('<H', f.read(2))[0]
                
                # Извлекаем ID с учетом флагов
                if ScreenFlags == 0x0010 or ScreenFlags == 0x0020:
                    metatile_id = metatile_raw & 0x03FF
                elif ScreenFlags == 0x0040:
                    metatile_id = metatile_raw & 0x0FFF
                else:
                    metatile_id = metatile_raw & 0x07FF
                
                screen_metatiles.append(metatile_id)
            
            screen_to_metatile_mapping[screen_id] = screen_metatiles
    
    # Теперь сопоставляем метатайлы из карты с ID из LYR
    metatile_updates = {}  # metatile_id -> new_image
    
    print("Сопоставляем метатайлы из карты с ID из LYR...")
    
    # Проходим по карте экран за экраном
    for map_screen_y in range(ScreenHeight):
        for map_screen_x in range(ScreenWidth):
            screen_index = map_screen_y * ScreenWidth + map_screen_x
            screen_id = screen_map[screen_index]
            
            if screen_id not in screen_to_metatile_mapping:
                continue  # Пустой экран
            
            screen_metatile_ids = screen_to_metatile_mapping[screen_id]
            
            # Извлекаем метатайлы из соответствующей области карты
            screen_start_x = map_screen_x * 256
            screen_start_y = map_screen_y * 256
            
            for metatile_pos in range(256):
                metatile_y = metatile_pos // 16
                metatile_x = metatile_pos % 16
                
                # Координаты метатайла в карте
                map_metatile_x = screen_start_x + metatile_x * 16
                map_metatile_y = screen_start_y + metatile_y * 16
                
                # Проверяем что координаты в пределах карты
                if (map_metatile_x + 16 <= map_width and 
                    map_metatile_y + 16 <= map_height):
                    
                    # Извлекаем метатайл из карты
                    metatile_img = map_img.crop((
                        map_metatile_x, map_metatile_y, 
                        map_metatile_x + 16, map_metatile_y + 16
                    ))
                    
                    # ID метатайла из LYR
                    lyr_metatile_id = screen_metatile_ids[metatile_pos]
                    
                    # Сохраняем для обновления
                    metatile_updates[lyr_metatile_id] = metatile_img.copy()
    
    print(f"Подготовлено обновлений: {len(metatile_updates)}")
    
    return metatile_updates

def update_metatile_sheet_from_mapping(original_img, original_metatiles, metatile_updates, output_path):
    """Обновляет оригинальный лист метатайлов согласно сопоставлению ID -> новые изображения"""
    
    print("Обновляем оригинальный лист метатайлов...")
    
    # Создаем копию оригинального листа
    updated_img = original_img.copy()
    
    # Сохраняем оригинальную палитру
    original_palette = None
    if original_img.mode == 'P':
        original_palette = original_img.getpalette()
        if original_palette:
            updated_img.putpalette(original_palette)
            print(f"Сохранена оригинальная палитра ({len(original_palette)//3} цветов)")
    
    width, height = updated_img.size
    metatiles_x = width // 16
    
    updates_made = 0
    
    # Обновляем метатайлы согласно сопоставлению
    for metatile_id, new_metatile_img in metatile_updates.items():
        # Проверяем что ID в пределах листа
        if metatile_id >= len(original_metatiles):
            print(f"  ВНИМАНИЕ: ID {metatile_id} выходит за пределы листа (макс {len(original_metatiles)-1})")
            continue
        
        # Вычисляем позицию в листе
        mx = metatile_id % metatiles_x
        my = metatile_id // metatiles_x
        
        x = mx * 16
        y = my * 16
        
        # ПРАВИЛЬНАЯ конвертация с сохранением оригинальной палитры
        if new_metatile_img.mode != updated_img.mode:
            if updated_img.mode == 'P' and original_palette:
                # Создаем временное изображение с оригинальной палитрой
                temp_img = Image.new('P', (1, 1))
                temp_img.putpalette(original_palette)
                
                # Конвертируем новый метатайл используя оригинальную палитру
                if new_metatile_img.mode in ['RGB', 'RGBA']:
                    # Сначала в RGB если нужно
                    rgb_img = new_metatile_img.convert('RGB')
                    # Затем квантизируем к оригинальной палитре
                    new_metatile_img = rgb_img.quantize(palette=temp_img, dither=Image.NONE)
                else:
                    new_metatile_img = new_metatile_img.convert('P')
                    new_metatile_img.putpalette(original_palette)
            else:
                # Для не-палитровых режимов просто конвертируем
                new_metatile_img = new_metatile_img.convert(updated_img.mode)
        
        # Обновляем метатайл
        updated_img.paste(new_metatile_img, (x, y))
        updates_made += 1
        
        if updates_made <= 10:  # Показываем только первые 10
            print(f"  Обновлен метатайл ID {metatile_id} в позиции ({x}, {y})")
        elif updates_made == 11:
            print("  ... (показаны только первые 10)")
    
    print(f"Обновлено метатайлов: {updates_made}")
    
    # Показываем информацию о неизмененных метатайлах
    unchanged_count = len(original_metatiles) - updates_made
    print(f"Сохранено без изменений: {unchanged_count}")
    
    # Убеждаемся что палитра сохранена
    if original_img.mode == 'P' and original_palette:
        updated_img.putpalette(original_palette)
        print("Палитра восстановлена перед сохранением")
    
    # Сохраняем обновленный файл
    updated_img.save(output_path)
    print(f"Обновленный лист сохранен: {output_path}")
    print(f"Режим изображения: {updated_img.mode}")
    
    return True


def parse_arguments():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(
        description='Генератор/обновлятор метатайлов WayForward',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  WayForward_MetatileGenerator.exe
  WayForward_MetatileGenerator.exe --map STATUS/Full.png
  WayForward_MetatileGenerator.exe --map LEVEL2/Full.png --original LEVEL2_metatile.png --lyr LEVEL2.lyr
  WayForward_MetatileGenerator.exe --map STATUS/Full.png --output STATUS_metatile_new.png
        '''
    )
    
    parser.add_argument('--map', '-m', default=MapPNG,
                        help='Входной PNG файл полной карты (по умолчанию: STATUS/Full.png)')
    parser.add_argument('--original', default=OriginalMetatiles,
                        help='Оригинальный PNG файл метатайлов (по умолчанию: STATUS_metatile.png)')
    parser.add_argument('--lyr', '-l', default=LYRFile,
                        help='LYR файл для анализа (по умолчанию: STATUS.lyr)')
    parser.add_argument('--output', '-o', default=OutputMetatile,
                        help='Выходной PNG файл (по умолчанию: STATUS_metatile_updated.png)')
    parser.add_argument('--lyr-format', type=int, default=LYRFormat,
                        help='Формат LYR (0-3, по умолчанию: 2)')
    parser.add_argument('--ts-format', type=int, default=TSFormat,
                        help='Формат TS (0-4, по умолчанию: 1)')
    
    args = parser.parse_args()
    
    return args

def main():
    # Парсим аргументы командной строки
    args = parse_arguments()
    
    # Применяем аргументы
    map_png = args.map
    original_metatiles = args.original
    lyr_file = args.lyr
    output_metatile = args.output
    lyr_format = args.lyr_format
    ts_format = args.ts_format
    
    # Устанавливаем глобальные переменные для функций
    global LYRFormat, TSFormat
    LYRFormat = lyr_format
    TSFormat = ts_format
    
    print("=== Обновлятор метатайлов WayForward (по LYR данным) ===")
    print(f"Входная карта: {map_png}")
    print(f"Оригинальный лист: {original_metatiles}")
    print(f"LYR файл: {lyr_file}")
    print(f"Выходной файл: {output_metatile}")
    print(f"LYR формат: {lyr_format}")
    print()
    
    # Загружаем оригинальный лист метатайлов
    original_img, original_metatiles_dict = load_original_metatiles(original_metatiles)
    
    if original_img is None:
        return
    
    # Создаем сопоставление между используемыми в LYR ID и метатайлами из карты
    metatile_updates = create_metatile_mapping_from_lyr_and_map(
        lyr_file, map_png, original_metatiles_dict
    )
    
    if metatile_updates is None:
        return
    
    if len(metatile_updates) == 0:
        print("Не найдено метатайлов для обновления!")
        print("Возможные причины:")
        print("- Карта не изменилась относительно оригинала")
        print("- LYR и карта не соответствуют друг другу")
        return
    
    # Обновляем лист метатайлов
    success = update_metatile_sheet_from_mapping(
        original_img, 
        original_metatiles_dict, 
        metatile_updates, 
        output_metatile
    )
    
    if success:
        print()
        print("=== Обновление завершено ===")
        print(f"Обновленный файл: {output_metatile}")
        print(f"Оригинальных метатайлов: {len(original_metatiles_dict)}")
        print(f"Обновлено из карты: {len(metatile_updates)}")
        
        # Показываем обновленные ID
        updated_ids = sorted(metatile_updates.keys())
        if len(updated_ids) <= 20:
            print(f"Обновленные ID: {updated_ids}")
        else:
            print(f"Обновленные ID: {updated_ids[:10]} ... {updated_ids[-5:]} (всего {len(updated_ids)})")
        
        print()
        print("✅ Метатайлы обновлены согласно их использованию в LYR файле")
        print("✅ Все координаты остаются правильными")
        print("✅ Неиспользуемые метатайлы сохранены на своих местах")
        
        print()
        print("Теперь можете использовать обновленный файл:")
        print(f"1. Переименовать его в {os.path.basename(original_metatiles)} если результат устраивает")
        print("2. Запустить TS-Pack для создания TS4 файла")
        print("3. LYR файл остается без изменений - все координаты правильные")
        
    else:
        print("Ошибка при обновлении листа метатайлов")

if __name__ == "__main__":
    main()
