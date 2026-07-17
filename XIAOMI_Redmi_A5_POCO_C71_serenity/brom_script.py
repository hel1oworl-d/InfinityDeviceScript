import sys
import subprocess
import os
import shutil
import time
import select

# Принудительно построчная буферизация stdout для GUI
sys.stdout.reconfigure(line_buffering=True)

action = sys.argv[1]
spd_dump = sys.argv[2]
workspace = sys.argv[3]

DEVICE_DIR = os.path.dirname(os.path.abspath(__file__))
DEVICE_NAME = os.path.basename(DEVICE_DIR)

EXEC_ADDR = "0x65015f08"
FDL1 = os.path.join(DEVICE_DIR, "fdl1-dl.bin")
FDL1_ADDR = "0x65000800"
FDL2 = os.path.join(DEVICE_DIR, "fdl2-dl.bin")
FDL2_ADDR = "0x9efffe00"

IDLE_TIMEOUT_SEC = 15


def run_cmd_watchdog(cmd_list, cwd=None, idle_timeout=IDLE_TIMEOUT_SEC, send_reset_after=False, is_multi_op=False):
    full_cmd = [spd_dump, "exec_addr", EXEC_ADDR, "fdl", FDL1, FDL1_ADDR,
                "fdl", FDL2, FDL2_ADDR, "exec"] + cmd_list
    print(f"Executing: {' '.join(full_cmd)}")

    proc = subprocess.Popen(
        full_cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE, text=True, bufsize=1,
    )

    last_activity = time.time()
    killed_by_watchdog = False

    while True:
        if proc.poll() is not None:
            break

        ready, _, _ = select.select([proc.stdout], [], [], 0.5)
        if ready:
            line = proc.stdout.readline()
            if line:
                cleaned_line = line.rstrip()
                print(cleaned_line)
                last_activity = time.time()
                
                # Применяем жесткий перехват ТОЛЬКО если это одиночная операция!
                if not is_multi_op:
                    if "Read Part Done" in cleaned_line or "Write Part Done" in cleaned_line or "100%" in cleaned_line:
                        if send_reset_after:
                            print(">>> Маркер завершения обнаружен! Принудительно отправляем 'reset'...")
                            try:
                                proc.stdin.write("reset\n")
                                proc.stdin.flush()
                                time.sleep(0.5)
                            except Exception as e:
                                print(f"[!] Ошибка отправки reset: {e}")
                        break
        else:
            # Если процесс завершился, readline вернет пустую строку
            if proc.poll() is not None:
                break

        if time.time() - last_activity > idle_timeout:
            print(f"[!] Тайм-аут ({idle_timeout} сек).")
            proc.kill()
            try: proc.wait(timeout=2)
            except Exception: pass
            killed_by_watchdog = True
            break

    try:
        proc.stdin.close()
        proc.stdout.close()
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=1)
    except Exception:
        pass

    return proc.returncode, killed_by_watchdog


def move_dumped_files(src_dir, dst_dir):
    ignored_files = {
        "brom_script.py", "custom_exec_no_verify_65015f08.bin",
        "custom_exec_no_verify.bin", "fdl1-dl.bin", "fdl2-dl.bin",
        "spd_dump", "spd_dump.exe"
    }
    moved = []
    for name in os.listdir(src_dir):
        if (name.endswith(".bin") or name.endswith(".xml") or name.endswith(".img")) and name not in ignored_files:
            src = os.path.join(src_dir, name)
            dst = os.path.join(dst_dir, name)
            try:
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(src, dst)
                moved.append(dst)
            except Exception as e:
                print(f"Не удалось перенести {src}: {e}")
    return moved


if action == "full_dump":
    save_dir = os.path.join(workspace, "Full_Dump", DEVICE_NAME)
    os.makedirs(save_dir, exist_ok=True)
    try:
        print(">>> Запуск нативного дампа служебных разделов (all_lite)...")
        returncode, killed = run_cmd_watchdog(["r", "all_lite"], cwd=DEVICE_DIR)
    finally:
        time.sleep(1.5)
        moved = move_dumped_files(DEVICE_DIR, save_dir)
        print(f"\n[+] Операция завершена. Перенесено разделов: {len(moved)}")

elif action == "part_dump":
    # Переносим чтение аргументов внутрь блока, здесь они занимают 4 и 5 индексы
    # sys.argv[4] — это папка (SinglePart_Dump), sys.argv[5] — имя раздела
    raw_part_name = sys.argv[5] 
    
    IS_AB = True
    slot_dependent_partitions = {
        "boot", "init_boot", "vendor_boot", "dtb", "dtbo", "logo", "trustos",
        "sml", "uboot", "l_modem", "l_deltanv", "l_gdsp", "l_ldsp", "l_agdsp",
        "pm_sys", "teecfg", "hypervsior", "vbmeta", "vbmeta_system", "vbmeta_vendor",
        "vbmeta_system_ext", "vbmeta_product", "vbmeta_odm", "avbmeta_rs", "common_rs1",
        "common_rs2", "common_rs3"
    }
    
    if IS_AB and (raw_part_name in slot_dependent_partitions) and not (raw_part_name.endswith("_a") or raw_part_name.endswith("_b")):
        part_name = f"{raw_part_name}_a"
        print(f"[SCRIPT] Устройство определено как A/B. Раздел '{raw_part_name}' автоматически изменен на слот по умолчанию -> '{part_name}'")
    else:
        part_name = raw_part_name

    PARTITION_SIZES = {
        "splloader": "256k", "prodnv": "64m", "miscdata": "1m", "countrycode": "2m",
        "misc": "1m", "trustos_a": "6m", "trustos_b": "6m", "sml_a": "1m", "sml_b": "1m",
        "uboot_a": "8m", "uboot_b": "8m", "uboot_log": "16m", "logo_a": "8m", "logo_b": "8m",
        "fbootlogo": "8m", "l_fixnv1_a": "2m", "l_fixnv2_a": "2m", "l_fixnv1_b": "2m",
        "l_fixnv2_b": "2m", "l_runtimenv1": "2m", "l_runtimenv2": "2m", "persist": "2m",
        "l_modem_a": "25m", "l_modem_b": "25m", "l_deltanv_a": "1m", "l_deltanv_b": "1m",
        "l_gdsp_a": "10m", "l_gdsp_b": "10m", "l_ldsp_a": "20m", "l_ldsp_b": "20m",
        "l_agdsp_a": "6m", "l_agdsp_b": "6m", "pm_sys_a": "1m", "pm_sys_b": "1m",
        "teecfg_a": "1m", "teecfg_b": "1m", "hypervsior_a": "10m", "hypervsior_b": "10m",
        "boot_a": "64m", "boot_b": "64m", "vendor_boot_a": "100m", "vendor_boot_b": "100m",
        "init_boot_a": "8m", "init_boot_b": "8m", "dtb_a": "8m", "dtb_b": "8m",
        "dtbo_a": "8m", "dtbo_b": "8m", "super": "5120m", "cache": "64m", "blackbox": "500m",
        "vbmeta_a": "2m", "vbmeta_b": "2m", "metadata": "64m", "sysdumpdb": "10m",
        "vbmeta_system_a": "2m", "vbmeta_system_b": "2m", "vbmeta_vendor_a": "2m",
        "vbmeta_vendor_b": "2m", "vbmeta_system_ext_a": "2m", "vbmeta_system_ext_b": "2m",
        "vbmeta_product_a": "2m", "vbmeta_product_b": "2m", "vbmeta_odm_a": "2m",
        "vbmeta_odm_b": "2m", "avbmeta_rs_a": "2m", "avbmeta_rs_b": "2m", "common_rs1_a": "8m",
        "common_rs1_b": "8m", "common_rs2_a": "16m", "common_rs2_b": "16m", "common_rs3_a": "32m",
        "common_rs3_b": "32m", "reserve1": "8m", "reserve2": "16m", "calinv": "2m",
        "gsort": "16m", "mem": "4m", "ffu": "8m", "cust": "2048m", "rescue": "128m"
    }

    part_size = PARTITION_SIZES.get(part_name, "64m")
    
    save_dir = os.path.join(workspace, "SinglePart_Dump", DEVICE_NAME)
    os.makedirs(save_dir, exist_ok=True)
    
    save_path = os.path.join(save_dir, f"{part_name}.bin")
    print(f"\n>>> Запуск одиночного дампа раздела '{part_name}' (Размер: {part_size})...")
    
    ret_code, killed = run_cmd_watchdog(["read_part", part_name, "0", part_size, save_path], cwd=DEVICE_DIR, send_reset_after=True)
    
    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        print(f"\n[+] Раздел {part_name} успешно сохранен: {save_path}")
        print(">>> Операция дампа завершена!")
    else:
        print(f"[!] Ошибка: Файл дампа пуст или не был создан.")
        if os.path.exists(save_path):
            try: os.remove(save_path)
            except: pass

elif action == "full_flash":
    src_dir = os.path.join(workspace, "Full_Dump", DEVICE_NAME)
    
    if not os.path.exists(src_dir):
        print(f"[!] Ошибка: Папка с дампом не найдена по пути: {src_dir}")
    else:
        ignored_files = {"pgpt.bin", "user_partition.bin"}
        bin_files = [f for f in os.listdir(src_dir) if f.endswith(".bin") and f not in ignored_files]
        
        if not bin_files:
            print(f"[!] Ошибка: В папке {src_dir} не найдено файлов .bin для прошивки!")
        else:
            print(f"\n>>> НАЙДЕНО РАЗДЕЛОВ ДЛЯ ВОССТАНОВЛЕНИЯ: {len(bin_files)}")
            
            flash_commands = []
            for bin_file in sorted(bin_files):
                part_name = bin_file.replace(".bin", "")
                file_path = os.path.join(src_dir, bin_file)
                
                flash_commands.extend(["write_part", part_name, file_path])
                print(f"  [+] В очереди на прошивку: {part_name}")
            
            flash_commands.append("reset")
            
            print(f"\n>>> ЗАПУСК ПОЛНОЙ ПРОШИВКИ ({len(bin_files)} разделов)...")
            print(">>> НЕ ОТКЛЮЧАЙТЕ УСТРОЙСТВО ОТ ПК!")
            
            ret_code, killed = run_cmd_watchdog(flash_commands, cwd=DEVICE_DIR, send_reset_after=True)
            
            if ret_code == 0:
                print("\n[+] УСПЕХ: Все разделы восстановлены, выполнен reset!")
            else:
                print(f"\n[!] Ошибка при прошивке. Код возврата: {ret_code}")

elif action == "part_flash":
    # Переносим чтение аргументов строго внутрь блока part_flash!
    folder_type = sys.argv[4]     # Сюда прилетает "Full_Dump" или "SinglePart_Dump"
    raw_part_name = sys.argv[5].lower().strip()  # Имя раздела, который ввёл юзер (напр. boot)
    
    IS_AB = True
    slot_dependent_partitions = {
        "boot", "init_boot", "vendor_boot", "dtb", "dtbo", "logo", "trustos",
        "sml", "uboot", "l_modem", "l_deltanv", "l_gdsp", "l_ldsp", "l_agdsp",
        "pm_sys", "teecfg", "hypervsior", "vbmeta", "vbmeta_system", "vbmeta_vendor",
        "vbmeta_system_ext", "vbmeta_product", "vbmeta_odm", "avbmeta_rs", "common_rs1",
        "common_rs2", "common_rs3"
    }
    
    if IS_AB and (raw_part_name in slot_dependent_partitions) and not (raw_part_name.endswith("_a") or raw_part_name.endswith("_b")):
        part_name = f"{raw_part_name}_a"
        print(f"[SCRIPT] Устройство определено как A/B. Раздел автоматически переключен на слот по умолчанию -> '{part_name}'")
    else:
        part_name = raw_part_name

    src_dir = os.path.join(workspace, folder_type, DEVICE_NAME)
    file_to_flash = os.path.join(src_dir, f"{part_name}.bin")
    
    if not os.path.exists(file_to_flash):
        print(f"[!] КРИТИЧЕСКАЯ ОШИБКА: Файл для прошивки не найден по пути:\n    {file_to_flash}")
    else:
        print(f"\n>>> СИНХРОНИЗАЦИЯ: Папка источника -> {folder_type}")
        print(f">>> ПОДГОТОВКА К ПРОШИВКЕ РАЗДЕЛА '{part_name}'...")
        print(f">>> Образ: {file_to_flash}")
        print(">>> НЕ ОТКЛЮЧАЙТЕ УСТРОЙСТВО!")
        
        ret_code, killed = run_cmd_watchdog(["write_part", part_name, file_to_flash, "reset"], cwd=DEVICE_DIR, send_reset_after=True)
        
        if ret_code == 0:
            print(f"\n[+] Раздел {part_name} успешно восстановлен из {folder_type}! Выполнен аппаратный сброс.")
        else:
            print(f"[!] Ошибка прошивки раздела {part_name}. Код возврата: {ret_code}")
