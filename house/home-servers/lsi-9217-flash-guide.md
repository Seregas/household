# Прошивка LSI 9217-8i (SAS2308) — додавання UEFI boot-ROM

> Мета: зробити HBA **завантажувальним у UEFI**, щоб BIOS бачив boot-запис TrueNAS
> на дзеркалі Intel+Samsung за цим контролером.
> Стан зараз: карта в IT-mode, диски в ОС/інсталяторі видно, heartbeat-LED блимає
> (firmware живий), АЛЕ banner LSI на POST відсутній і Boot Options порожній →
> на карті **немає UEFI boot-ROM (UEFI BSD)**.

## ⭐ ГОЛОВНЕ: мінімальний (низькоризиковий) шлях

Карта вже на робочому firmware. Тобі НЕ треба стирати й перешивати firmware
(саме стирання `-e` — головне джерело ризику «цеглини» через втрату SAS-адреси).
Достатньо **ДОДАТИ** відсутній UEFI boot-ROM однією командою:

```
sas2flash.efi -b x64sas2.rom
```

`-b` пише лише boot-ROM, не чіпає firmware, NVDATA і SAS-адресу. Це найбезпечніша
операція. Очікувано — цього достатньо, щоб з'явився banner і boot-запис.

Повне стирання+перешивання firmware робимо ТІЛЬКИ якщо `-list` покаже, що firmware
неправильний/старий — і тоді НЕ самостійно, а разом (див. «Фолбек» у кінці).

## Ризики й запобіжники (прочитати ДО початку)
- ⚡ Живлення від UPS (є) — не переривати процес.
- Записати **SAS Address** з `-list` ДО будь-якої заливки (страховка №1).
- Переконатися, що шиєш ПРАВИЛЬНИЙ контролер (у тебе він один — але звіряй).
- Не виймати флешку / не ребутати під час заливки.
- `-b` (додавання ROM) безпечніше за `-e`+`-f` (стирання+firmware) на порядок.

## Які файли потрібні (качай на MacBook)

Усе з офіційного Broadcom (support → SAS 9217-8i → Downloads → Firmware):

1. **sas2flash.efi** — UEFI-флешер. Пакет `Installer_P20_for_UEFI.zip`.
2. **x64sas2.rom** — UEFI BSD boot-ROM (v7.27.01.00). Пакет `UEFI_BSD_P20.zip`
   (на docs.broadcom.com). ⬅️ ЦЕ ключовий файл для UEFI-завантаження.
3. (опц.) **mptsas2.rom** — legacy BIOS ROM. Потрібен лише якщо колись
   вантажитимешся в CSM/Legacy. Для UEFI не обов'язковий.
4. (фолбек) **9207-8.bin** — IT-firmware. Лише якщо знадобиться повне перешивання.
   Пакет `9217-8i_Package_P20_IR_IT_Firmware_BIOS_for_MSDOS_Windows.zip`,
   тека `Firmware/HBA_9207_8i_IT/9207-8.bin`. (Увага: 9207 = IT, 9217 = IR!)

5. **UEFI Shell v1** (КРИТИЧНО — не v2!): TianoCore EDK2 гілка UDK2014,
   `ShellBinPkg/UefiShell/X64/Shell.efi`. ⚠️ sas2flash.efi працює ТІЛЬКИ з
   Shell **v1**; з v2 буде помилка `InitShellApp: Application not started from Shell`.

## Підготовка флешки (на MacBook)

Окрема порожня флешка (НЕ інсталяційна TrueNAS).

1. Disk Utility → Erase → формат **MS-DOS (FAT)**, схема **GUID Partition Map**.
2. Розкласти файли так:
   ```
   (корінь флешки)
     sas2flash.efi
     x64sas2.rom
     mptsas2.rom        (якщо взяв)
     9207-8.bin         (лише для фолбеку)
     EFI/
       BOOT/
         BOOTX64.EFI    <- це перейменований Shell.efi (UEFI Shell v1)
   ```
   ⚠️ sas2flash.efi і .rom мають лежати в КОРЕНІ (інакше `Could not open file`).

## Процедура (біля сервера)

### Крок 0. Завантажитись у UEFI Shell
- Встав підготовлену флешку в **задній USB 2.0**.
- Старт → F7 (Boot menu) → вибери `UEFI: <флешка>` (вона завантажить BOOTX64.EFI = Shell v1).
- Опинишся в shell. Перейди на флешку: набери `fs0:` + Enter (якщо не та — `fs1:`, `fs2:`…).
  Перевір вміст командою `ls` — маєш бачити sas2flash.efi, x64sas2.rom.

### Крок 1. ЗЧИТАТИ СТАН (нічого не змінює) — і ЗУПИНИТИСЬ
```
sas2flash.efi -listall
sas2flash.efi -list
```
СФОТКАЙ вивід. Звідти критично:
- `Firmware Version` (очікувано 20.00.07.00 = P20 IT)
- `BIOS Version` і `UEFI BSD Version` (очікувано N/A — підтвердить, що ROM нема)
- `SAS Address` ← ЗАПИШИ ОКРЕМО (на папір/у нотатку). Страховка.

➡️ На цьому СТОП. Надішли вивід — звіримо, що шлях мінімальний, і лише тоді Крок 2.

### Крок 2. Додати UEFI boot-ROM (мінімальний шлях)
```
sas2flash.efi -b x64sas2.rom
```
(якщо відмовить без override — `sas2flash.efi -o -b x64sas2.rom`)
Чекай ~хвилину, до `Finished Processing Commands Successfully`.

Перевір:
```
sas2flash.efi -list
```
Тепер `UEFI BSD Version` має показувати версію (не N/A). SAS Address — на місці.

### Крок 3. Ребут і перевірка
- `reset` (або вийми флешку й перезавантаж).
- На POST має з'явитися **banner LSI/Avago** зі списком дисків.
- BIOS → Boot: має з'явитися boot-запис (UEFI OS / truenas).
- Постав його першим. Переконайся, що Storage OpROM = UEFI (Chipset → CSM).
- Завантажся в TrueNAS.

## Фолбек (ТІЛЬКИ якщо Крок 2 не допоміг або firmware неправильний)
Повне стирання `-e` + перешивання `-f` — небезпечне (ризик втрати SAS-адреси).
НЕ роби самостійно. Надішли вивід `-list` — пройдемо разом, покроково,
зі збереженням і відновленням SAS-адреси (`-o -sasadd <addr>`).

## Якщо щось пішло не так
- `Failed to initialize PAL` → ти в DOS-утиліті або не тій версії; треба UEFI sas2flash.efi.
- `Application not started from Shell` → завантажив Shell v2; потрібен v1.
- `Could not open file` → файли не в корені флешки.
- Постійний звуковий сигнал після прошивки → не виймай, зчитай `-list`, напиши мені.

## SAS Address (з наклейки на платі — страховка)
**SAS Address: `500605B005CE13E0`** (на платі: `500605B 005CE13E0`).
Assembly P/N: H3-25331-01J (SAS9217-8i, чип SAS2308).
Нижня наклейка KCC: SAS9205-8I — нормально (кросфлеш/змішане маркування, орієнтир — `-list`).

Якщо після прошивки SAS-адреса загубиться:
```
sas2flash.efi -o -sasadd 500605B005CE13E0
```
(звірити з тим, що покаже `-list` ДО прошивки — пріоритет у живого `-list`, наклейка — резерв).
