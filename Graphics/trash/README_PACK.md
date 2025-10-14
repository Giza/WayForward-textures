# WayForward Упаковщики TS4/LYR

Эти программы создают обратную упаковку для форматов WayForward:
- **WayForward_TS-Pack.py** - упаковывает PNG метатайлы в TS4/TS8 файлы
- **WayForward_LYR-Pack.py** - упаковывает PNG карты в LYR файлы
- **WayForward_MetatileGenerator.py** - обновляет лист метатайлов по LYR данным из карты
- **WayForward_LYR-Analyzer.py** - анализирует использование метатайлов в LYR
- **WayForward_LYR-Updater.py** - обновляет LYR после изменения метатайлов

## Что такое форматы WayForward?

### TS4/TS8 файлы (тайлсеты)
- Содержат графические блоки (тайлы 8×8 пикселей)
- Объединены в метатайлы 16×16 пикселей
- TS4 = 16 цветов, TS8 = 256 цветов

### LYR файлы (карты/уровни)  
- Содержат инструкции как собирать уровни из метатайлов
- Карта состоит из экранов 256×256 пикселей
- Каждый экран состоит из 16×16 метатайлов
- **ВАЖНО**: LYR ссылается на метатайлы по ID (позиция в листе)

## Рабочий процесс

### 1. Распаковка (существующие программы)
```bash
# Извлекаем метатайлы из TS4
python WayForward_TS-Extract.py
# Создается: STATUS_metatile.png

# Извлекаем карты из LYR  
python WayForward_LYR-Extract.py
# Создается папка: STATUS/ с экранами и Full.png
```

### 2. Редактирование

#### Способ 1: Редактирование метатайлов
- Редактируйте `STATUS_metatile.png` - добавляйте/изменяйте метатайлы
- Редактируйте `STATUS/Full.png` - изменяйте карту уровня

#### Способ 2: Обновление из отредактированной карты  
- Отредактируйте карту в `STATUS/Full.png` 
- Запустите `WayForward_MetatileGenerator.py` для обновления используемых метатайлов

### 3. Генерация метатайлов из карты (если нужно)

Если вы отредактировали `STATUS/Full.png` и добавили новые элементы:

#### Настройка WayForward_MetatileGenerator.py:
```python
MapPNG = "STATUS/Full.png"                      # Входная карта
OriginalMetatiles = "STATUS_metatile.png"       # Оригинальный лист (база)
OutputMetatile = "STATUS_metatile_updated.png"  # Выходной файл
LYRFile = "STATUS.lyr"                          # LYR файл (определяет какие ID обновлять)
LYRFormat = 2                                   # Формат LYR
```

```bash
python WayForward_MetatileGenerator.py
# Создается STATUS_metatile_updated.png - обновленная версия оригинального листа
# Программа читает LYR файл, узнает какие ID метатайлов используются
# Обновляет эти конкретные позиции метатайлами из соответствующих мест карты
# Все остальные метатайлы остаются нетронутыми
```

### 4. Упаковка обратно (новые программы)

#### Настройка WayForward_TS-Pack.py:
```python
TSFormat = 1                          # Такой же как в распаковщике
TilesetName = "STATUS"                # Имя выходного файла
MetatilePNG = "STATUS_metatile.png"   # Входной PNG с метатайлами  
PaletteName = "STATUS"                # Палитра (пустая строка = авто)
Use256Colors = False                  # True для TS8, False для TS4
```

#### Настройка WayForward_LYR-Pack.py:
```python
LYRFormat = 2                         # Такой же как в распаковщике
ScreenName = "STATUS"                 # Имя выходного файла
MapPNG = "STATUS/Full.png"            # Входной PNG карты
MetatilePNG = "STATUS_metatile.png"   # PNG с метатайлами
TilesetID = 1                         # ID тайлсета
```

#### Запуск упаковки:
```bash
# Упаковываем метатайлы в TS4
python WayForward_TS-Pack.py
# Создается: STATUS.ts4 + STATUS.pal

# Упаковываем карту в LYR
python WayForward_LYR-Pack.py  
# Создается: STATUS.lyr
```

## Важные требования

### Для метатайлов (TS4):
- PNG должен иметь ширину кратную 16 пикселям
- Высота кратна 16 пикселям  
- Каждый блок 16×16 = один метатайл
- Рекомендуется палитровый режим (256 цветов максимум)

### Для карт (LYR):
- PNG карта должна иметь размер кратный 256 пикселям
- Каждый блок 256×256 = один экран
- Все метатайлы на карте должны существовать в файле метатайлов
- Программа автоматически найдет повторяющиеся экраны и сожмет данные

## Форматы игр

Установите правильные значения TSFormat и LYRFormat для вашей игры:

### Game Boy Advance:
- **Shantae Advance**: TSFormat=1, LYRFormat=2
- **Sigma Star Saga**: TSFormat=1, LYRFormat=3  
- **Godzilla Domination**: TSFormat=0, LYRFormat=1

### Nintendo DS:
- **Contra 4**: TSFormat=2, LYRFormat=3
- **Shantae Risky's Revenge**: TSFormat=2, LYRFormat=3
- **Batman Brave and Bold**: TSFormat=2, LYRFormat=3

### LeapFrog Didj:
- **Nicktoons**: TSFormat=3, LYRFormat=3  
- **SpongeBob Fists of Foam**: TSFormat=3, LYRFormat=3

### LeapFrog Leapster:
- **Все игры**: TSFormat=4, LYRFormat=2

## Устранение проблем

### "Не найден файл"
- Проверьте пути к файлам в переменных программы
- Убедитесь что PNG файлы существуют

### "Размер не кратен 256/16"
- Измените размер PNG в графическом редакторе
- Размер должен быть точно кратным нужному значению

### "Метатайл не найден" 
- Убедитесь что все метатайлы на карте есть в файле метатайлов
- Проверьте что метатайлы не изменились после редактирования

### Неправильные цвета
- Установите RawPalette = True для "сырых" значений
- Используйте палитровый режим PNG (256 цветов)

## Работа с LYR данными и ID метатайлов

### Проблема связи метатайлов и LYR

**LYR файлы ссылаются на метатайлы по ID:**
- ID 0 = метатайл в позиции (0,0) листа  
- ID 1 = метатайл в позиции (16,0)
- ID 16 = метатайл в позиции (0,16)

**Если вы измените `STATUS_metatile.png`** (переставите/добавите метатайлы), ID изменятся, но LYR будет ссылаться на старые ID!

### Анализ использования метатайлов

```bash
# Анализируем какие метатайлы где используются
python WayForward_LYR-Analyzer.py
# Создается: STATUS_analysis.json, STATUS_coordinates.json, STATUS_usage.txt
```

**Результаты анализа:**
- Какие метатайлы используются в LYR
- Сколько раз каждый метатайл встречается  
- В каких экранах и позициях
- Координаты метатайлов в листе

### Обновление LYR после изменения метатайлов

**Если вы отредактировали `STATUS_metatile.png`:**

```bash
# 1. Переименуйте оригинальный файл
move STATUS_metatile.png STATUS_metatile_old.png

# 2. Создайте новый файл метатайлов (ваш отредактированный)
# STATUS_metatile.png

# 3. Обновите LYR файл
python WayForward_LYR-Updater.py
# Создается: STATUS_updated.lyr, STATUS_mapping_report.txt

# 4. Проверьте результат и переименуйте если всё хорошо  
move STATUS_updated.lyr STATUS.lyr
```

**Программа автоматически:**
- Найдет соответствия между старыми и новыми метатайлами
- Обновит все ссылки в LYR файле
- Создаст отчет о переназначении ID

## Пример полного цикла

### Вариант 1: Редактирование существующих ресурсов
```bash
# 1. Распаковка оригинальных файлов
python WayForward_TS-Extract.py    # STATUS.ts4 -> STATUS_metatile.png
python WayForward_LYR-Extract.py   # STATUS.lyr -> STATUS/Full.png

# 2. Редактирование в графическом редакторе
# - Измените STATUS_metatile.png (добавьте новые блоки)  
# - Измените STATUS/Full.png (постройте новый уровень)

# 3. Упаковка обратно
python WayForward_TS-Pack.py       # STATUS_metatile.png -> STATUS.ts4
python WayForward_LYR-Pack.py      # STATUS/Full.png -> STATUS.lyr

# 4. Готово! Новые STATUS.ts4 и STATUS.lyr готовы для игры
```

### Вариант 2: Обновление из отредактированной карты
```bash
# 1. Распаковка оригинальных файлов
python WayForward_TS-Extract.py    # STATUS.ts4 -> STATUS_metatile.png
python WayForward_LYR-Extract.py   # STATUS.lyr -> STATUS/Full.png

# 2. Редактирование карты
# - Отредактируйте STATUS/Full.png (измените уровень)
# - Используйте существующие элементы или добавьте новые

# 3. Обновление метатайлов из карты
python WayForward_MetatileGenerator.py  # Обновляет только используемые метатайлы
# Создается STATUS_metatile_updated.png

# 4. Упаковка обновленных файлов  
# Переименуйте обновленный файл
move STATUS_metatile_updated.png STATUS_metatile.png
python WayForward_TS-Pack.py           # обновленный лист -> STATUS.ts4
python WayForward_LYR-Pack.py          # STATUS/Full.png -> STATUS.lyr

# 5. Готово! Координаты LYR правильные, неиспользуемые метатайлы сохранены
```

### Вариант 3: Редактирование только метатайлов с обновлением LYR
```bash
# 1. Распаковка оригинальных файлов
python WayForward_TS-Extract.py    # STATUS.ts4 -> STATUS_metatile.png
python WayForward_LYR-Extract.py   # STATUS.lyr -> STATUS/Full.png

# 2. Анализ использования (опционально)
python WayForward_LYR-Analyzer.py  # Узнать какие метатайлы используются

# 3. Переименуйте оригинальный файл
move STATUS_metatile.png STATUS_metatile_old.png

# 4. Отредактируйте метатайлы (переставьте, добавьте новые)
# Создайте новый STATUS_metatile.png

# 5. Обновите LYR файл с новыми ID метатайлов  
python WayForward_LYR-Updater.py   # Обновляет ссылки на метатайлы

# 6. Упаковка новых файлов
python WayForward_TS-Pack.py       # новый STATUS_metatile.png -> STATUS.ts4
move STATUS_updated.lyr STATUS.lyr # новый LYR файл

# 7. Готово! Метатайлы обновлены, LYR синхронизирован
```

Теперь у вас есть полный набор инструментов для редактирования уровней игр WayForward!
