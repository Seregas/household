:do { /ip firewall nat remove [find comment~"defconf"] } on-error={}
:do { /ip firewall filter remove [find comment~"defconf"] } on-error={}
:do { /ip dhcp-server remove [find] } on-error={}
:do { /ip dhcp-server network remove [find] } on-error={}
:do { /ip pool remove [find] } on-error={}
:do { /ip dhcp-client remove [find] } on-error={}
:do { /ip address remove [find] } on-error={}
/interface wireless security-profiles
add name=sp-fubar mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="N7k!pR9sL2xV4mH8"
add name=sp-guest mode=dynamic-keys authentication-types=wpa2-psk wpa2-pre-shared-key="chinazes-42"
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
/interface bridge vlan add bridge=bridge vlan-ids=10 tagged=ether1,ether2,bridge
/interface bridge vlan add bridge=bridge vlan-ids=20 tagged=ether1,ether2 untagged=wlan1,wlan2
/interface bridge vlan add bridge=bridge vlan-ids=50 tagged=ether1,ether2 untagged=wlan-guest24,wlan-guest5
/interface vlan add name=vlan10-mgmt interface=bridge vlan-id=10
/ip address add address=10.20.10.12/24 interface=vlan10-mgmt
/ip route add dst-address=0.0.0.0/0 gateway=10.20.10.1
/ip dns set servers=10.20.10.1
/tool mac-server set allowed-interface-list=all
/tool mac-server mac-winbox set allowed-interface-list=all
/interface bridge set bridge vlan-filtering=yes
:do { /user ssh-keys import public-key-file=mikrotik_boro_seregas_ed25519.pub user=admin } on-error={}
:do { /interface ethernet poe set ether2 poe-out=auto-on } on-error={}
