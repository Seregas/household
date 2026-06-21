# Боровиця — мережа (Wi-Fi + VLAN)

> Оновлено: 2026-06-18. **В експлуатації + централізоване керування.** Усі 3 точки керуються через **legacy CAPsMAN на hAP** (RouterOS 7.22.1; точки — 7.11.2 legacy wireless). Журнали: розгортання §10, міграція в CAPsMAN §11, смерть+заміна cAP#1 §12 (2026-06-18). Розділи §3–§9 нижче описують ПОПЕРЕДНЮ standalone-архітектуру — лишені як база для відкату/перезбірки точок; актуальна Wi-Fi-архітектура — у розділі «CAPsMAN» нижче.

## 1. Топологія (фінал)

```
WAN (PPPoE alden) ── hAP ax lite ether1
                      hAP ether2 ── cAP#1 (RBcAPGi-5acD2nD) ──(ether2 PoE-out)── cAP#2 (RBcAPGi-5acD2nD)
                      hAP ether3 ── wAP ac (RBwAPG-5HacT2HnD)
                      hAP ether4 ── (вільний; access VLAN20 для провідного пристрою)
```

MAC точок (звірено по live mgmt VID10): cAP `10.20.10.11` = `CC:2D:E0:ED:18:44`, cAP `10.20.10.12` = `CC:2D:E0:ED:1A:38`, wAP `10.20.10.13` = `CC:2D:E0:85:BE:6F`. hAP ether3 = `78:9A:18:19:AF:AE`.

Живлення ланцюга: пасивний гігабітний інжектор MikroTik 24 В / 1.2 А (28.8 Вт) у cAP#1; cAP#1 передає живлення на cAP#2 через ether2 PoE-out (auto-on). Запасу вистачає (~13 Вт навантаження). Застереження: на 24 В просадка на довгих прогонах помітніша — якщо cAP#2 перезавантажується, перевірити довжину/якість кабелю.

## Кабелі та прокладка точок (фізика)

Усі три прогони несуть **PoE (живлення+дані)**, тож якість міді важливіша за категорію.

**Спільне:** лише **100% мідь (solid copper), НЕ CCA** (мідь-плак. алюміній — просадка PoE, нагрів); Cat5e достатньо, **Cat6 (23 AWG)** краще для довгих PoE-прогонів; одножильний (solid). 24 В passive PoE просідає на довжині — cAP#2 у кінці ланцюга найвразливіша.

**hAP → cAP#1 (дім):** звичайний внутрішній Cat5e/6 solid copper. Головне — щоб мідь, не CCA.

**hAP → cAP#2 (через горище, у гофрі):** solid copper Cat5e/6; гофра захищає від гризунів і механіки. Неопалюване горище = перепади температур (влітку 50–70 °C під дахом), у сухій гофрі прийнятно; не герметизувати наглухо з обох кінців (конденсат). Живлення: cAP#2 живиться passthrough від cAP#1 (24 В) — на довгому прогоні можливі ребути; надійніше **окремий інжектор для cAP#2** у прибудові, якщо там є розетка.

**hAP → wAP (вулиця) — ⚠️ ПЛАН, НЕ ВИКОНАНО (станом на 2026-06-09):**
> Прогон ще не прокладено. Ймовірно спершу **повітрям** (тимчасово), закопування — згодом і **під питанням** (може трохи повисіти). Нижче — погоджене рішення, коли дійде до прокладки.
- **Кабель:** зовнішній **UTP cat5e/6, цільна мідь (solid, НЕ CCA), PE-оболонка**; без екрана. Прогін ~15 м (hAP→сарай).
- **Без екрана (UTP, не FTP):** екран нема де нормально заземлити (земля лише в хаті, та й та довга/тонка). Незаземлений екран EMI не прибирає й може сам наводити на пари; від EMI тут рятує сама скрутка пар. FTP мав би сенс лише якби колись заземлити екран хоч з одного кінця.
- **Без розрядників:** розрядник без короткого локального заземлення — марний (довгий тонкий PE = індуктивність, не «земля» для кидка). Нормальної землі під ввід у хаті нема, у сараї землю не роблю; до того ж неприв'язана друга земля може **погіршити** міжбудинковий GPD. wAP живиться PoE від hAP і «висить» — сараю ні живлення, ні землі не треба. Ризик блискавки приймаємо; жертовний пристрій — hAP (роутер як кілок). Розрядники (EtherProtect 1000 ~264 грн / MikroTik RBGESP ~1212 грн) — лише якщо колись з'явиться нормальна локальна земля під ввід.
- **Повітрям:** лише на **тросі (messenger)** — кабель із вбудованим тросом або окремий сталевий трос + стяжки; голий Ethernet не вішати. Термінація надворі — у **герметичній коробці/гермовводі**.
- **У землю (якщо/коли):** UTP у **ПЕ-трубі** — труба = механіка + гризуни, тож **дорогий броньований direct-burial не потрібен** (труба його замінює). Але труба сама не тримає сухо (конденсат/просочування), тож кабель — **зовнішній PE solid copper**, не внутрішній PVC; за бажанням **гідрофобний (гелезаповнений)** на випадок затоплення труби. Залишити **протяжку** (перетягнути кабель без перекопування), кінці загерметизувати, невеликий ухил + дренаж у нижній точці, труба **окремо від 230 В** (≥20–30 см / перетин 90°), діаметр із запасом.
- **Живлення:** PoE wAP від hAP; на довгому прогоні краще інжектор **48 В/802.3at**, ніж 24 В passive.
- **Опційний апгрейд — оптика:** єдиний варіант із захистом від кидків **без** мідної петлі й без заземлення (гальванічна розв'язка). Тоді wAP живити локально + пара медіаконвертерів (~1.7–3.3 тис. грн). Поки **не розглядаємо**.
- **Орієнтовний бюджет (15 м):** зовнішній UTP cat5e PE ~25–30 грн/м, cat6 ~35 грн/м → кабель ~300–500 грн; труба окремо. Тобто варіант «труба» — економніший за броньований кабель у грунт.

## 2. VLAN / адресація

| VLAN | Підмережа | Шлюз | SSID | Призначення |
|---|---|---|---|---|
| 10 | 10.20.10.0/24 | .1 | — | Management |
| 20 | 10.20.20.0/24 | .1 | Fubar | Своя + smart (Shelly) |
| 50 | 10.20.50.0/24 | .1 | Chinazes | Гостьова (ізольована) |

Mgmt-адреси: hAP `.1`, cAP#1 `10.20.10.11`, cAP#2 `10.20.10.12`, wAP `10.20.10.13`. Усі SSID — WPA2-PSK.

## CAPsMAN — централізоване керування Wi-Fi (АКТУАЛЬНЕ, 2026-06-08)

**Чому legacy CAPsMAN.** Треба керувати всіма трьома точками з одного місця. Новий CAPsMAN (wifi-qcom) керує лише новим стеком: cAP ac (ARM/IPQ-4018) його тягнуть, але **wAP ac (RBwAPG-5HacT2HnD, mipsbe/QCA9556) — ні** (підтримується лише ревізія RBwAPG-5HacD2HnD). Тож єдиний шлях для всіх трьох — **legacy `/caps-man` на hAP**, що вимагає пакета `wireless` і вимикає онбордне AX-радіо hAP (`wireless` і `wifi-qcom` не співіснують на AX-пристрої). Повністю зворотно.

**Своп пакетів на hAP** (зроблено з reboot-стійким авто-rollback таймером, емуляція commit-confirm):
```rsc
/tool fetch url=https://download.mikrotik.com/routeros/7.22.1/wireless-7.22.1-arm.npk
/system package disable wifi-qcom
/system reboot
# після ребуту /caps-man доступний; онбордне AX зникло (прийнятно — воно лише дублювало cAP#1)
```
Відкат: `/system package enable wifi-qcom; /system package disable wireless` + reboot.

**Об'єкти контролера (hAP):**
```rsc
/caps-man security
add name=sec-fubar authentication-types=wpa2-psk encryption=aes-ccm passphrase="<FUBAR>"
add name=sec-guest authentication-types=wpa2-psk encryption=aes-ccm passphrase="<CHINAZES>"
/caps-man datapath
add name=dp-fubar local-forwarding=yes vlan-mode=use-tag vlan-id=20
add name=dp-guest local-forwarding=yes vlan-mode=use-tag vlan-id=50
/caps-man channel
add name=ch-2g-1  frequency=2412 band=2ghz-b/g/n
add name=ch-2g-6  frequency=2437 band=2ghz-b/g/n
add name=ch-2g-11 frequency=2462 band=2ghz-b/g/n
add name=ch-5g-36 frequency=5180 band=5ghz-a/n/ac extension-channel=Ceee
add name=ch-5g-44 frequency=5220 band=5ghz-a/n/ac extension-channel=eeCe
add name=ch-5g-48 frequency=5240 band=5ghz-a/n/ac extension-channel=eeeC
/caps-man configuration
add name=cfg-fubar-2g-cap1 ssid=Fubar country=ukraine security=sec-fubar datapath=dp-fubar channel=ch-2g-6
add name=cfg-fubar-2g-cap2 ssid=Fubar country=ukraine security=sec-fubar datapath=dp-fubar channel=ch-2g-1
add name=cfg-fubar-2g-wap  ssid=Fubar country=ukraine security=sec-fubar datapath=dp-fubar channel=ch-2g-11
add name=cfg-fubar-5g-cap1 ssid=Fubar country=ukraine security=sec-fubar datapath=dp-fubar channel=ch-5g-44
add name=cfg-fubar-5g-cap2 ssid=Fubar country=ukraine security=sec-fubar datapath=dp-fubar channel=ch-5g-36
add name=cfg-fubar-5g-wap  ssid=Fubar country=ukraine security=sec-fubar datapath=dp-fubar channel=ch-5g-48
add name=cfg-guest ssid=Chinazes country=ukraine security=sec-guest datapath=dp-guest
/caps-man manager set enabled=yes
```
(Паролі вводяться окремо, у файл не пишемо: sec-fubar passLen=16, sec-guest passLen=11.)

**Provisioning — по одному правилу на radio-MAC** (майстер Fubar за смугою + slave Chinazes):
```rsc
/caps-man provisioning
add radio-mac=CC:2D:E0:ED:18:46 action=create-dynamic-enabled master-configuration=cfg-fubar-2g-cap1 slave-configurations=cfg-guest
add radio-mac=CC:2D:E0:ED:18:47 action=create-dynamic-enabled master-configuration=cfg-fubar-5g-cap1 slave-configurations=cfg-guest
add radio-mac=CC:2D:E0:ED:1A:3A action=create-dynamic-enabled master-configuration=cfg-fubar-2g-cap2 slave-configurations=cfg-guest
add radio-mac=CC:2D:E0:ED:1A:3B action=create-dynamic-enabled master-configuration=cfg-fubar-5g-cap2 slave-configurations=cfg-guest
add radio-mac=CC:2D:E0:85:BE:71 action=create-dynamic-enabled master-configuration=cfg-fubar-2g-wap  slave-configurations=cfg-guest
add radio-mac=CC:2D:E0:85:BE:70 action=create-dynamic-enabled master-configuration=cfg-fubar-5g-wap  slave-configurations=cfg-guest
```

**Канальний план (закріплений per-AP):**

| radio-MAC | Точка | Смуга | Конфіг | Канал |
|---|---|---|---|---|
| CC:2D:E0:ED:18:46 | cAP#1 (дім) | 2.4 | cfg-fubar-2g-cap1 | **ch6** (2437) |
| CC:2D:E0:ED:18:47 | cAP#1 | 5 | cfg-fubar-5g-cap1 | **ch44** (80 МГц, блок 36–48, eeCe) |
| CC:2D:E0:ED:1A:3A | cAP#2 (прибудова) | 2.4 | cfg-fubar-2g-cap2 | **ch1** (2412) |
| CC:2D:E0:ED:1A:3B | cAP#2 | 5 | cfg-fubar-5g-cap2 | **ch36** (Ceee) |
| CC:2D:E0:85:BE:71 | wAP (сарай/вулиця) | 2.4 | cfg-fubar-2g-wap | **ch11** (2462) |
| CC:2D:E0:85:BE:70 | wAP | 5 | cfg-fubar-5g-wap | **ch48** (eeeC) |

2.4 — повне рознесення 1/6/11. 5 ГГц — спільний 80-МГц блок 36–48 з рознесеними контрольними підканалами (крізь стіни/відстань соти 5 ГГц майже не перетинаються, тож 80 МГц лишили заради швидкості). **Важливо:** смугу радіо визначати за фактичною `current-channel`, а не за зсувом MAC — порядок 2.4/5 у MAC різний на різних пристроях.

**Конверсія точки зі standalone у CAP** (через jump hAP→точка, ПО ОДНІЙ команді; `<capN-boro>` = cap1-boro/cap2-boro/wap-boro):
```rsc
/system backup save name=pre-cap dont-encrypt=yes
/export file=pre-cap
/system identity set name=<capN-boro>
/interface wireless remove [find name~"guest"]
/interface bridge port remove [find interface~"wlan"]
/interface bridge vlan set [find vlan-ids=20] untagged=""
/interface bridge vlan set [find vlan-ids=50] untagged=""
/interface wireless cap set enabled=yes interfaces=wlan1,wlan2 bridge=bridge discovery-interfaces=vlan10-mgmt caps-man-addresses=10.20.10.1
```
CAPsMAN сам додає динамічні wlan-порти з потрібним PVID (20/50) і **сам перезаповнює** `untagged` у bridge vlan по-PVID — очищення вище лише прибирає старі статичні прив'язки.

**Танець статичних масок:** при першому конекті CAP без відповідного provisioning-правила CAPsMAN створює СТАТИЧНІ master-інтерфейси з дефолтним каналом. Лік: додати правило за radio-MAC → `/caps-man interface remove [find name=capN]` (статичні) → `/caps-man radio provision [find]` → з'являються динамічні (D) з конфігом.

**Точки відкату:** `pre-capsman` (до свопу пакетів), `pre-chanplan` (після міграції, до закріплення каналів), `boro-capsman-done` (фінал) — на hAP і на Mac (`.rsc` = повний актуальний експорт, джерело істини).

---

> **⚠️ Розділи §3–§9 нижче — ПОПЕРЕДНЯ standalone-архітектура (до 2026-06-08).** Лишені як база для відкату/перезбірки точок. Актуальні керування й канальний план — у розділі вище. Зокрема: канали 2.4 змінились (тепер cAP#1=ch6, cAP#2=ch1, wAP=ch11), онбордне AX-радіо hAP вимкнене.

## 3. Канали 2.4 ГГц (20 МГц) — standalone (історичне)

cAP#1 = ch1 (2412), cAP#2 = ch6 (2437), wAP = ch11 (2462), hAP onboard = ch1 (ділить із cAP#1; вимкнути за потреби). 5 ГГц (cAP×2/wAP) — auto.

## 4. Роутер hAP ax lite — merge-скрипт

> Бекап: `/system backup save name=pre-vlan`. Застосовувати через Winbox-MAC або `/import` (переживе обрив). vlan-filtering — останнім. WAN/PPPoE/ZeroTier/NAT/ZT-SSH не чіпаємо.

```rsc
/ip dhcp-server remove [find name=defconf]
/ip dhcp-server network remove [find address=192.168.88.0/24]
/ip address remove [find address=192.168.88.1/24]
/ip pool remove [find name=default-dhcp]
/ip dns static remove [find name=router.lan]
/interface vlan
add name=vlan10-mgmt interface=bridge vlan-id=10
add name=vlan20-fubar interface=bridge vlan-id=20
add name=vlan50-guest interface=bridge vlan-id=50
/ip address
add address=10.20.10.1/24 interface=vlan10-mgmt
add address=10.20.20.1/24 interface=vlan20-fubar
add address=10.20.50.1/24 interface=vlan50-guest
/ip pool
add name=pool-mgmt ranges=10.20.10.100-10.20.10.150
add name=pool-fubar ranges=10.20.20.100-10.20.20.200
add name=pool-guest ranges=10.20.50.100-10.20.50.200
/ip dhcp-server
add name=dhcp-mgmt interface=vlan10-mgmt address-pool=pool-mgmt lease-time=1d
add name=dhcp-fubar interface=vlan20-fubar address-pool=pool-fubar lease-time=1d
add name=dhcp-guest interface=vlan50-guest address-pool=pool-guest lease-time=4h
/ip dhcp-server network
add address=10.20.10.0/24 gateway=10.20.10.1 dns-server=10.20.10.1
add address=10.20.20.0/24 gateway=10.20.20.1 dns-server=10.20.20.1
add address=10.20.50.0/24 gateway=10.20.50.1 dns-server=10.20.50.1
/interface wifi
set [find default-name=wifi1] .ssid=Fubar channel.frequency=2412 channel.width=20mhz security.authentication-types=wpa2-psk security.passphrase="ПАРОЛЬ_FUBAR" disabled=no
/interface bridge port set [find interface=ether2] pvid=1
/interface bridge port set [find interface=ether3] pvid=1
/interface bridge port set [find interface=ether4] pvid=20
/interface bridge port set [find interface=wifi1] pvid=20
/interface bridge vlan
add bridge=bridge vlan-ids=10 tagged=bridge,ether2,ether3
add bridge=bridge vlan-ids=20 tagged=bridge,ether2,ether3 untagged=ether4,wifi1
add bridge=bridge vlan-ids=50 tagged=bridge,ether2,ether3
/interface list member
add interface=vlan10-mgmt list=LAN
add interface=vlan20-fubar list=LAN
/ip firewall filter
add chain=input action=accept in-interface=vlan50-guest protocol=udp dst-port=53,67 comment="guest dns+dhcp" place-before=[find chain=input action=drop in-interface-list=!LAN]
add chain=input action=accept in-interface=vlan50-guest protocol=tcp dst-port=53 place-before=[find chain=input action=drop in-interface-list=!LAN]
add chain=forward action=drop in-interface=vlan50-guest out-interface-list=!WAN comment="guest only internet" place-before=[find chain=forward comment~"DSTNATed"]
/interface bridge set bridge vlan-filtering=yes
```

## 5. cAP#1 — ГОЛОВА ЛАНЦЮГА (обидва порти trunk, PoE-out)

> 7.11.2 legacy wireless. Reset-to-defaults → Winbox по MAC → вставити. ether1 = trunk uplink (живлення+дані від інжектора), ether2 = trunk downlink + PoE-out до cAP#2.

```rsc
:do { /ip firewall nat remove [find comment~"defconf"] } on-error={}
:do { /ip firewall filter remove [find comment~"defconf"] } on-error={}
:do { /ip dhcp-server remove [find] } on-error={}
:do { /ip dhcp-server network remove [find] } on-error={}
:do { /ip pool remove [find] } on-error={}
:do { /ip dhcp-client remove [find] } on-error={}
:do { /ip address remove [find] } on-error={}
/interface wireless security-profiles
add name=sp-fubar mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="ПАРОЛЬ_FUBAR"
add name=sp-guest mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="ПАРОЛЬ_CHINAZES"
/interface wireless
set wlan1 disabled=no mode=ap-bridge band=2ghz-b/g/n channel-width=20mhz frequency=2412 ssid=Fubar security-profile=sp-fubar country=ukraine
set wlan2 disabled=no mode=ap-bridge band=5ghz-a/n/ac channel-width=20/40/80mhz-Ceee frequency=auto ssid=Fubar security-profile=sp-fubar country=ukraine
add name=wlan-guest24 master-interface=wlan1 ssid=Chinazes security-profile=sp-guest disabled=no
add name=wlan-guest5 master-interface=wlan2 ssid=Chinazes security-profile=sp-guest disabled=no
:do { /interface bridge port remove [find interface=ether1] } on-error={}
:do { /interface bridge port remove [find interface=ether2] } on-error={}
:do { /interface bridge port remove [find interface=wlan1] } on-error={}
:do { /interface bridge port remove [find interface=wlan2] } on-error={}
:do { /interface bridge port remove [find interface=wlan-guest24] } on-error={}
:do { /interface bridge port remove [find interface=wlan-guest5] } on-error={}
/interface bridge port add bridge=bridge interface=ether1 pvid=1
/interface bridge port add bridge=bridge interface=ether2 pvid=1
/interface bridge port add bridge=bridge interface=wlan1 pvid=20
/interface bridge port add bridge=bridge interface=wlan2 pvid=20
/interface bridge port add bridge=bridge interface=wlan-guest24 pvid=50
/interface bridge port add bridge=bridge interface=wlan-guest5 pvid=50
/interface ethernet poe set ether2 poe-out=auto-on
/interface bridge vlan
add bridge=bridge vlan-ids=10 tagged=ether1,ether2,bridge
add bridge=bridge vlan-ids=20 tagged=ether1,ether2 untagged=wlan1,wlan2
add bridge=bridge vlan-ids=50 tagged=ether1,ether2 untagged=wlan-guest24,wlan-guest5
/interface vlan add name=vlan10-mgmt interface=bridge vlan-id=10
/ip address add address=10.20.10.11/24 interface=vlan10-mgmt
/ip route add dst-address=0.0.0.0/0 gateway=10.20.10.1
/ip dns set servers=10.20.10.1
/tool mac-server set allowed-interface-list=all
/tool mac-server mac-winbox set allowed-interface-list=all
/interface bridge set bridge vlan-filtering=yes
```

## 6. cAP#2 — ХВІСТ ЛАНЦЮГА

Як cAP#1, але: ether2 — НЕ trunk і НЕ живить далі (`poe-out=off`), mgmt `10.20.10.12`, 2.4 = ch6 (2437).

```rsc
# ...(блок 1 і Wi-Fi — як у cAP#1, але frequency=2437 на wlan1)...
# порти:
/interface bridge port add bridge=bridge interface=ether1 pvid=1
/interface bridge port add bridge=bridge interface=ether2 pvid=20
/interface bridge port add bridge=bridge interface=wlan1 pvid=20
/interface bridge port add bridge=bridge interface=wlan2 pvid=20
/interface bridge port add bridge=bridge interface=wlan-guest24 pvid=50
/interface bridge port add bridge=bridge interface=wlan-guest5 pvid=50
/interface ethernet poe set ether2 poe-out=off
/interface bridge vlan
add bridge=bridge vlan-ids=10 tagged=ether1,bridge
add bridge=bridge vlan-ids=20 tagged=ether1 untagged=wlan1,wlan2,ether2
add bridge=bridge vlan-ids=50 tagged=ether1 untagged=wlan-guest24,wlan-guest5
/interface vlan add name=vlan10-mgmt interface=bridge vlan-id=10
/ip address add address=10.20.10.12/24 interface=vlan10-mgmt
/ip route add dst-address=0.0.0.0/0 gateway=10.20.10.1
/ip dns set servers=10.20.10.1
/tool mac-server set allowed-interface-list=all
/tool mac-server mac-winbox set allowed-interface-list=all
/interface bridge set bridge vlan-filtering=yes
```

## 7. wAP ac — однопортова

Як cAP#2, але без ether2 (один порт), mgmt `10.20.10.13`, 2.4 = ch11 (2462).

```rsc
# ...(блок 1 і Wi-Fi — як вище, frequency=2462 на wlan1)...
/interface bridge port add bridge=bridge interface=ether1 pvid=1
/interface bridge port add bridge=bridge interface=wlan1 pvid=20
/interface bridge port add bridge=bridge interface=wlan2 pvid=20
/interface bridge port add bridge=bridge interface=wlan-guest24 pvid=50
/interface bridge port add bridge=bridge interface=wlan-guest5 pvid=50
/interface bridge vlan
add bridge=bridge vlan-ids=10 tagged=ether1,bridge
add bridge=bridge vlan-ids=20 tagged=ether1 untagged=wlan1,wlan2
add bridge=bridge vlan-ids=50 tagged=ether1 untagged=wlan-guest24,wlan-guest5
/interface vlan add name=vlan10-mgmt interface=bridge vlan-id=10
/ip address add address=10.20.10.13/24 interface=vlan10-mgmt
/ip route add dst-address=0.0.0.0/0 gateway=10.20.10.1
/ip dns set servers=10.20.10.1
/tool mac-server set allowed-interface-list=all
/tool mac-server mac-winbox set allowed-interface-list=all
/interface bridge set bridge vlan-filtering=yes
```

## 8. Порядок застосування (on-site)

1. Бекапи всіх пристроїв.
2. hAP cutover (Winbox-MAC або /import) → ноут на Fubar/ether4 → `10.20.20.x`.
3. cAP#1 (Winbox по MAC `CC:2D:E0:ED:1A:38`) → скрипт §5. Після неї стане видно cAP#2.
4. cAP#2 (Winbox по MAC) → §6.
5. wAP (Winbox по MAC `CC:2D:E0:85:BE:6F`) → §7.
6. Перевірка: клієнт на Fubar → `10.20.20.x` + інтернет; на Chinazes → `10.20.50.x`, інтернет є, до 10.20.20/10.20.10 нема; точки пінгуються `10.20.10.11/.12/.13`.

## 9. Факти зі сканування (2026-06-06, до розгортання — історичне)

- hAP: RouterOS 7.22.1, ще flat defconf (192.168.88.0/24) — cutover не застосований.
- Точки: RouterOS 7.11.2, **legacy wireless** (скрипти на `/interface wireless` коректні).
- ether2 і ether3 — лінк OK (RS). ether4 вільний.
- Точки в router-defconf, лізинг на WAN не тримають; дискаверяться по MNDP/MAC.

## 10. Журнал розгортання (2026-06-07 — ФІНАЛ)

**Статус: мережа в експлуатації.** Розгорнуто on-site по SSH.

Зроблено:
- hAP cutover застосовано через відчеплений планувальник `/import` + авто-rollback таймер (емуляція commit-confirm; бекап `pre-vlan.backup`). Перший імпорт впав на firewall-рядку (баг `!LAN`) — виправлено через `comment~"..."` та `[find where address~"..."]`, далі успішно. Перевірено: `vlan-filtering=yes`, стара 192.168.88.1 прибрана, шлюзи+DHCP VID10/20/50 підняті, гостьовий firewall на місці, WAN/PPPoE/ZeroTier/ZT-SSH не чіпані, всі клієнти (вкл. Shelly) на Fubar VID20. Таймер відкату знято після підтвердження.
- Усі 3 точки конвертовано у VLAN-aware dumb AP (`.11/.12/.13` пінгуються з hAP, mgmt-MAC на VID10, клієнти на VID20/VID50). Ланцюг cAP→cAP живиться. Stray-SSID «MikroTik» з defconf прибрано.
- Онбордове радіо hAP перейменовано Chinazes→Fubar (VID20), пароль уніфіковано (passLen=16 підтверджено) — усунуто небезпечний клеш SSID «Chinazes» (довірена vs гостьова).

Лишилось (робиться у Winbox, термінал не потрібен):
1. **Паролі wAP `10.20.10.13`** — ще плейсхолдери. Winbox по IP → New Terminal:
   `/interface wireless security-profiles set sp-fubar wpa2-pre-shared-key="<FUBAR>"`
   `/interface wireless security-profiles set sp-guest wpa2-pre-shared-key="<CHINAZES>"`
2. **Перенаправити Shelly та IoT на SSID «Fubar»** з уніфікованим паролем (раніше були на старій онбордовій «Chinazes»; після перейменування/зміни пароля інакше відваляться або сядуть у гостьову VID50).

Граблі (на майбутнє):
- ed25519-ключ **не імпортується** на точках 7.11.2 («wrong format») — SSH-доступ лише на hAP (7.22.1); для точок — Winbox/MAC або RSA-ключ.
- Точки на mgmt VID10 НЕ видно в Winbox Neighbors з Fubar/VID20 (MNDP — L2, не ходить крізь VLAN) — конектись по IP.
- Багаторядкова вставка в термінал точки рветься на першій помилці → лише `/import file-name=...` після завантаження через Winbox Files.
- Рядок `/interface ethernet poe set ether2 poe-out=...` у середині скрипта може обірвати виконання — ставити в кінець, у `:do {...} on-error={}`.

## 11. Журнал: міграція в legacy CAPsMAN (2026-06-08)

**Статус: усі 3 точки під CAPsMAN, керування централізоване.** Зроблено віддалено по ZeroTier (SSH на hAP), точки — через jump з термінала hAP.

Зроблено:
- Своп пакетів hAP (`wifi-qcom`→`wireless`) з reboot-стійким авто-rollback планувальником: якщо за 15 хв після ребуту нема маркера `capsman-keep` — повернути wifi-qcom і ребут назад. Маркер виставлено, відкат знято.
- Підняв legacy-контролер (див. розділ CAPsMAN). Конвертував точки в порядку wAP → cAP#2 → cAP#1.
- Закріпив канали per-AP: 1/6/11 на 2.4; контроль 36/44/48 у 80-МГц блоці на 5 ГГц. Прибрав тимчасові загальні конфіги/канали-списки.

Граблі / уроки:
- **Новий CAPsMAN не бере wAP ac (mipsbe)** — звідси legacy + вимкнене онбордне AX hAP.
- **Точки недосяжні напряму** (ні з Mac, ні з офісу; ed25519 точки не беруть) — зміни лише через `/system ssh <ip>` з ТЕРМІНАЛА hAP, по одній команді.
- **⚠️ Запобіжник jump (був інцидент):** одна спроба jump на cAP#1 не під'єдналась, і весь блок конверсії (включно з `/system reboot`) виконався на самому hAP — той перейменувався в `cap1-boro`, очистив `untagged` на vid20, перезавантажився. Відновлено повністю (identity → `MikroTik-Boro`, `vid20 untagged=ether4,wifi1`; бекап `pre-capsman` був напоготові). Ознака провалу jump: запрошення `seregas@…` замість `admin@…`. **SOP: після jump перевір `admin@` + `/system/routerboard print` (модель = cAP) ПЕРЕД будь-якими змінами.** Пощастило: небезпечні команди на hAP були майже no-op (нема legacy-wlan; транки — tagged, не untagged).
- **Смугу радіо — за фактичною `current-channel`**, не за зсувом radio-MAC (порядок 2.4/5 у MAC різний: на cAP#2 :3A=2.4/:3B=5, на wAP навпаки).
- **Авто-вибір зі списку частот не розводить точки** — кілька сідають на той самий «найкращий» канал. Для чистого 1/6/11 — жорстке закріплення per-AP (окремі одночастотні канали + по конфігу на точку/смугу).
- **Танець статичних масок** при першому конекті без правила (див. розділ CAPsMAN).
- `/import` для скриптів-файлів, не вставка в термінал. Filesystem/DC MCP періодично висне на 4 хв — допомагає повний перезапуск Claude Desktop.

## 12. Журнал: смерть cAP#1 після аварії живлення + заміна (2026-06-17/18)

**Статус: cAP#1 списано (несправне залізо), замінено на іншу (теж б/у) cAP ac. Мережу тримають cAP#2 + wAP. Wi-Fi працює.**

**Хронологія / діагностика:**
- Ранкове **брудне знеструмлення** Боровиці (лог hAP: `router rebooted without proper shutdown`). hAP піднявся повністю (WAN/PPPoE, VLAN, CAPsMAN). cAP#1 — ні.
- Симптом cAP#1: аплінк up на гігабіті, але **нуль L2-кадрів** (порожня MAC-таблиця на hAP, нема MNDP, mac-scan порожній, не пінгується, не join'иться). На точці — «горить лише ether1 LED, не вантажиться». Поведінка **інтермітентна**: іноді завантажувалась (join'илась, віддавала клієнтам), потім знову висла.
- Хибні сліди, відкинуті по черзі: (1) поганий контакт — reseat роз'ємів оживляв тимчасово, але не лікував; (2) живлення — **замінено БЖ, потім PoE-інжектор cAP#1 → не допомогло**; своп-тест (cAP#2 на місце cAP#1) показав, що проблема лишається на позиції, але cAP#2 на тому ж фідері працював → отже винен **сам cAP#1**.
- **Вирок дав Netinstall + стрес:** залили чисту прошивку (формат+запис без помилок) — і все одно **2-й холодний старт завис**. Чистий рефлеш знімає версію «софт/конфіг» → лишається залізо: **плаваюча несправність, найімовірніше NAND** (RouterBOOT живий → ether1 up, а підвантаження ОС із флешу виходить через раз). Версія користувача — **перегрів** (теж правдоподібно: працювала холодною, висла після прогріву). Точний механізм не визначено, але це **залізо**.
- Урок: **чистий Netinstall + інтермітентні зависання холодного старту = залізо, не конфіг.** Брудне знеструмлення може фізично пошкодити NAND. Reset/reseat, що оживляють на раз, ≠ полагоджено.

**Заміна:**
- cAP#1 → нова (б/у) cAP ac. Початково **3/3 холодні старти чисті** (мрець сипався на 2-му). Усі точки **б/у** → перед бойовим деплоєм догнати стрес повніше (цикли + соак); тримати запасну як норму.
- Тимчасово **wAP заведено за cAP#2** (раніше — на hAP ether3): на cAP#2 порт **ether2 зроблено tagged-trunk'ом VLAN 10/20/50** (append через `:local t [...] ; set tagged=($t,ether2)`, щоб не зачепити ether1 і не обвалити ~10 живих клієнтів). wAP отримав VLAN10 → достукався до контролера → join (ch11/ch48). **Нештатно, на переробку.**

**Нова схема імен (непозиційна):** оскільки CAPsMAN провіжить за radio-MAC, а не за позицією, точкам дано текстові імена замість порядкових — щоб ставити в будь-якому порядку без плутанини:
- **Capybara** = cAP#2 (`CC:2D:E0:ED:1A:38`)
- **Capelin** = нова на заміну cAP#1
- **Wapiti** = wAP (`CC:2D:E0:85:BE:6F`)

(Перейменування identity — косметика, CAP-з'єднання не рве; зробити при нагоді.)

**Netinstall з macOS (спрацювало):** проєкт **tikoci/netinstall** через QEMU-VM. `brew install qemu crane wget`; у `/tmp/netinstall`: `sudo make run ARCH=arm PKGS="" IFACE=en6 VER=7.11.2` (sudo — у власному терміналі, DC sudo блокує). Точку — в Etherboot (затиснути reset → подати живлення → тримати, поки не з'явиться). Легасі-драйвер `wireless` **вшитий у `routeros-7.11.2-arm.npk`** (окремого пакета в 7.11.2 нема). cAP ac = **arm** (ARMv7/IPQ-4018). Свіжий дефолт cAP ac: ether1 = WAN (по дроту в нього `192.168.88.1` не дістати — керування через його Wi-Fi або Winbox по MAC).

**Незакрите:**
- Повний CAP-конфіг **Capelin** — у Боровиці: клонувати з Capybara (cAP#2), задати identity + унікальну mgmt-IP, перевірити join наживо.
- Перейменувати живі cAP#2/wAP у Capybara/Wapiti.
- Повернути wAP до штатної топології (або лишити за Capybara й задокументувати як норму) + переглянути канальний план, якщо точки переставлятимуться.
- Стежити за рештою (б/у залізо).
