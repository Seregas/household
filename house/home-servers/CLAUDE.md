# Proxmox Server Management

> **СТАТУС (24.06.2026):** Міграція на нове залізо **ASRock Rack AM5D4ID2 + Ryzen 9 9900X**.
> Стара система (TOPC PHX) виведена з роботи, але збережена як резервна — див. розділ
> **"АРХІВ: попередня система (TOPC PHX)"** у кінці документа.

## 📍 ДЕ МИ ЗАРАЗ (читати першим у новій сесії)

**Зроблено (сесія 24.06.2026 — від голого заліза до готової ноди):**
- ✅ Залізо зібрано: AM5D4ID2 + 9900X, 2×32 DDR5 (A1/B1), Samsung 990 PRO 1TB, NH-D12L
- ✅ Прошивки: BMC 1.05→**2.05.00** (закрито CVE-2024-54085), BIOS 10.09→**11.04** (AGESA 1.2.0.3b)
- ✅ Дані старої системи врятовано на зовнішній **Samsung T7** (`/mnt/backup/pve/`): pihole, haos, pbs,
  truenas-ОС(Jellyfin), genomics-virtio0 + конфіги. windows10/NAS-диски — на offline-NAS, фізично цілі.
- ✅ **Proxmox VE 9.2.3** встановлено начисто (ZFS rpool, єдиний пул на NVMe), оновлено (ядро 7.0.12, мікрокод Zen5)
- ✅ Перевірки: memtest 1 прохід 0 помилок; стрес-тест охолодження (65W→52°C, повний TDP→87°C без троттлінгу)
- ✅ Базове налаштування: репо no-subscription, sleep/suspend masked, ARC 6GB закріплено, timezone Kyiv
  - ⏸️ rasdaemon СВІДОМО відкладено до налаштування інтернету (потребує apt → робити разом з Tailscale/SSH, Етап 5)
- ✅ HDMI діагностовано: НЕ обмеження (amdgpu живий на ядрі 9.2), але консоль на ASPEED → фіз. HDMI чорний. KVM = основний канал.
- ✅ Роутер RB5009 підготовлено: **ether6→BMC, ether7→PVE host, обидва access VLAN 10**. WAN на ether4, ether1 вільний 2.5G.
- ✅ Документація: CLAUDE.md (цей файл) + bom-homelab-10inch.md оновлено. Бекап роутера після змін зроблено.

**Зроблено (сесія — CRS305 свіч заведено в мережу + перегляд плану портів):**
- ✅ **CRS305-1G-4S+IN у мережі.** RouterOS 7.20.8 (long-term). Remove Configuration → чистий старт.
  - Живлення: **PoE з RB5009 ether7** (poe-out auto-on, ~5.7 Вт). Вхід роутера 48.7 В (DC-jack) → PoE-out 802.3af/at-сумісний; CRS305 приймає 12–57 В.
  - Менеджмент: **10.10.10.2/24** на **ether1** (гіг), gw 10.10.10.1. Пароль admin задано.
  - Дані: **10G SFP-trunk** — sfp-sfpplus1(свіч) ↔ sfp-sfpplus1(роутер), tagged усі VLAN (10/20/30/40/45/50), vlan-filtering=yes, protocol-mode=rstp.
  - **Дизайн (важливо):** ether1 НЕ в бриджі — гіг лишається окремим mgmt+PoE-портом; у бриджі лише SFP-trunk. Тому нема петлі, RSTP нічого не блокує, менеджмент стабільний. (Перша спроба «ether1 у бриджі» давала RSTP-блок гіга → обрив MAC-сесії → відкат Safe Mode. НЕ повторювати.)
  - sfp2/3/4 свіча — вільні, під NAS / 10G ноди / робочу станцію (access-порти при підключенні).
- 🔄 **ЗМІНА плану портів RB5009** (нода обходиться одним кабелем — shared NIC; БУЛО: ether6→BMC, ether7→PVE host):
  - **ether6 → Proxmox-нода** (BMC .5 + хост .10 разом, shared NIC), frame-types=admit-all, pvid=10.
  - **ether7 → CRS305** (PoE + гіг-лінк).
  - **sfp-sfpplus1 → trunk до CRS305** (10G ноди тепер піде В СВІЧ на sfp2/3/4, не прямо в роутер).
- ✅ **Firewall:** додано `MGMT (VLAN10) → Internet` (forward/accept, src MGMT_NETS, out WAN) — лише вихід; inter-VLAN ізоляція ціла. Свідомо: VLAN 10 раніше був без інтернету. Потрібно для apt/Tailscale ноди + щоб admin-SSID мав інтернет.
- ✅ **admin-SSID `Fubar-Mgmt`** (CAPsMAN: cfg-mgmt/sec-mgmt/dp-mgmt) — нетегований → нативний VLAN 10. Локальний адмін-вхід у MGMT по Wi-Fi (з LAN/SRV у MGMT свідомо закрито). ⚠️ Пароль тимчасовий (світився) — змінити/прибрати.
- ✅ Lease MacBook закріплено статикою 10.10.20.200.

**📋 ЗАДАЧІ НА МАЙБУТНЄ (свіч / мережа):**
- [ ] **ether6 під ноду** (ПЕРЕД підключенням): додати ether6 у **untagged VLAN 10** + **tagged VLAN 30** (зараз ні те, ні те — VLAN 30 тегований на ether7, спадок «host на ether7»). Без цього shared-NIC нода (untagged) не запрацює.
- [ ] **Fubar-Mgmt пароль:** змінити на приватний (Winbox → WiFi → Security → sec-mgmt → Passphrase) АБО прибрати SSID (cfg-mgmt + sec-mgmt + dp-mgmt + з provisioning; re-provision блимне Wi-Fi).
- [ ] **sfp2/3/4 свіча → access-порти** під кожен пристрій при підключенні (NAS → VLAN 30; 10G ноди → trunk/VLAN за потребою; робоча станція → VLAN 20/30).
- [ ] **Tailscale для Черкас** — на Proxmox-ноді (Етап 2) як subnet-router VLAN 10. Рішення: **Черкаси = Tailscale**, Боровиця лишається ZeroTier (у ZT вичерпано ліміт маршрутів 2/1 + перетин 10.10.x між локаціями).
- [ ] **ether7 cleanup:** прибрати застарілі tagged-членства VLAN 20/30/40/45/50 з ether7 (тепер це лише гіг свіча, untagged VLAN 10). Нешкідливо, але охайніше.
- [ ] **Бекапи:** бекап конфігу роутера (після цих змін) + бекап свіча (`/export` або `/system/backup`) на Mac mini.
- [ ] **Свіч identity + SSH:** задати identity (напр. `home-switch`); коли буде overlay — ключ на свіч, вимкнути парольний SSH, alias.
- [ ] (Опц.) **RSTP root:** зробити роутер кореневим мостом (зараз корінь — свіч; підняти bridge priority роутера). Не критично.

**🔜 НАСТУПНИЙ КРОК:** фізичний монтаж ноди в стійку → далі по плану нижче ("ПЛАН ДОНАЛАШТУВАННЯ", Етапи 1-7).
Нода зараз НЕ в стійці, працювала через тимчасову мережу макбука (Internet Sharing 192.168.2.x).
Статика ноди: **10.10.10.10/24** (VLAN 10, gw 10.10.10.1). BMC цільова статика: **10.10.10.5**.

**⭐ ВИМОГА користувача (пріоритет, Етап 2):** доступ до BMC через інтернет (через Tailscale subnet-router,
НЕ прямий проброс!) + SSH до сервера. Деталі — в Етапі 2 плану.

**Гості ще НЕ відновлені** — це Етап 4 (після монтажу й мережі).

---


## Сервер (НОВИЙ — AM5D4ID2)

- **Hostname:** pve.home.arpa
- **Hardware:** ASRock Rack AM5D4ID2, AMD Ryzen 9 9900X (12 cores), **64GB RAM (2×32 DDR5-5600)**,
  Samsung 990 PRO 1TB NVMe. BMC/IPMI (ASPEED AST2600).
- **OS:** Proxmox VE 9.2.2, kernel 7.0.2-6-pve (рідне ядро 9.2 — нова нумерація, НЕ старе ядро).
- **ZFS:** **rpool — єдиний пул на весь NVMe** (ZFS RAID0, ashift=12, compress=on). Система + VM-диски
  в одному пулі (датасети ділять простір динамічно). БЕЗ дзеркала (PBS-бекапи покривають).
- **Прошивки:** BMC 2.05.00 (закрито CVE-2024-54085, CVSS 10.0), BIOS 11.04 (AGESA 1.2.0.3b).
- **CPU power:** Eco Mode 65W (менше тепла у вузькому 10" корпусі; підняти до 105W за потреби під genomics).
- **Тести 24.06 (відкритий стенд, NH-D12L):** memtest 1 прохід 0 помилок. Стрес-тест stress-ng (24 потоки):
  Eco 65W → Tccd 52-54°C (частоти ~3.0GHz); повний TDP → Tccd 85-88°C плато, БЕЗ троттлінгу (запас ~8°C
  до 95°C). Паста/контакт відмінні. Always-on режим: 65W (холодно/тихо) або 105W (~70-75°C під genomics);
  повний TDP постійно НЕ тримати (у корпусі запас стане тонким).
- **Мережа менеджменту:** i210 (гігабіт) → **VLAN 10**, IP **10.10.10.10/24**, gw 10.10.10.1.
  BMC → **VLAN 10**, статика 10.10.10.5 (або DHCP .50-99). Майбутня 10G SFP+ карта → робочий трафік.
- **BMC доступ:** H5Viewer (KVM), Serial-over-LAN. HDMI: amdgpu піднімається на ядрі 9.2 (НЕ обмеження),
  але консоль на ASPEED (primary) → фізичний HDMI чорний. KVM — основний канал, HDMI лишено як є.

> **Стан міграції:** система встановлена начисто, ZFS rpool ONLINE. Гості ще НЕ відновлені (бекапи на T7).
> Нода фізично ще не підключена в стійку. Наступні кроки — див. "TODO міграції" нижче.

## SSH доступ (новий — після підключення/відновлення)

```bash
ssh pve   # MacBook key (~/.ssh/pve_admin) — налаштувати на новій системі
```

- Парольний SSH вимкнути після налаштування ключів
- Tailscale — ставиться заново на чисту 9.2 (старий не переноситься), потім `tailscale up` + авторизація

## Мережа (НОВА — AM5D4ID2)

- **Менеджмент:** i210 (гігабіт) → **MikroTik ether7** (access VLAN 10, untagged) → **10.10.10.10/24**, gw 10.10.10.1.
- **BMC/IPMI:** окремий порт → **MikroTik ether6** (access VLAN 10, untagged) → 10.10.10.5 (статика) або DHCP (.50-99).
- **Майбутня 10G SFP+ карта** → робочий трафік (VLAN 30 servers + сторедж до NAS), trunk на sfp-sfpplus1.

> **ЗМІНА vs стара система:** на старому залізі ether6/ether7 були VLAN 30 (vmbr0 + виділений vmbr1 для TrueNAS).
> 24.06.2026 переналаштовано: **ether6/ether7 → VLAN 10** під нову ноду + BMC. Виділений NIC для TrueNAS
> більше не актуальний — TrueNAS переїжджає на окрему bare-metal NAS-плату (CWWK).

**Підготовка роутера ЗРОБЛЕНА 24.06.2026** (детально — у bom-homelab-10inch.md):
- ether6 → PVID 10, untagged VLAN 10 (BMC). ether7 → PVID 10, untagged VLAN 10 (PVE host).
- ether3 (AP) збережено в untagged VLAN 10. "Увіткнув патчкорд — запрацювало".
- WAN мігрував на ether4 (ether1 — вільний 2.5G резерв; WAN на 1G ether4 нічого не ріже).

### VLAN (MikroTik RB5009UPr+S+) — підтверджено з конфігу 24.06.2026

| VLAN | Назва | Підмережа | Gateway | DHCP-пул |
|------|-------|-----------|---------|----------|
| 10 | Management | 10.10.10.0/24 | 10.10.10.1 | 10.10.10.50-99 |
| 20 | LAN | 10.10.20.0/24 | 10.10.20.1 | 10.10.20.100-200 |
| 30 | Servers | 10.10.30.0/24 | 10.10.30.1 | 10.10.30.200-254 |
| 40 | IoT | 10.10.40.0/24 | 10.10.40.1 | 10.10.40.100-200 |
| 45 | IP Cameras | 10.10.45.0/24 | 10.10.45.1 | (Wi-Fi via AP) |
| 50 | Guest | 10.10.50.0/24 | 10.10.50.1 | 10.10.50.50-200 |

### Сервіси нової системи — IP

> Після відновлення гостей IP/доступи треба буде перепризначити під нову мережу (менеджмент VLAN 10).
> Сервіси (Pi-hole, HAOS, TrueNAS, PBS, Jellyfin) — у VLAN 30, IP-плани див. в архіві (стара система),
> уточнити при відновленні. DNS-імена `.home.arpa` зберігаються.

## ПЛАН ДОНАЛАШТУВАННЯ ПІСЛЯ МОНТАЖУ В СТІЙКУ

> Підготовку до стійки ЗРОБЛЕНО 24.06 (оновлення 9.2.3, ядро 7.0.12, мікрокод, sleep mask,
> ARC 6GB, timezone Kyiv). rasdaemon ЩЕ НЕ стоїть — відкладено до інтернету (Етап 5). Нижче — що робити ПІСЛЯ фізичного підключення, по етапах.

### Етап 1 — фізичне підключення + мережа (фундамент)
- [ ] Підключити патчкорд: нода (shared NIC, BMC+хост разом) → **ether6** (ОДИН кабель). ⚠️ Спершу підправити членство ether6: untagged VLAN 10 + tagged VLAN 30 (див. «ЗАДАЧІ НА МАЙБУТНЄ» вгорі). ether7 ТЕПЕР зайнятий свічем CRS305 (PoE+гіг), не нодою.
- [ ] Перевірити, що нода піднялась на статиці **10.10.10.10** (vmbr0), доступна з робочого місця (VLAN 20/30)
  - веб-морда: https://10.10.10.10:8006
- [ ] **BMC у VLAN 10:** веб-інтерфейс BMC → Network Settings → Network IP Settings → Static
  **10.10.10.5 / 24, gw 10.10.10.1**. (BMC = Shared NIC режим, підтверджено.) Після цього старий
  192.168.2.6 (Internet Sharing) відпаде — робити, КОЛИ вже є лінк у VLAN 10.
- [ ] Перевірити інтернет на ноді (через шлюз VLAN 10 → WAN ether4): `ping 8.8.8.8`, `ping google.com`

### Етап 2 — ВИМОГА: доступ до BMC через інтернет + SSH до сервера
> ⚠️ BMC НІКОЛИ не виставляти прямо в інтернет (проброс порту = критична діра, згадай CVE-2024-54085).
> Правильний шлях — через **Tailscale subnet-router** (зашифрований тунель, не голий інтернет).
- [ ] **Tailscale на ноду:** `curl -fsSL https://tailscale.com/install.sh | sh`
- [ ] Підняти як **subnet-router для VLAN 10** (щоб дістати BMC через тунель):
  `tailscale up --advertise-routes=10.10.10.0/24 --accept-routes`
  (за потреби додати й інші VLAN: 10.10.30.0/24 для сервісів, як було на старій системі)
- [ ] В адмінці Tailscale (login.tailscale.com) — **схвалити advertised route** 10.10.10.0/24
- [ ] Увімкнути IP forwarding на ноді: `/etc/sysctl.d/99-tailscale.conf` →
  `net.ipv4.ip_forward=1` + `net.ipv6.conf.all.forwarding=1`, потім `sysctl -p ...`
- [ ] **Перевірка доступу до BMC через інтернет:** з телефона/ноута (через Tailscale, з мобільного
  інтернету) відкрити https://10.10.10.5 → має відкритись BMC. ЦЕ Й Є ВИКОНАННЯ ВИМОГИ.
- [ ] **SSH до сервера:** скопіювати ключ MacBook на ноду (`ssh-copy-id` або вручну в
  `/root/.ssh/authorized_keys`), додати iPhone-ключ (Termius). Тоді `ssh pve` працює і локально,
  і через Tailscale (з будь-де). ВИМКНУТИ парольний SSH: `/etc/ssh/sshd_config` →
  `PasswordAuthentication no`, `systemctl restart ssh`.
- [ ] (Опц.) MagicDNS-ім'я ноди в Tailscale для зручності (типу pve.<tailnet>.ts.net)

### Етап 3 — мережеві мости під VLAN для гостей
- [ ] Вирішити trunk vs access на ether7: якщо гостям потрібні різні VLAN (HAOS, pihole, NAS-трафік) —
  зробити ether7 **trunk** на RB5009 + **VLAN-aware bridge** на Proxmox (vmbr0 vlan-aware).
  Якщо все в одному VLAN — лишити access. (Зараз access VLAN 10.)
- [ ] Налаштувати vmbr0 vlan-aware, призначити гостям потрібні VLAN-теги

### Етап 4 — відновлення гостей із бекапу (T7: /mnt/backup/pve/)
- [ ] Підключити T7, змонтувати (`mount -t exfat /dev/sda1 /mnt/backup`)
- [ ] Відновити: **pihole (110), haos-ck (111), pbs (130)** — повні, локальні
- [ ] Відновити **truenas-ОС (120, scsi0 32G з Jellyfin)** + **genomics (150, virtio0 64G)** —
  але БЕЗ NAS-дисків (вони на offline-NAS; прив'язки відновити, коли буде NAS)
- [ ] windows10 (100) — лише конфіг (диски на NAS, чекають NAS-плату)
- [ ] Команда: `qmrestore /mnt/backup/pve/vzdump-qemu-NNN-....vma.zst NNN --storage local-zfs`
  (для CT: `pct restore`). Перевірити мережу кожного гостя після відновлення.

### Етап 5 — гігієна / стабільність / моніторинг (потребує інтернету)
- [ ] **rasdaemon — ВСТАНОВИТИ** (ще НЕ стоїть, відкладено з 24.06 через брак інтернету):
  `apt install -y rasdaemon` → `systemctl enable --now rasdaemon` → перевірка `ras-mc-ctl --summary` + `ras-mc-ctl --error-count`
- [ ] ZFS scrub за розкладом (cron щонеділі, як на старій: `zpool scrub rpool`)
- [ ] Налаштувати сповіщення (email вже заданий sergey.slepchenko@gmail.com — перевірити postfix)
- [ ] (Опц.) kernel.panic=10 для авторебуту headless — за бажанням (на здоровому BIOS 11.04 менш критично)
- [ ] **НЕ переносити** старі cmdline-милиці (processor.max_cstate=1, pcie_aspm=off, amd_pstate=passive) —
  вони були під мертвий BIOS 0.01, на AM5D4ID2 шкодять енергоефективності

### Етап 6 — NAS-плата (CWWK), коли приїде
- [ ] TrueNAS bare-metal на CWWK (не VM!) — прибирає ZFS-on-ZFS і passthrough-проблеми
- [ ] PBS — або на NAS, або окремо; відновити бекап-джоби
- [ ] Перенести Toshiba 8TB пул на bare-metal TrueNAS (`zpool import tank8TB-mirror`)
- [ ] Відновити прив'язки NAS-дисків для windows10/genomics, NFS-сторедж до Proxmox

### Етап 7 — залізо / фіналізація
- [ ] Звірити 2×32 DDR5 у слотах A1/B1 за мануалом
- [ ] Друк корпусу (Bambu A1: ASA гаряча зона / PETG решта) + фінальна орієнтація NH-D12L
- [ ] (Майбутнє) 10G SFP+ карта → sfp-sfpplus1 (trunk, робочий трафік/сторедж); риг ADT-Link за потреби

### БЕЗПЕКА (окремо)
- [ ] Змінити пароль backup-користувача (`backup`@10.10.30.200) — відкритим текстом у скрипті make-backup
      на RB5009; перейти на SSH-ключ. Пароль засвітився в сесії 24.06.
- [ ] Перевірити firewall RB5009: доступ до VLAN 10 лише з VLAN 20/30 (правило є) + masquerade покриває
      10.10.10.0/24 (для інтернету/Tailscale на ноді)

---

## Сесія 2026-06-30 — NAS bare-metal (CWWK CW-NAS-ADLP): збірка й перші кроки

**Залізо (підтверджено по етикетках/memtest):**
- Плата **CWWK CW-NAS-ADLP**, CPU **i5-12450H** (8 фіз. ядер / 12 потоків — 4P+HT + 4E).
  Вхід живлення: DC-in **5.5×2.5 мм center-positive** АБО ATX 8-pin — це ОДИН вхід 12–24 В, два роз'єми (не дві шини).
- RAM: **Kingston FURY Impact DDR5 2×16 = 32 ГБ (KF556S40-16)**, двоканал, працює на 4788 MT/s (платформний максимум ~4800; модулі заводські 5600 CL40 — сідають до платформи). Не-ECC.
- HBA: **LSI 9217-8i** у PCIe x8. Кулер HBA (3-pin) → **SYSFAN3** (крутиться 100%, PWM нема — для гарячого 9217 норм). ⚠️ Перевірити IT-mode (диски мають бути сирі, не RAID).
- PSU: **Enhance ENP-7660B** (один блок). Плата живиться ATX 8-pin від PSU; для старту замкнено **PS_ON на 24-pin PSU** (на платі PS_ON нема — це не звичайна ATX-мати). Для headless: JATX_AT 1-2 АБО BIOS Restore AC Power Loss = Power On.
- KVM: **JetKVM** (чекаємо PoE-версію). Живити від **PoE RB5009**, НЕ від NAS — щоб міг піднімати вимкнену машину. ISO-mount по мережі → встановлення ОС без фізичної флешки. На SFP+ нема WoL → KVM = віддалена «кнопка живлення».

**memtest86 v11.7 (на цьому ж залізі):** 4 проходи, **0 помилок**. CPU max 72°C / RAM max 75°C (пік на Block move), із запасом до стелі (CPU 95 / RAM 85).

**КАРТА ДИСКІВ (карта відмов — звірити в TrueNAS Storage → Disks та `/dev/disk/by-id/`):**

| Диск | Роль | Серійник | WWN | SAS-кабель | Лоток |
|------|------|----------|-----|-----------|-------|
| Samsung SM863 120GB (MZ-7KM1200) | boot-mirror | S2HPNX0HB06060 | 5002538C4048A088 | SAS0 | HDD5 |
| Intel S3500 120GB (SSDSC2BB120G4) | boot-mirror | CVWL422401RN120LGN | 55CD2E404BC76A83 | SAS1 | HDD9 |
| Toshiba MG10ADA800E 8TB | tank8TB-mirror (data) | 8572A048FTUJ | — | (звірити) | (звірити) |
| Toshiba MG10ADA800E 8TB | tank8TB-mirror (data) | X4U0A07MFTUJ | — | (звірити) | (звірити) |

- SAS-маркування: **SAS0 = лотки HDD5-8, SAS1 = HDD9-12** (9217 обслуговує 5-12).
- Обидва SSD enterprise з PLP (power-loss protection) — правильно під ZFS boot. Здоров'я: Intel 96%, Samsung 99%.
- Принцип SAS: кожне дзеркало рознесене по двох кабелях/портах (відмова кабелю/порту не вбиває обидві половини).

**ЖИВЛЕННЯ ДИСКІВ (ENP-7660B, 2 SATA-кабелі × 2 роз'єми):**
- Рознести по членах дзеркал (НЕ «boot на один кабель, data на інший» — це вбило б data-дзеркало при відмові кабелю):
  - **SATA-кабель 1:** Samsung (boot) + Toshiba #1
  - **SATA-кабель 2:** Intel (boot) + Toshiba #2
- Причина: захист від відмови кабелю/роз'єму + балансування spin-up струму 8TB HDD. PSU один → це НЕ захист від смерті PSU (для того потрібен резервований блок), лише cable/connector-рівень.

**BIOS застосовано (цією сесією):**
- **Restore AC Power Loss → Power On** (Super IO / F81804) — автостарт після блекауту (headless).
- **CSM → UEFI only**; **Secure Boot → Disabled** (для ZFS; перемикач розблоковується заданням Administrator Password на AMI).
- **ACPI Auto Configuration → Disable → ACPI Sleep State → Disabled** (NAS не спить; нема WoL на SFP+).
- **Intel DTT → Disabled** (ноутбучна фіча, під Linux шкодить передбачуваності лімітів).
- **VT-d / Intel VMX → Enabled** (на майбутнє, прокидання).
- **C-states + SpeedStep + Speed Shift/HWP → Enabled** (idle-економія 24/7); Turbo на розсуд.
- **Hardware Monitor Fan Mode → Automatic**; **TPM (fTPM/PTT) → Enabled** (НЕ робити Clear).
- Boot performance mode — не чіпати (впливає лише на POST).

**ОС: bare-metal TrueNAS SCALE** (не VM, не Proxmox) — Етап 6. Прибирає passthrough/ZFS-on-ZFS, звільняє ~16 ГБ RAM на Proxmox-ноді (AM5D4ID2).

**ОНОВЛЕННЯ 30.06.2026 (кінець сесії — система піднята):**
- ✅ TrueNAS SCALE **25.10.4** встановлено на boot-mirror (Intel sda + Samsung sdb, 111.79 GiB кожен). У інсталяторі обидва SSD позначені, 8TB були ФІЗИЧНО ВІД'ЄДНАНІ (щоб не зачепити). Samsung мав `isw_raid_member` — TrueNAS затер при інсталяції.
- ✅ **LSI 9217-8i дошито UEFI boot-ROM** (`sas2flash.efi -b x64sas2.rom`, firmware НЕ чіпали). Тепер banner LSI на POST є, boot-запис є, система вантажиться нативно з дзеркала за HBA. Деталі — `lsi-9217-flash-guide.md`. **SAS Address: 500605B005CE13E0** (з наклейки).
- ✅ Система здорова, HBA + диски бачаться з ОС. NAS поки на столі, в мережу НЕ підключений.

**НАСТУПНІ КРОКИ (NAS) — коли в стійці:**
- [ ] Підключити 2× Toshiba 8TB (рознести SAS0/SAS1 + SATA-кабелі за схемою вище), звірити серійники з таблицею.
- [ ] **badblocks / довгий SMART** на обидва 8TB ПЕРЕД імпортом (з консолі: `smartctl`, бо в 25.10 SMART-UI прибрано).
- [ ] 10G DAC → CRS305 (access VLAN 30), IP 10.10.30.20 (nas.home.arpa). До того — веб-морда по DHCP-IP з тимчасового кабелю.
- [x] ~~Встановити TrueNAS на boot-mirror~~ — ЗРОБЛЕНО 30.06.
- [ ] ⚠️ **`tank8TB-mirror` — ІМПОРТ (Storage → Import Pool), НЕ створювати!** Дані на дисках. Звірити серійники перед будь-якою дією.
- [ ] Мережа: **10G SFP+ (82599ES) → CRS305 sfp2/3/4**, access **VLAN 30**; IP **10.10.30.20** (nas.home.arpa, як стара VM).
- [ ] Після: NFS/PBS-прив'язки до Proxmox; відновити SMB / Time Machine / Jellyfin (UID 568, ACL).

---

## Сесія 2026-06-30 (ч.2) — мережа під NAS (DHCP reservation + access VLAN 30)

**RB5009 — DHCP reservation для NAS (зроблено через `ssh home-router`):**
- Статичний lease: **`10.10.30.20` ↔ MAC `A8:B8:E0:06:27:B3`**, server `dhcp30`, comment "nas truenas (SFP+ port1)".
- NAS має 2× SFP+ (82599ES), MAC портів послідовні: **port1 `...27B3`** (зарезервований), port2 `...27B4` (вільний). DAC вмикати ЗАВЖДИ в port1, інакше адреса буде не та.
- Інтерфейс у TrueNAS лишити на DHCP (адресою керуємо з роутера, статику в NAS НЕ дублювати).
- DHCP-сервери RB5009: dhcp10/20/30/40/50 (vlanXX-*, poolXX-*). VLAN 30 = `dhcp30`/`vlan30-srv`/`pool30-srv` (пул .200-254; .20 — поза пулом, тому ідеально під reservation).

**CRS305 (тепер identity `10GbSwitch`) — access VLAN 30 на sfp-sfpplus2:**
- Бридж `bridge` (rstp, vlan-filtering=yes). Trunk = `sfp-sfpplus1` (tagged усі VLAN), ether1 = management (НЕ в бриджі).
- Додано `sfp-sfpplus2` у бридж: **PVID 30, frame-types=admit-only-untagged-and-priority-tagged** (access під NAS).
- VLAN 30 ВИНЕСЕНО в окремий bridge-vlan запис: `vlan-ids=30 tagged=sfp-sfpplus1 untagged=sfp-sfpplus2`. Решта (10,20,40,45,50) лишились у спільному записі (tagged sfp-sfpplus1). Причина: не можна додати untagged лише для 30, поки 30 «склеєний» з іншими в одному записі.
- Ланцюг VLAN 30: роутер(tagged)→trunk→свіч→sfp-sfpplus2(untagged)→NAS. `current-untagged` порожній доки порт неактивний (`I`) — норма, оживе з DAC.
- ⚠️ Свіч SSH/аліас ДОСІ TODO: Mac (VLAN 20) → 10.10.10.2 по SSH = таймаут (mgmt VLAN 10 закритий). Конфіг свіча йде через **Winbox (MAC-telnet)**, Сергій сам. Claude НЕ має доступу до свіча (підтверджено: known_hosts 0 записів про 10.10.10.2). Аліаси з іменами поки не чіпаємо (свіч один).

**ЩОБ ПІДНЯТИ NAS (фізика, без команд):** DAC `10GbSwitch sfp-sfpplus2` ↔ NAS **port1** (`...27B3`) → увімкнути → автоматом `10.10.30.20` → `https://10.10.30.20` з MacBook → далі ІМПОРТ tank8TB-mirror.

---

# АРХІВ: попередня система (TOPC PHX) — виведена з роботи 24.06.2026

> ⚠️ **Усе нижче описує СТАРУ систему** (TOPC PHX mini-PC, Ryzen 7 7840HS), яка **мігрована** на
> AM5D4ID2 (опис угорі). Збережено як резервну довідку — стара плата лишається робочою про запас.
> **IP-адреси, мережа (VLAN 30, ether6/7), BIOS-проблеми тут стосуються СТАРОГО заліза.**
> На новій системі: менеджмент у VLAN 10 (10.10.10.10), ether6/7 переналаштовані, BIOS AM5D4ID2 11.04
> без крашів BIOS 0.01. Цінні УРОКИ (io_uring/aio, NFS ceiling, memory budget, ZFS-on-ZFS, PBS) —
> лишаються актуальними архітектурно й переносяться на нову систему.

## VM / CT (стара система — для відновлення з бекапу)

| VMID | Назва | Тип | Стан | RAM | Диски |
|------|-------|-----|------|-----|-------|
| 110 | pihole | LXC | running | - | local-zfs |
| 111 | haos-ck | QEMU | running | 4GB | local-zfs |
| 100 | windows10 | QEMU | stopped | 32GB | **truenas-nfs** |
| 120 | truenas | QEMU | running | 16GB | vmstore (system), passthrough HDDs |
| 130 | pbs | LXC | running | 4GB (cap) | local-zfs (OS) + NFS datastore |
| 150 | genomics | QEMU | stopped | 28GB | **truenas-nfs** (всі диски) |

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
