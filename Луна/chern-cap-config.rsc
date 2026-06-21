# 2026-05-29 11:45:20 by RouterOS 7.11.2
# software id = W6YN-62XI
#
# model = RBcAPGi-5acD2nD
# serial number = 81CE0886A63A
/interface bridge
add comment="dumb-AP L2 bridge" name=bridge
/interface ethernet
set [ find default-name=ether2 ] poe-out=off
/interface wireless security-profiles
set [ find default=yes ] supplicant-identity=MikroTik
add authentication-types=wpa2-psk mode=dynamic-keys name=home \
    supplicant-identity=MikroTik
/interface wireless
set [ find default-name=wlan1 ] band=2ghz-b/g/n channel-width=20/40mhz-Ce \
    country=ukraine disabled=no distance=indoors frequency=auto installation=\
    indoor mode=ap-bridge security-profile=home ssid=Chern wireless-protocol=\
    802.11
set [ find default-name=wlan2 ] band=5ghz-a/n/ac channel-width=\
    20/40/80mhz-Ceee country=ukraine disabled=no distance=indoors frequency=\
    auto installation=indoor mode=ap-bridge security-profile=home ssid=Chern \
    wireless-protocol=802.11
/ip hotspot profile
set [ find default=yes ] html-directory=hotspot
/interface bridge port
add bridge=bridge interface=ether1
add bridge=bridge interface=ether2
add bridge=bridge interface=wlan1
add bridge=bridge interface=wlan2
/ip neighbor discovery-settings
set discover-interface-list=!dynamic
/ip dhcp-client
add comment="upstream lease" interface=bridge
/system clock
set time-zone-name=Europe/Kyiv
/system identity
set name=interlink-cap-chern
/system note
set show-at-login=no
/system routerboard settings
# Firmware upgraded successfully, please reboot for changes to take effect!
set auto-upgrade=yes
