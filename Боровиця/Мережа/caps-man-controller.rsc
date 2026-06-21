# ============================================================
# Боровиця — legacy CAPsMAN контролер на hAP (MikroTik-Boro)
# Phase B. Forwarding: LOCAL (точка тегує клієнта у VID20/50 і шле
#   тегованим у trunk; hAP уже тримає 10/20/50 на ether2/3 — на боці
#   hAP міняти нічого не треба).
# Паролі НАВМИСНО порожні — вписуються у Winbox (sec-fubar/sec-chinazes).
# Provisioning + CAP-режим точок — Phase C, на місці (див. низ файлу).
# ============================================================

/caps-man security
add name=sec-fubar    authentication-types=wpa2-psk encryption=aes-ccm group-encryption=aes-ccm passphrase=""
add name=sec-chinazes authentication-types=wpa2-psk encryption=aes-ccm group-encryption=aes-ccm passphrase=""

/caps-man datapath
add name=dp-fubar    bridge=bridge local-forwarding=yes vlan-mode=use-tag vlan-id=20
add name=dp-chinazes bridge=bridge local-forwarding=yes vlan-mode=use-tag vlan-id=50

/caps-man channel
add name=ch-2g1  band=2ghz-b/g/n frequency=2412
add name=ch-2g6  band=2ghz-b/g/n frequency=2437
add name=ch-2g11 band=2ghz-b/g/n frequency=2462

/caps-man configuration
add name=cfg-fubar-2g    ssid=Fubar    country=ukraine security=sec-fubar    datapath=dp-fubar    channel=ch-2g1,ch-2g6,ch-2g11
add name=cfg-chinazes-2g ssid=Chinazes country=ukraine security=sec-chinazes datapath=dp-chinazes channel=ch-2g1,ch-2g6,ch-2g11
add name=cfg-fubar-5g    ssid=Fubar    country=ukraine security=sec-fubar    datapath=dp-fubar    channel.band=5ghz-a/n/ac channel.control-channel-width=20mhz channel.skip-dfs-channels=yes
add name=cfg-chinazes-5g ssid=Chinazes country=ukraine security=sec-chinazes datapath=dp-chinazes channel.band=5ghz-a/n/ac channel.control-channel-width=20mhz channel.skip-dfs-channels=yes

/caps-man manager
set enabled=yes

/caps-man manager interface
add interface=vlan10-mgmt

# ============================================================
# PHASE C — НА МІСЦІ (цим імпортом НЕ виконується)
# 1) Provisioning на hAP (звірити проти /caps-man radio print):
#   /caps-man provisioning
#   add action=create-dynamic-enabled hw-supported-modes=gn master-configuration=cfg-fubar-2g slave-configurations=cfg-chinazes-2g
#   add action=create-dynamic-enabled hw-supported-modes=an master-configuration=cfg-fubar-5g slave-configurations=cfg-chinazes-5g
#   (якщо hw-supported-modes не зматчить — призначити конфіги вручну на /caps-man radio)
# 2) На кожній точці (cAP x2, wAP) — увімкнути CAP (вони вже на wireless-стеку):
#   /interface wireless cap set enabled=yes interfaces=wlan1,wlan2 \
#       discovery-interfaces=vlan10-mgmt caps-man-addresses=10.20.10.1 \
#       bridge=bridge certificate=request
#   (bridge=bridge — для local-forwarding; trunk/VLAN на точці лишаються як є)
# 3) Паролі у Winbox: /caps-man security set [find name=sec-fubar] passphrase=...
#                     /caps-man security set [find name=sec-chinazes] passphrase=...
# ============================================================
