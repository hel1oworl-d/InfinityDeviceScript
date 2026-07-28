<div align="center">

# 📜 InfinityDeviceScript

База скриптов для BROM-режима, используемая **UnisocToolInfinity**
Device script database for BROM mode, used by **UnisocToolInfinity**

[Русский](#-русский) • [English](#-english)

</div>

---

## 🇷🇺 Русский

### Описание

Этот репозиторий — **база скриптов под конкретные устройства** на процессорах Unisoc. Каждая папка внутри репозитория соответствует одной модели устройства и содержит скрипт для управления `spd_dump` в BROM-режиме: снятие дампов памяти и прошивку разделов.

Репозиторий автоматически скачивается и распаковывается программой [**UnisocToolInfinity**](https://github.com/hel1oworl-d/UnisocTool-Infinity) в мастере первого запуска, а также может быть обновлён вручную кнопкой **«Восстановить / Обновить базу»** в настройках программы.

### 📂 Структура репозитория

```
InfinityDeviceScript/
├── <модель_устройства_1>/
│   ├── brom_script.py
│   └── spd_dump[.exe]
├── <модель_устройства_2>/
│   ├── brom_script.py
│   └── spd_dump[.exe]
└── ...
```

После загрузки главная программа копирует эти папки в `UTFHome/BROM/<модель_устройства>/`.

### ⚙️ Как программа вызывает скрипт

`UnisocToolInfinity` запускает `brom_script.py` как отдельный процесс:

```bash
python3 brom_script.py <action> <spd_dump_path> <workspace_path> [extra_args...]
```

| Параметр | Описание |
|---|---|
| `action` | Одно из: `full_dump`, `part_dump`, `full_flash`, `part_flash` |
| `spd_dump_path` | Абсолютный путь к бинарнику `spd_dump` в папке устройства |
| `workspace_path` | Путь к рабочей директории пользователя (`UTFHome`) |
| `extra_args` | Дополнительные аргументы (см. ниже) |

**Дополнительные аргументы по операциям:**

- `part_dump` → `<целевая_папка> <имя_раздела>` — например `SinglePart_Dump boot`
- `part_flash` → `<исходная_папка> <имя_раздела>` — например `Full_Dump system`
- `full_dump` / `full_flash` — дополнительные аргументы не требуются

Скрипт обязан:
- Выводить прогресс построчно в **stdout** (программа читает его в реальном времени и отображает в логе BROM)
- Возвращать корректный код завершения процесса
- Для распознавания статуса подключения программа отслеживает в выводе такие маркеры, как `CHECK_BAUD`, `CMD_CONNECT`, `BSL_REP_VER`, `SEND`, `Executing:`

### 🧩 Вспомогательные файлы

Если в папке `BIN` главной программы присутствуют файлы `custom_exec*` или `custom_exec_no_verify*`, они автоматически копируются в папку устройства при каждом запуске — используйте их в своём `brom_script.py`, если требуется собственный исполняемый обработчик команд.

### ➕ Как добавить новое устройство

1. Создайте папку с названием модели устройства (латиницей, без пробелов)
2. Поместите внутрь `spd_dump` (или `spd_dump.exe` для Windows) и `brom_script.py`
3. Реализуйте в `brom_script.py` обработку всех четырёх действий (`full_dump`, `part_dump`, `full_flash`, `part_flash`) согласно контракту выше
4. Откройте Pull Request

### ⚠️ Дисклеймер

Скрипты в этом репозитории выполняют низкоуровневые операции с памятью устройства. Неправильные параметры (адреса разделов, FDL-загрузчики) могут привести к необратимому повреждению устройства. Используйте на свой страх и риск.

---

## 🇬🇧 English

### Description

This repository is a **device-specific script database** for Unisoc-based chipsets. Each folder corresponds to a single device model and contains a script that drives `spd_dump` in BROM mode — dumping memory and flashing partitions.

The repository is automatically downloaded and extracted by [**UnisocToolInfinity**](https://github.com/hel1oworl-d/UnisocTool-Infinity) during the first-launch setup wizard, and can also be refreshed manually via the **"Repair / Update Database"** button in the app's settings.

### 📂 Repository Structure

```
InfinityDeviceScript/
├── <device_model_1>/
│   ├── brom_script.py
│   └── spd_dump[.exe]
├── <device_model_2>/
│   ├── brom_script.py
│   └── spd_dump[.exe]
└── ...
```

After downloading, the main app copies these folders into `UTFHome/BROM/<device_model>/`.

### ⚙️ How the app invokes the script

`UnisocToolInfinity` runs `brom_script.py` as a separate process:

```bash
python3 brom_script.py <action> <spd_dump_path> <workspace_path> [extra_args...]
```

| Parameter | Description |
|---|---|
| `action` | One of: `full_dump`, `part_dump`, `full_flash`, `part_flash` |
| `spd_dump_path` | Absolute path to the `spd_dump` binary inside the device folder |
| `workspace_path` | Path to the user's workspace directory (`UTFHome`) |
| `extra_args` | Additional arguments (see below) |

**Extra arguments per operation:**

- `part_dump` → `<target_folder> <partition_name>` — e.g. `SinglePart_Dump boot`
- `part_flash` → `<source_folder> <partition_name>` — e.g. `Full_Dump system`
- `full_dump` / `full_flash` — no extra arguments required

The script must:
- Print progress line-by-line to **stdout** (the app reads it in real time and shows it in the BROM log)
- Return a proper process exit code
- Be aware that the app tracks connection status by matching markers in the output such as `CHECK_BAUD`, `CMD_CONNECT`, `BSL_REP_VER`, `SEND`, `Executing:`

### 🧩 Helper Files

If `custom_exec*` or `custom_exec_no_verify*` files exist in the main app's `BIN` folder, they are automatically copied into the device folder on every run — use them from your `brom_script.py` if you need a custom command executor.

### ➕ Adding a New Device

1. Create a folder named after the device model (Latin characters, no spaces)
2. Place `spd_dump` (or `spd_dump.exe` for Windows) and `brom_script.py` inside it
3. Implement all four actions (`full_dump`, `part_dump`, `full_flash`, `part_flash`) in `brom_script.py` following the contract above
4. Open a Pull Request

### ⚠️ Disclaimer

Scripts in this repository perform low-level memory operations on the device. Incorrect parameters (partition addresses, FDL loaders) can cause permanent device damage. Use at your own risk.
