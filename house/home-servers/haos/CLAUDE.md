# Home Assistant OS на Mac mini M4 (QEMU) — відновлено з бекапу

## Поточний стан (2026-06-21)

✅ **Працює.** HA відновлено з бекапу і запущено на Mac mini M4 у QEMU.

| | |
|---|---|
| Хост | Mac mini M4 — `home-srv` (Tailscale 100.109.200.1) |
| VM | QEMU 11.0.1, HAOS 18.0 (kernel 6.18.35-haos), hvf-прискорення |
| IP | **`10.10.30.11/24`** (статичний), gw `10.10.30.1`, VLAN 30 |
| Веб | http://10.10.30.11:8123 |
| Мережа VM | vmnet-bridged через `en0`, MAC `52:54:00:30:00:11` |
| SIA Alarm | `:8124` слухає ✅ (охоронна панель шле сюди) |
| Console | `telnet 127.0.0.1 6663` (лог: `~/haos-install/haos-serial.log`) |

> ⚠️ **Автостарту ще немає** — VM піднімається вручну (`sudo run-haos.sh`).
> Після ребуту mac-mini HA НЕ підніметься сам. LaunchDaemon — у TODO.

---

## Передісторія

Proxmox-хост помер (~2026-06-10), з ним TrueNAS-VM і PBS-бекапи на ZFS-пулі
(тимчасово недоступні). HA-VM `haos-ck` (VM 111) не воскресити. Урятував щоденний
**automatic backup** у Google Drive — `Automatic_backup_2026.3.4_2026-06-09`
(зашифрований securetar). Розшифровано emergency-kit ключем, відновлено на новому HAOS.

---

## Як запущено (QEMU CLI)

Пішли через **чистий QEMU**, а не UTM (UTM-VM «Virtual Machine» у системі — ймовірно
рештки старого HAOS, не чіпали). Причини: headless-сервер, повторюваність, скриптованість.

**Каталог:** `~/haos-install/` (поза git)
- `haos_generic-aarch64-18.0.qcow2` — образ (resized до 64 GiB)
- `edk2-aarch64-vars.fd` — writable UEFI vars (code: `/opt/homebrew/share/qemu/edk2-aarch64-code.fd`)
- `run-haos.sh` — launch-скрипт
- `haos-serial.log`, `haos.pid`, `qemu.out`

**Launch (`run-haos.sh`), ключове:**
```
qemu-system-aarch64 \
  -machine virt,accel=hvf,highmem=on -cpu host -smp 2 -m 3072 \
  -drive if=pflash,...,readonly=on,file=edk2-aarch64-code.fd \
  -drive if=pflash,...,file=edk2-aarch64-vars.fd \
  -drive if=virtio,format=qcow2,file=haos_generic-aarch64-18.0.qcow2 \
  -netdev vmnet-bridged,id=net0,ifname=en0 \
  -device virtio-net-pci,netdev=net0,mac=52:54:00:30:00:11 \
  -display none \
  -chardev socket,...,port=6663,server=on,wait=off,telnet=on,logfile=haos-serial.log \
  -serial chardev:ser0
```

**Запуск:** `sudo /Users/seregas/haos-install/run-haos.sh`
- **Потребує root** — `vmnet-bridged` (доступ до en0) працює лише від root.
- **Без `-daemonize`!** Він робить `fork()`, що ламає hvf/vmnet (objc fork-краш).
  Фон забезпечує `nohup … &` усередині скрипта.
- Скрипт сам зупиняє попередній екземпляр (`pkill -f 'qemu-system-aarch64 -name haos'`).

**Керування:**
- стоп: `sudo pkill -f 'qemu-system-aarch64 -name haos'`
- консоль HAOS: `telnet 127.0.0.1 6663` (login `root` → `ha …`)
- IP VM: `arp -an | grep 52:54:0:30:0:11`

---

## Мережа

- mac-mini `en0` — у **VLAN 30** (сам має `10.10.30.200`), тому bridged-VM теж у VLAN 30.
- VM: статичний **`10.10.30.11/24`**, gw `10.10.30.1`, задано через HA UI
  (*Settings → System → Network → enp0s1 → IPv4 Static*).
- DNS — тимчасово `1.1.1.1` (Pi-hole `10.10.30.15` помер разом із Proxmox).
- Доступ до `:8123` з MacBook через Tailscale поки **немає прямого маршруту** в
  10.10.30.0/24 (subnet-router `pve` мертвий). Варіанти: підняти `home-srv` як
  subnet-router, або заходити з пристроїв у LAN/VLAN 30.

---

## Поточна конфігурація (snapshot бекапу 2026-06-09)

HA версія бекапу — 2026.3.4 (відновлено на HAOS 18.0, новіший core — коректно).

### Призначення
Керування **офісом на Грушевського** — ворота, охоронна сигналізація, Tuya, камери.

### Інтеграції (15 доменів)
`tuya` + `localtuya` (локальні ключі) · `sia` (охоронна панель, **TCP :8124**) ·
`go2rtc` (камери) · `google_drive` (бекапи) · `tailscale` · `mobile_app` (4 телефони) ·
`met` · `radio_browser` · `shopping_list` · `sun` · `backup` · `hassio`

### HACS
`hacs/integration` 2.0.5 · `rospogrigio/localtuya` 5.2.5 · `NemesisRE/kiosk-mode` 10.0.0

### Add-ons
Tailscale 0.27.1 · Terminal & SSH 10.0.2 · File editor 5.8.0
(add-on repos: HACS, hassio-addons, Music Assistant, ESPHome)

### Масштаб
46 пристроїв · 614 сутностей · кімнати: Bedroom, Kitchen, Living Room, Офіс Грушевського ·
дашборди `map`, `vorota-grushevskogo` · 4 особи ·
скрипт `open_office_gate_pulse` (`switch.gate_operation`, імпульс 1 с)

---

## Звірка після відновлення

- [x] HA піднявся (`:8123` HTTP 200, не onboarding)
- [x] SIA Alarm `:8124` слухає
- [x] Статичний IP `10.10.30.11`
- [ ] localtuya бачить Tuya-пристрої (та сама мережа / firewall до :6668)
- [ ] go2rtc камери (потоки)
- [ ] mobile_app — можлива переавторизація 4 телефонів
- [ ] Tailscale add-on (новий вузол у tailnet)
- [ ] Google Drive backup знову вивантажує
- [ ] Перевірити роботу воріт (`open_office_gate_pulse`)

---

## Радіо (Zigbee / Thread) — на майбутнє

Радіо нема, все по WiFi/мережі. Якщо додавати — **мережевий координатор** (SLZB-06,
Ethernet/PoE), бо USB-passthrough у QEMU на Apple Silicon ненадійний.

---

## TODO

- [ ] **Автостарт VM** — LaunchDaemon (root, бо vmnet), щоб HA піднімався після ребуту
- [ ] macOS: заборона сну — `sudo pmset -a sleep 0 disablesleep 1 powernap 0; pmset -a autorestart 1`
- [ ] Відновити DNS (підняти Pi-hole деінде або лишити роутер/1.1.1.1)
- [ ] Доступ із MacBook: `home-srv` як Tailscale subnet-router 10.10.30.0/24
- [ ] Завершити звірку (localtuya / go2rtc / mobile_app / ворота)
- [ ] Зберегти ключ шифрування бекапів у менеджер паролів
- [ ] Прибрати/розібратися зі старою UTM-VM «Virtual Machine»
- [ ] (майбутнє) мережевий Zigbee/Thread координатор за потреби

---

## Статус

- [x] QEMU + образ HAOS 18.0 + UEFI підготовлено
- [x] VM запущено (vmnet-bridged, VLAN 30, hvf)
- [x] Відновлено з Google Drive бекапу
- [x] Статичний IP `10.10.30.11`, SIA `:8124` працює
- [ ] Автостарт (LaunchDaemon) + заборона сну
- [ ] Повна звірка інтеграцій (localtuya/go2rtc/mobile_app/ворота)
- [ ] DNS / Tailscale-маршрут
