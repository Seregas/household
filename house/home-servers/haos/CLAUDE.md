# Home Assistant OS на Mac mini M4 (UTM) — відновлення з бекапу

## Загальний опис

Підняти Home Assistant на окремому залізі — **Mac mini M4** — у вигляді **HAOS у VM
під UTM**, **відновивши з бекапу** наявну конфігурацію.

**Що сталося:** Proxmox-хост помер (разом із ним TrueNAS-VM і PBS-бекапи на ZFS-пулі —
тимчасово недоступні). HA-VM `haos-ck` (VM 111) **не воскресити**.
Tailscale підтверджує: `pve` і `haos-ck` offline з ~10.06.2026.

**Рятунок:** щоденний **automatic backup** HA вивантажувався в **Google Drive**.
Узятий бекап `Automatic_backup_2026.3.4_2026-06-09` (зашифрований, securetar) —
повна конфігурація. Розшифровано ключем (emergency kit), вміст звірено (нижче).

**Мета:** відновити HA «як було» на Mac mini M4, незалежно від Proxmox.

---

## Поточна конфігурація (snapshot бекапу 2026-06-09)

> Джерело істини для відновлення. HA версія на момент бекапу — **2026.3.4**,
> Supervisor 2026.05.1.

### Ядро
| Параметр | Значення |
|---|---|
| location_name | Home |
| time_zone | Europe/Kiev |
| country / language / currency | UA / en / UAH |
| Призначення | керування **офісом на Грушевського** (ворота, сигналізація, Tuya) |

### Інтеграції (15 доменів, 18 записів)
| Домен | Призначення |
|---|---|
| `tuya` + `localtuya` | Tuya-пристрої (хмара + локальні ключі) |
| `sia` | **SIA Alarm** — охоронна панель, HA слухає **TCP :8124** |
| `go2rtc` | камери (RTSP/WebRTC) |
| `google_drive` | вивантаження бекапів (рятівне!) |
| `tailscale` | віддалений доступ (`sergey.slepchenko@gmail.com`) |
| `mobile_app` | 4 телефони (Seregas, OnePlus CPH2653/HD1913, motorola edge 50) |
| `met` | погода Met.no |
| `radio_browser`, `shopping_list`, `sun`, `backup`, `hassio` | стандартні |

### HACS (custom)
- `hacs/integration` v2.0.5
- `rospogrigio/localtuya` v5.2.5 (integration)
- `NemesisRE/kiosk-mode` v10.0.0 (plugin)

### Add-ons
- Tailscale `0.27.1` · Terminal & SSH `10.0.2` · File editor `5.8.0`
- Репозиторії add-on: HACS, hassio-addons, Music Assistant, ESPHome

### Масштаб
- **46 пристроїв** (Tuya 7, Tailscale 14, HA 5, телефони/Google/Apple, ін.)
- **614 сутностей** (mobile_app 364, tailscale 150, hassio 35, tuya 25, …)
- Кімнати: Bedroom, Kitchen, Living Room, Офіс Грушевського
- Дашборди: `map`, `vorota-grushevskogo`
- Особи: 4
- Скрипт: `open_office_gate_pulse` (реле `switch.gate_operation`, імпульс 1 с)
- `configuration.yaml`: `default_config`, themes, http з `trusted_proxies`
  (`172.30.33.0/24` — внутрішня supervisor-мережа), automations порожні (все через UI)

---

## Залізо

| Параметр | Значення |
|---|---|
| Модель | Mac mini M4 (Apple Silicon, ARM64) |
| RAM / SSD / macOS | ⬜ уточнити |
| Хост у Tailscale | `home-srv` (100.109.200.1), tag:server, offers exit node |

> HAOS bare-metal на Apple Silicon неможливий — лише у VM (UTM + образ `generic-aarch64`).

---

## Гіпервізор: UTM

- **UTM** (безкоштовний, QEMU backend) — найнадійніший шлях для HAOS на Apple Silicon
- QEMU, не Apple Virtualization (потрібен UEFI-boot)

## HAOS образ

- `haos_generic-aarch64-<версія>.qcow2.xz` з
  https://github.com/home-assistant/operating-system/releases
- Брати версію **≥ 2026.3** (бекап зроблено на 2026.3.4 — нижчу не відновлювати)
- `xz -d haos_generic-aarch64-*.qcow2.xz`

## Конфігурація VM в UTM

| Параметр | Значення |
|---|---|
| Тип / backend | Other (ARM64) / QEMU |
| Boot | UEFI |
| CPU / RAM | 2 ядра / 2–4 GB |
| Диск | імпорт `haos_generic-aarch64.qcow2` |
| Мережа | **Bridged** — HA отримує власний IP у LAN |

---

## Мережа

| Параметр | Значення |
|---|---|
| IP | ⬜ **статичний** (важливо для SIA :8124 і localtuya) |
| VLAN | ⬜ кандидат **VLAN 40 IoT** (`10.10.40.0/24`) — там Tuby/камери/панель |
| DNS | 10.10.30.15 (Pi-hole) — ⬜ підняти, бо помер разом із хостом |

**Критично для відновлення:**
- **localtuya** тримає локальні ключі пристроїв → HA має бути в **тій самій L2-підмережі**,
  що й Tuya-пристрої (звідси Bridged + IoT VLAN). NAT/інший VLAN — ламає локальний доступ.
- **SIA Alarm** — охоронна панель надсилає події на HA `TCP :8124` → статичний IP +
  firewall-дозвіл від панелі.
- **go2rtc** камери — RTSP у тій самій мережі.

---

## Відновлення з бекапу

1. Розгорнути HAOS у UTM (UEFI, bridged, 2 cores / 2–4GB), дочекатися екрана onboarding
2. Обрати **«Restore from backup»** → завантажити
   `Automatic_backup_2026.3.4_2026-06-09_05.17_42002114.tar`
3. Ввести **ключ шифрування** (emergency kit) — без нього бекап не відкриється
4. Дочекатися відновлення (HACS, localtuya, дашборди, особи, інтеграції)
5. Перевірити після старту:
   - [ ] localtuya бачить Tuya-пристрої (та сама мережа!)
   - [ ] SIA: HA слухає `:8124`, панель достукується
   - [ ] go2rtc камери
   - [ ] mobile_app — можливо переавторизація 4 телефонів
   - [ ] Tailscale add-on піднявся (новий/той самий вузол)
   - [ ] скрипт `open_office_gate_pulse` / `switch.gate_operation`
   - [ ] Google Drive backup add-on знову вивантажує

> ⚠️ Ключ шифрування зберегти надійно (1Password тощо) — без нього майбутні
> automatic backups так само не відновити.

---

## Радіо (Zigbee / Thread) — на майбутнє

Зараз радіо немає — все по WiFi/мережі (Tuya WiFi, камери, SIA через мережу).
Якщо додаватимеш Zigbee/Thread:
⚠️ USB-passthrough на Apple Silicon UTM ненадійний → брати **мережевий координатор**
(SLZB-06, Ethernet/PoE), не USB-стік.

---

## macOS host (`home-srv`) — «завжди працює»

- Автологін користувача
- Заборона сну:
  ```bash
  sudo pmset -a sleep 0 disablesleep 1 powernap 0
  sudo pmset -a autorestart 1
  ```
- Автостарт VM при вході (UTM "Start automatically" або `utmctl start <UUID>` у LaunchAgent)
- Перевірити автозапуск після ребуту

---

## Бекапи HA

- **Google Drive backup** уже був налаштований (і врятував ситуацію) — відновиться з бекапу,
  перевірити що знову працює
- HAOS має Supervisor → за бажання додати Samba Backup на майбутній NAS
- ⚠️ **Зберегти ключ шифрування бекапів** окремо від самих бекапів

---

## Ключові рішення та обґрунтування

- **Відновлення з Google Drive бекапу**, а не з PBS/ZFS — PBS-бекапи замкнені на мертвому
  хості; Google Drive-копія незалежна й доступна (цінність offsite-копії підтверджена)
- **HAOS у VM, не HA Container** — паритет: Supervisor, add-ons, HACS, повне restore
- **UTM/QEMU** — надійний UEFI-boot для HAOS
- **Bridged + IoT VLAN, статичний IP** — вимога localtuya (локальні ключі) і SIA (:8124)
- **Окреме залізо (Mac mini)** — HA не залежить від крашів Proxmox

---

## TODO

- [x] Дістати й розшифрувати бекап, звірити конфігурацію (2026-06-09)
- [ ] Уточнити Mac mini (RAM/SSD/macOS) і VLAN/статичний IP
- [ ] Підняти Pi-hole/DNS (помер із хостом) або тимчасовий DNS
- [ ] Встановити UTM, завантажити образ `generic-aarch64` ≥ 2026.3
- [ ] Створити VM (UEFI, bridged, 2c/2–4GB)
- [ ] Restore from backup + ключ шифрування
- [ ] Звірити localtuya / SIA / go2rtc / mobile_app / Tailscale (чеклист вище)
- [ ] Налаштувати автологін + без сну + автостарт VM
- [ ] Перевірити Google Drive backup
- [ ] Зберегти ключ шифрування в менеджер паролів
- [ ] (майбутнє) мережевий Zigbee/Thread координатор за потреби

---

## Статус

- [x] Підхід визначено: HAOS у VM (UTM/QEMU) на Mac mini M4
- [x] Бекап здобуто з Google Drive, розшифровано, конфігурацію задокументовано
- [ ] VM створено
- [ ] Відновлено з бекапу
- [ ] Інтеграції звірено (localtuya/SIA/go2rtc/mobile_app)
- [ ] Хост налаштовано (автостарт, без сну)
- [ ] Працює стабільно
