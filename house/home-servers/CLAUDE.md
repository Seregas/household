# Proxmox Server Management

## Сервер

- **Hostname:** pve (Tailscale: 100.120.149.7, pve.mining-owl.ts.net)
- **Hardware:** TOPC PHX mini-PC, AMD Ryzen 7 PRO 7840HS, 16 cores, 64GB RAM, NVMe 931GB
- **OS:** Proxmox VE 9.2.3, Debian 13 (trixie), kernel 6.17.13-11-pve (pinned)
- **ZFS:** rpool (148GB, системний), vmstore (781GB, /vmstore — переважно для TrueNAS system disk)

## SSH доступ

```bash
ssh pve   # MacBook key (~/.ssh/pve_admin)
```

- Парольний SSH вимкнено
- Authorized keys: MacBook (pve_admin), iPhone (Termius)
- Tailscale DNS: pve.mining-owl.ts.net

## VM / CT

| VMID | Назва | Тип | Стан | RAM | Диски |
|------|-------|-----|------|-----|-------|
| 110 | pihole | LXC | running | - | local-zfs |
| 111 | haos-ck | QEMU | running | 4GB | local-zfs |
| 100 | windows10 | QEMU | stopped | 32GB | **truenas-nfs** |
| 120 | truenas | QEMU | running | 16GB | vmstore (system), passthrough HDDs |
| 130 | pbs | LXC | running | 4GB (cap) | local-zfs (OS) + NFS datastore |
| 150 | genomics | QEMU | stopped | 28GB | **truenas-nfs** (всі диски) |

## Мережева архітектура

### VLAN (MikroTik RB5009UPr+S+)

| VLAN | Назва | Підмережа | Gateway |
|------|-------|-----------|---------|
| 10 | Management | 10.10.10.0/24 | 10.10.10.1 |
| 20 | LAN | 10.10.20.0/24 | 10.10.20.1 |
| 30 | Servers | 10.10.30.0/24 | 10.10.30.1 |
| 40 | IoT | 10.10.40.0/24 | 10.10.40.1 |
| 50 | Guest | 10.10.50.0/24 | 10.10.50.1 |

### Proxmox мережа

- `vmbr0` → eno1 → MikroTik ether6 — VLAN-aware, VLAN 30 (Servers)
  - `vmbr0.30` — 10.10.30.10/24 (Proxmox management)
- `vmbr1` → enp4s0 → MikroTik ether7 — VLAN-aware, VLAN 30 (**виділений для TrueNAS**)
  - маршрут до 10.10.20.0/24 через 10.10.30.1 (статичний)

### Сервіси в мережі — IP та веб-інтерфейси

| Сервіс | Хост / VM | IP (VLAN 30) | Веб-інтерфейс / доступ |
|--------|-----------|--------------|------------------------|
| Proxmox VE | pve | 10.10.30.10 | https://10.10.30.10:8006 |
| Proxmox Backup Server | pbs (LXC 130) | 10.10.30.12 | https://10.10.30.12:8007 |
| Pi-hole | pihole (LXC 110) | 10.10.30.15 | http://10.10.30.15/admin |
| TrueNAS SCALE | truenas (VM 120) | 10.10.30.20 | https://10.10.30.20 (або https://nas.home.arpa) |
| Jellyfin | app на TrueNAS (120) | 10.10.30.20 | http://10.10.30.20:30013 (TrueNAS nodeport; 8096 — внутрішній порт контейнера) |
| Home Assistant | haos-ck (VM 111) | DHCP | http://100.115.199.25:8123 (Tailscale) або DHCP-IP:8123 |
| MikroTik RB5009 | router | 10.10.30.1 (gw VLAN30) | WebFig http://10.10.30.1 / Winbox; mgmt також 10.10.10.1 |

**Порти-довідник:** Proxmox VE `8006` · PBS `8007` · TrueNAS `443` · Jellyfin `30013` (TrueNAS nodeport) ·
Pi-hole `80` (/admin) · Home Assistant `8123` · SMB `445` · NFS `2049`.

**Tailscale (mining-owl.ts.net):** pve `100.120.149.7` · haos-ck `100.115.199.25` · mbp `100.80.112.38`
(детальніше — розділ "Tailscale мережа" нижче). PBS (130) у Tailscale немає — доступ лише локально/через subnet-router pve.

### Tailscale мережа (mining-owl.ts.net)

- `pve` — 100.120.149.7 (tag:server, subnet router 10.10.30.0/24 + 10.10.20.0/24)
- `haos-ck` — 100.115.199.25
- `mbp` — 100.80.112.38

### DNS (MikroTik + Pi-hole)

- `pve.home.arpa` → 10.10.30.10
- `pihole.home.arpa` → 10.10.30.15
- `nas.home.arpa` → 10.10.30.20
- `pbs.home.arpa` → 10.10.30.12 (додати запис, якщо ще немає)

## Storages на Proxmox

| Storage | Тип | Розташування | Вміст | Використання |
|---------|-----|-------------|-------|-------------|
| local | dir | /var/lib/vz | ISO, snippets | мінімальне |
| local-zfs | zfspool | rpool | VM disks (haos, pihole) | ~12GB |
| vmstore | dir | /vmstore | TrueNAS system disk | ~14GB |
| truenas-nfs | nfs | 10.10.30.20:/mnt/tank8TB-mirror/pve-storage | iso, images, (vztmpl) | див. нижче |
| pbs | pbs | 10.10.30.12:8007, datastore "backup" (NFS на tank8TB-mirror/pbs-store) | backup (дедуп) | — |

### NFS mount (truenas-nfs)
```
nfs: truenas-nfs
    export /mnt/tank8TB-mirror/pve-storage
    path /mnt/pve/truenas-nfs
    server 10.10.30.20
    content backup,iso,images,vztmpl
    options vers=4,soft,timeo=100,retrans=3
    bwlimit default=150000
```

## Бекапи

| Job | VM/CT | Розклад | Retention | Сховище |
|-----|-------|---------|-----------|---------|
| daily | 110, 111, 150 | щодня 02:00 | keep-daily=7, keep-weekly=4 | **pbs** |
| weekly-windows | 100 | неділя 03:00 | keep-weekly=4 | **pbs** |

⚠️ **120 (TrueNAS) і 130 (PBS) виключені з усіх бекапів.** bwlimit джобів = 100000.
Старий шлях (raw vzdump на truenas-nfs) замінено на PBS — деталі в розділі "Сесія 2026-05-29".

## Відомі проблеми та стан

### Стабільність (критично)
- Сервер регулярно зависає (silent hard lockup, без логів)
- **Причина:** BIOS версія 0.01 від 07/05/2024 — alpha прошивка з багами ACPI
- **Обхідний шлях застосовано:** kernel параметри в `/etc/kernel/cmdline`:
  ```
  processor.max_cstate=1 pcie_aspm=off amd_pstate=passive
  ```
- **Рішення:** прошити новий BIOS (`AX6H2.rom` з сайту TOPC, TR-BIOS Ryzen7000-8000)
- Флешка підготовлена, потрібен фізичний доступ (монітор + клавіатура)
- Послідовність: Boot USB → EFI shell → `AfuEfix64.efi AX6H2.rom /CHECKME` → якщо OK → `/P /B /N`

### Kernel
- Pinned на **6.17.13-11-pve** (оновлено 2026-05-29; раніше було запінено 6.14, тому й не оновлювалось автоматично)
- Зміни kernel cmdline → `/etc/kernel/cmdline` + `proxmox-boot-tool refresh` (НЕ update-grub)

### RAM баланс (важливо!)
- Сервер має **64GB RAM**, ARC обмежено 8GB
- Правило: `sum(VM RAM) + ARC(8GB) + ~5GB host < 64GB`
- ⚠️ genomics(28GB) + truenas(16GB) + haos(4GB) ≈ 48GB; додавати windows10(32GB) НЕ МОЖНА
- НІКОЛИ не запускати windows10 + genomics + truenas одночасно під I/O
- Це лише ОДНА з причин крашів — повний каскад див. розділ "Сесія 2026-05-29"

## TrueNAS SCALE (VM 120)

- **Версія:** 25.10.3.1
- **IP:** 10.10.30.20 (статична, VLAN 30)
- **Web UI:** https://10.10.30.20 або https://nas.home.arpa
- **Мережа:** net0 → **vmbr1**, tag=30 (через enp4s0/ether7 — **виділений фізичний NIC**)
- **RAM:** 16GB (навмисно — баланс з іншими VM)
- **Диски VM:**
  - scsi0: 32GB (системний, vmstore — НЕ переносити, chicken-and-egg!)
  - scsi1: Toshiba MG10ADA800E 8TB (serial: 8572A048FTUJ) — passthrough
  - scsi2: Toshiba MG10ADA800E 8TB (serial: X4U0A07MFTUJ) — passthrough
- **ZFS пул:** `tank8TB-mirror` — Mirror (8TB usable), обидва 8TB HDD
- **Dataset для Proxmox:** `tank8TB-mirror/pve-storage`
- **ZFS ARC max:** 8GB (zfs_arc_max = 8589934592, тунінг через TrueNAS UI)
- **sync=disabled** на датасеті pve-storage (async writes)
- **Hostname:** nas, domain: home.arpa
- **Gateway:** 10.10.30.1, DNS: 10.10.30.15 (Pi-hole)

### Чому виділений NIC для TrueNAS
Якщо TrueNAS і Proxmox на одному bridge (vmbr0) — трафік іде через in-kernel
bridge forwarding зі швидкістю шини пам'яті (2-3 GB/s), минаючи фізичний NIC.
Це переповнює ZFS write buffer → crash. На vmbr1 (окремий NIC) трафік проходить
через фізичний 1Gbps комутатор → природне обмеження + ZFS backpressure.

### Правило переносу великих дисків
⚠️ **Ніколи не використовувати `qm move-disk`** для великих дисків на NFS — пише без
backpressure, crashує TrueNAS. Використовувати:
```bash
# Для файлів (vmstore → NFS):
rsync -av --sparse --progress /source/file.raw /mnt/pve/truenas-nfs/images/VMID/file.raw

# Для ZFS zvol (local-zfs → NFS):
# Крок 1: конвертуємо локально (без NAS)
qemu-img convert -p -f raw /dev/zvol/rpool/data/vm-ID-disk-N -O raw /vmstore/images/ID/temp.raw
# Крок 2: rsync з backpressure
rsync -av --sparse --progress /vmstore/images/ID/temp.raw /mnt/pve/truenas-nfs/images/ID/file.raw
# Крок 3: оновити конфіг VM, видалити temp і zvol
```

### Що ще треба налаштувати в TrueNAS

- [x] Створити датасети (media, timemachine) — 2026-05-29
- [x] Налаштувати SMB шари — 2026-05-29
- [x] Time Machine для MacBook — 2026-05-29
- [ ] Бекапи телефонів
- [ ] Доступ з VLAN 20 (LAN) через MikroTik firewall rules

## Розташування дисків VM

| VM | Диск | Storage | Розмір |
|----|------|---------|--------|
| haos-ck (111) | scsi0 (OS) + efidisk | local-zfs | 32GB + 1MB |
| truenas (120) | scsi0 (system) | vmstore | 32GB |
| truenas (120) | scsi1, scsi2 | passthrough HDD | 8TB × 2 |
| windows10 (100) | sata0 (OS) + efidisk + usb-flash.img | truenas-nfs | 100GB + 528KB + 1GB |
| genomics (150) | scsi0 (OS) | truenas-nfs | 64GB |
| genomics (150) | scsi1 (data) | truenas-nfs | 500GB |
| genomics (150) | efidisk | truenas-nfs | 1MB |

**Примітка:** `usb-flash.img` у Windows10 — образ флешки для прошивки BIOS (зберігати!)

## Що зроблено в цій сесії

- [x] Налаштовано backup завдання (daily + weekly)
- [x] Оновлено Proxmox 9.0 → 9.1.7
- [x] Оновлено всі пакети (170 штук)
- [x] ZFS pool upgrade до 2.4.1
- [x] ZFS scrub щонеділі о 02:00 (cron)
- [x] SSH ключі: MacBook + iPhone, парольний SSH вимкнено
- [x] Sleep/suspend вимкнено (`systemctl mask`)
- [x] `kernel.softlockup_panic=1`, `kernel.panic=10` (`/etc/sysctl.d/99-proxmox-stability.conf`)
- [x] Встановлено `rasdaemon` для логування hardware помилок
- [x] postfix aliases.db створено (`newaliases`)
- [x] Kernel параметри стабільності застосовано
- [x] TrueNAS SCALE встановлено і налаштовано (мережа, ZFS mirror пул)
- [x] Tailscale subnet router для 10.10.30.0/24 і 10.10.20.0/24
- [x] IP forwarding увімкнено (`/etc/sysctl.d/99-tailscale.conf`)
- [x] TrueNAS на виділеному NIC (vmbr1/enp4s0/ether7)
- [x] NFS storage підключено до Proxmox (truenas-nfs, 7.3TB)
- [x] Backup jobs перенесено на truenas-nfs
- [x] Всі бекапи перенесено з vmstore на NAS
- [x] Windows10 VM — всі диски перенесено на NAS
- [x] Genomics VM — всі диски перенесено на NAS
- [x] Debian cloud image перенесено на truenas-nfs/template/iso
- [x] vmstore розвантажено: було ~450GB, стало ~14GB

## Що ще треба зробити

- [ ] **Прошити BIOS** (флешка готова, потрібен фізичний доступ)
- [ ] Видалити старий ключ `root@pve` з `/root/.ssh/authorized_keys`
- [ ] Налаштувати PVE Firewall між VM і хостом
- [ ] Після оновлення BIOS — перевірити стабільність і розглянути kernel 6.17
- [ ] TrueNAS: датасети, SMB, Time Machine, бекапи телефонів
- [ ] MikroTik: firewall rules для доступу VLAN 20 → VLAN 30 (NAS)
- [ ] Перевірити genomics VM після запуску з NAS (перший старт)

## Корисні команди

```bash
# Стан системи
ssh pve 'pveversion && zpool status && qm list && pct list'

# Стан storages
ssh pve 'pvesm status'

# Бекапи
ssh pve 'pvesh get /cluster/backup --output-format yaml'

# Логи краші
ssh pve 'last -x | grep -E "shutdown|reboot|crash" | head -10'

# Hardware помилки
ssh pve 'rasdaemon -d'

# Температура
ssh pve 'sensors'

# NFS remount (якщо TrueNAS перезапускався)
ssh pve 'umount -f -l /mnt/pve/truenas-nfs; mount -t nfs -o vers=4,soft,timeo=100,retrans=3 10.10.30.20:/mnt/tank8TB-mirror/pve-storage /mnt/pve/truenas-nfs'
```

---

## Сесія 2026-05-29 — PBS, NAS-сервіси, розплутування крашів

### Справжня причина крашів (уточнення — це НЕ лише BIOS)
Нічні падіння — **каскад із трьох незалежних проблем**, не один баг:
1. **Memory overcommit.** sum(VM RAM) + ARC + host > 64GB. Правило:
   `sum(VM RAM) + ARC(8GB) + ~5GB host < 64GB`. НІКОЛИ windows10(32GB) +
   genomics(28GB) + truenas(16GB) одночасно.
2. **io_uring без iothread на passthrough-дисках** → весь хост у D-state.
   Фікс: scsi1/scsi2 TrueNAS → `iothread=1,aio=native,cache=none`.
   Правило: raw-block → `aio=native`; файл/NFS/ZFS-backed → `aio=io_uring`.
   (Диск genomics на NFS МАЄ бути io_uring, НЕ native — native блокується на NFS.)
3. **NFS write ceiling.** 2-HDD дзеркало ~200MB/s; повношвидкісний qemu-img/rsync
   через NFS забивав nfsd (sync-записи в ZIL) → "nfs: server not responding"
   (виглядає як зависання, але TrueNAS живий). Фікс: `sync=disabled` на
   pve-storage, `bwlimit default=150000` у storage.cfg, NFS `vers=4,soft,timeo=100,retrans=3`.

Після цих фіксів хост більше НЕ валиться — у гіршому разі підвисає лише гість.

### Інцидент vzdump (важливий урок)
Застряглий vzdump VM 120 (старт 02:00) заморозив TrueNAS: fsfreeze →
journald restart-storm → "Processes still around after SIGKILL". Відновлено БЕЗ
ребуту хоста: `umount -l -f /mnt/pve/truenas-nfs` → `qm unlock 120` → `qm start 120`.

⚠️ **ПРАВИЛО: VM 120 (TrueNAS) НІКОЛИ не включати в бекап-джоби.**
passthrough-диски vzdump не бекапить; fsfreeze живого NAS = дедлок.
Захист TrueNAS = експорт конфігу (System → General → Save Config) + переносний
ZFS-пул. Якщо помре TrueNAS — дані НЕ втрачені (`zpool import tank8TB-mirror`
на будь-якій ZFS-системі). Бекапи потрібні лише проти смерті ОБОХ дисків,
пошкодження пулу, випадкового видалення, втрати локації.

### Proxmox Backup Server (PBS) — LXC 130
- Привілейований LXC 130, Debian 13, nesting=1, 4GB cap / 2 cores, root 16GB local-zfs.
- IP **10.10.30.12** (VLAN 30). Web UI: https://10.10.30.12:8007 (root@pam).
- **nameserver 10.10.30.15** (Pi-hole) — інакше успадковує Tailscale MagicDNS
  100.100.100.100 (недоступний у контейнері) → DNS не працює.
- **Datastore `backup`** на `/datastore`.
- **NFS під datastore:** TrueNAS dataset `tank8TB-mirror/pbs-store`, експорт обмежено
  10.10.30.0/24, **Mapall=root:wheel** (НЕ maproot — PBS пише від `backup` UID 34).
- **Монтування:** хост → `/mnt/pbs-store` (fstab `_netdev,x-systemd.automount`),
  bind у контейнер: `pct set 130 -mp0 /mnt/pbs-store,mp=/datastore`.
- **Fingerprint:** `fc:2e:dd:b4:d6:01:a9:37:6a:ec:6b:69:18:05:d2:0a:23:7b:21:e7:8f:a2:82:bf:59:f9:eb:59:76:35:7f:e6`
- **Репо:** `deb http://download.proxmox.com/debian/pbs trixie pbs-no-subscription`.
- **GC:** запланувати (Datastore → Prune & GC) — без нього місце не звільняється.
- ⚠️ PBS (130) у бекапи НЕ включати (циркулярно).

### Jellyfin (TrueNAS app)
- **Доступ:** http://10.10.30.20:30013 (TrueNAS nodeport; 8096 — внутрішній порт контейнера).
- Apps pool = tank8TB-mirror. Host Path `/mnt/tank8TB-mirror/media` → `/media` (read-only).
- Jellyfin = **UID 568** → права: `setfacl -R -m g:568:rx /mnt/tank8TB-mirror/media`.
- Library paths — контейнерний шлях `/media/...`. "Allow remote connections" = ON
  (клієнти з інших VLAN — "remote"; не публікує в інтернет). Без GPU → CPU-транскод.

### SMB-шари
- **Time Machine:** `tank8TB-mirror/timemachine` (SMB preset, quota 4TiB refquota+quota,
  без ZFS-снапшотів). Purpose=Time Machine. Користувач `timemachine` (SMB only).
  macOS: `smb://10.10.30.20/TimeMachine`.
- **Media:** `tank8TB-mirror/media` (SMB preset, recordsize 1MiB, quota ~2.5TiB).

### Стратегічні рішення (майбутнє)
- **Bare-metal N100 NAS** (схиляюсь до купівлі): TrueNAS із VM на окреме залізо.
  Прибирає passthrough/VM-проблеми, звільняє 24GB, QuickSync → HW-транскод.
  ⚠️ SATA: нативний Intel або ASM1166, **уникати JMB585**. RAM 16/32GB, ECC немає.
  N100 НЕ вирішує брак RAM під важкі VM.
- **Offsite у Боровиці** (наступний проєкт): PBS-sync datastore туди. Зараз там лише роутер.
- **Memory budget:** поки TrueNAS у VM — пам'ять впритул. Right-sizing windows10 (32→16?)
  або апгрейд 96GB (2×48GB DDR5, BIOS 0.01 може не тренувати 48GB — перевірити).

### Зроблено 2026-05-29
- [x] Розплутано каскад крашів (memory + io_uring + NFS ceiling)
- [x] iothread=1,aio=native на passthrough scsi1/scsi2 TrueNAS
- [x] bwlimit default=150000 у storage.cfg
- [x] Kernel → 6.17.13-11-pve (pinned); Proxmox → 9.2.3
- [x] Відновлено vzdump-дедлок TrueNAS без ребуту
- [x] PBS встановлено (LXC 130, datastore на NFS-дзеркалі)
- [x] Бекап-джоби truenas-nfs → pbs (дедуп, bwlimit 100000), 120/130 виключено
- [x] TrueNAS: datasets media+timemachine, SMB, Time Machine
- [x] Jellyfin (read-only media, ACL UID 568)
- [x] Почищено старі vzdump (161GB) + orphan-диск VM100

### Команди (сесія)
```bash
# Відновлення vzdump-дедлоку TrueNAS (БЕЗ ребуту хоста):
ssh pve 'umount -l -f /mnt/pve/truenas-nfs; qm unlock 120; qm start 120'
# Стан PBS:
ssh pve 'pct exec 130 -- proxmox-backup-manager datastore list'
# Ручний бекап однієї VM на PBS (з ХОСТА):
ssh pve 'vzdump 110 --storage pbs --mode snapshot'
```
