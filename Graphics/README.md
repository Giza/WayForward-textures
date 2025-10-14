# Руководство по использованию аргументов командной строки

Все программы теперь поддерживают аргументы командной строки для удобной работы без редактирования кода.

## WayForward_TS-Extract.py

Распаковывает TS4/TS8 файлы в PNG метатайлы.

### Основное использование:
```bash
# Использовать значения по умолчанию (STATUS)
python WayForward_TS-Extract.py

# Указать другой файл
python WayForward_TS-Extract.py LEVEL2

# С дополнительными опциями
python WayForward_TS-Extract.py 363 --format 1 --scene 362
```

### Аргументы:
- `tileset` - Имя TS4/TS8 файла без расширения (по умолчанию: STATUS)
- `--format` / `-f` - Формат TS (0-4, по умолчанию: 1)
- `--scene` / `-s` - Имя SCN/PAL файла для палитры
- `--raw-palette` - Использовать сырые значения палитры
- `--no-raw-palette` - Нормализовать значения палитры

### Примеры:
```bash
# Распаковать STATUS.ts4 с палитрой STATUS.scn
python WayForward_TS-Extract.py STATUS

# Распаковать LEVEL2.ts4 в формате DS (format=2)
python WayForward_TS-Extract.py LEVEL2 --format 2

# Распаковать 363.ts4 с палитрой из 362.scn
python WayForward_TS-Extract.py 363 --scene 362
```

---

## WayForward_LYR-Extract.py

Распаковывает LYR файлы в PNG карты и экраны.

### Основное использование:
```bash
# Использовать значения по умолчанию (STATUS)
python WayForward_LYR-Extract.py

# Указать другой файл
python WayForward_LYR-Extract.py LEVEL2

# С дополнительными опциями
python WayForward_LYR-Extract.py 366 --format 2 --metatiles 365
```

### Аргументы:
- `screen` - Имя LYR файла без расширения (по умолчанию: STATUS)
- `--format` / `-f` - Формат LYR (0-3, по умолчанию: 2)
- `--metatiles` / `-m` - Имя PNG файла метатайлов

### Примеры:
```bash
# Распаковать STATUS.lyr используя STATUS_metatile.png
python WayForward_LYR-Extract.py STATUS

# Распаковать LEVEL2.lyr в формате 3
python WayForward_LYR-Extract.py LEVEL2 --format 3

# Распаковать 366.lyr используя метатайлы из 365_metatile.png
python WayForward_LYR-Extract.py 366 --metatiles 365
```

---

## WayForward_TS-Pack.py

Упаковывает PNG метатайлы обратно в TS4/TS8 файлы.

### Основное использование:
```bash
# Использовать значения по умолчанию
python WayForward_TS-Pack.py

# Указать входной файл (выходной файл определится автоматически)
python WayForward_TS-Pack.py STATUS_metatile.png

# С указанием выходного файла
python WayForward_TS-Pack.py STATUS_metatile.png --output STATUS
```

### Аргументы:
- `input` - Входной PNG файл с метатайлами (по умолчанию: STATUS_metatile.png)
- `--output` / `-o` - Имя выходного TS4 файла без расширения
- `--format` / `-f` - Формат TS (0-4, по умолчанию: 1)
- `--palette` / `-p` - Имя палитры SCN/PAL
- `--ts8` - Создать TS8 (256 цветов) вместо TS4 (16 цветов)
- `--metatile-count` - Точное количество метатайлов (поддерживает 0x для hex, например: 257 или 0x101)
- `--raw-palette` - Использовать сырые значения палитры
- `--no-raw-palette` - Нормализовать значения палитры

**ВАЖНО**: Если в оригинальном TS4 файле количество метатайлов отличается от размера PNG листа, используйте `--metatile-count` для указания точного значения из оригинала. Это предотвратит смещение текстур в игре.

### Примеры:
```bash
# Упаковать STATUS_metatile.png в STATUS.ts4
python WayForward_TS-Pack.py STATUS_metatile.png

# Упаковать с указанием формата DS
python WayForward_TS-Pack.py LEVEL2_metatile.png --output LEVEL2 --format 2

# Создать TS8 файл (256 цветов)
python WayForward_TS-Pack.py texture.png --output MYTEX --ts8

# С указанием отдельного файла палитры
python WayForward_TS-Pack.py texture.png --output TEX1 --palette TEX1_PAL

# С указанием точного количества метатайлов (десятичное)
python WayForward_TS-Pack.py STATUS_metatile.png --metatile-count 257

# С указанием точного количества метатайлов (шестнадцатеричное)
python WayForward_TS-Pack.py STATUS_metatile.png --metatile-count 0x101
```

**Совет**: Откройте оригинальный TS4 файл в hex редакторе. Смещение `0x02` содержит 2-байтовое значение (little-endian) - это количество метатайлов. Например:
- Байты `01 01` = 0x0101 = 257 метатайлов
- Используйте: `--metatile-count 257` или `--metatile-count 0x101`
```

---

## WayForward_MetatileGenerator.py

Обновляет оригинальный лист метатайлов из отредактированной карты.

### Основное использование:
```bash
# Использовать значения по умолчанию
python WayForward_MetatileGenerator.py

# Указать файлы
python WayForward_MetatileGenerator.py --map STATUS/Full.png --original STATUS_metatile.png
```

### Аргументы:
- `--map` / `-m` - Входной PNG файл полной карты (по умолчанию: STATUS/Full.png)
- `--original` - Оригинальный PNG файл метатайлов (по умолчанию: STATUS_metatile.png)
- `--lyr` / `-l` - LYR файл для анализа (по умолчанию: STATUS.lyr)
- `--output` / `-o` - Выходной PNG файл (по умолчанию: STATUS_metatile_updated.png)
- `--lyr-format` - Формат LYR (0-3, по умолчанию: 2)
- `--ts-format` - Формат TS (0-4, по умолчанию: 1)

### Примеры:
```bash
# Обновить STATUS_metatile.png из STATUS/Full.png
python WayForward_MetatileGenerator.py

# Работа с другим уровнем
python WayForward_MetatileGenerator.py \
  --map LEVEL2/Full.png \
  --original LEVEL2_metatile.png \
  --lyr LEVEL2.lyr \
  --output LEVEL2_metatile_updated.png

# С указанием форматов
python WayForward_MetatileGenerator.py --lyr-format 3 --ts-format 2

# Только указать карту (остальное по умолчанию)
python WayForward_MetatileGenerator.py --map STATUS/Full.png
```

---

## Полный рабочий процесс с аргументами

### 1. Распаковка:
```bash
# Распаковать текстуры
python WayForward_TS-Extract.py STATUS

# Распаковать карту
python WayForward_LYR-Extract.py STATUS
```

### 2. Редактирование:
Отредактируйте файл `STATUS/Full.png` в вашем графическом редакторе.

**ВАЖНО**: `Full.png` теперь сохраняется в палитровом режиме (8-bit с PLTE чанком), сохраняя оригинальную палитру из `_metatile.png`. При редактировании:
- Используйте редактор, поддерживающий Indexed Color (GIMP, Aseprite, Photoshop)
- НЕ конвертируйте в RGB/RGBA
- НЕ используйте сглаживание (anti-aliasing)
- НЕ используйте дизеринг (dithering)

### 3. Генерация обновленных метатайлов:
```bash
python WayForward_MetatileGenerator.py --map STATUS/Full.png
```

### 4. Упаковка обратно:
```bash
# Переименовать обновленный файл
move STATUS_metatile_updated.png STATUS_metatile.png

# Упаковать в TS4
python WayForward_TS-Pack.py STATUS_metatile.png
```

### 5. Готово!
Теперь у вас есть обновленный `STATUS.ts4` файл с вашими изменениями.

---

## Работа с несколькими уровнями

Вы можете легко работать с разными уровнями без редактирования кода:

```bash
# Уровень 1
python WayForward_TS-Extract.py LEVEL1
python WayForward_LYR-Extract.py LEVEL1
# ... редактирование LEVEL1/Full.png ...
python WayForward_MetatileGenerator.py --map LEVEL1/Full.png --original LEVEL1_metatile.png --lyr LEVEL1.lyr --output LEVEL1_metatile_updated.png
python WayForward_TS-Pack.py LEVEL1_metatile_updated.png --output LEVEL1

# Уровень 2
python WayForward_TS-Extract.py LEVEL2
python WayForward_LYR-Extract.py LEVEL2
# ... редактирование LEVEL2/Full.png ...
python WayForward_MetatileGenerator.py --map LEVEL2/Full.png --original LEVEL2_metatile.png --lyr LEVEL2.lyr --output LEVEL2_metatile_updated.png
python WayForward_TS-Pack.py LEVEL2_metatile_updated.png --output LEVEL2
```

---

## Получение справки

Для любой программы можно вызвать справку с помощью `--help` или `-h`:

```bash
python WayForward_TS-Extract.py --help
python WayForward_LYR-Extract.py --help
python WayForward_TS-Pack.py --help
python WayForward_MetatileGenerator.py --help
```

Это покажет полный список доступных аргументов и примеры использования.

---

## Примечания

- Все аргументы опциональны - программы будут использовать значения по умолчанию
- Короткие формы аргументов (`-f`, `-m`, `-o` и т.д.) работают так же как полные (`--format`, `--map`, `--output`)
- Если не указать выходной файл, он будет определен автоматически на основе входного
- Форматы файлов (TSFormat, LYRFormat) зависят от игры - см. комментарии в исходном коде программ

