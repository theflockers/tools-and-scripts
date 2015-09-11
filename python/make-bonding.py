#!/usr/bin/env python
# =============================================================================
#
# @name: makebonding.py
#
# @description: Create sys configuration for bonding interfaces
# @author: Leandro Mendes <leandro.mendes@dafiti.com.br>
#
# @changelog
#
# Tue Sep  1 00:50:28 BRT 2015 - Leandro Mendes<leandro.mendes@dafiti.com.br>
# - setting default gateway
# - bonding mode changed to 6 (balance-alb)
#
# Mon Aug 31 15:50:13 BRT 2015 - Leandro Mendes<leandro.mendes@dafiti.com.br>
# - configuration changed to not use Network Manager
# - script changed to fix IP address received from DHCP server with /22 CIDR
# - bonding mode changed to 5 (balance-tlb)
#
# =============================================================================
import os,sys
import socket
import re
from subprocess import call

network_sysconfig_dir = '/etc/sysconfig/network-scripts'

sys_class_net = '/sys/class/net'
exclude_regex = ['vnet','rhevm','lo','bond','vlan',';vdsmdummy;','virbr']
exclude_list  = []

print '=> Getting physical devices...'
ifaces_list = os.listdir(sys_class_net)
for iface in ifaces_list:
  for exclude in exclude_regex:
    if re.match(exclude, iface):
      exclude_list.append(iface)

clean_list = filter(lambda x: x not in exclude_list, ifaces_list)

def get_def_gw():
  rt_table = []
  r = open('/proc/net/route', 'r')
  for route in r.readlines():
    rt_table.append(route.split())
  r.close()

  dests = []
  gws = []
  i = 0
  for route in rt_table:
    dest = {}
    gw   = {}
    if i == 0:
      title = route
      i = i + 1
      continue

    dstlist  = map(lambda x: str(int("0x%s" % (x), 0)) ,re.findall('..', route[1]) )[::-1]
    dest     = '.'.join(dstlist)
    gwlist   = map(lambda x: str(int("0x%s" % (x), 0)) ,re.findall('..', route[2]) )[::-1]
    gw       = '.'.join(gwlist)

    dests.append({title[0]: route[0], title[1]: dest, title[2]: gw})
    i = i + 1

  for dest in dests:
    if dest['Destination'] == '0.0.0.0':
      return dest['Gateway']


def get_my_ip():
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  s.connect(("google.com",80))
  ip = s.getsockname()[0]
  s.close()
  return ip

def map_bond(bonds, idx):
  bidx   = 0
  map   = {}
  for i in range(2,10):
    if bidx == bonds:
       bidx = 0

    map[i] = bidx
    bidx = bidx+1

  return map[idx]

ifaces = {}
for iface in clean_list:
  i = int(open('%s/%s/ifindex' % (sys_class_net, iface) ).read())
  hwaddr = open('%s/%s/address' % (sys_class_net, iface) ).read()
  ifaces[i] = {'hwaddr': hwaddr.strip(), 'device': iface.strip() }

ifcount = len(ifaces)
bonds   = ifcount / 2

print '=> Gererating bonding configuration...'

# what's my ip?
my_ip = get_my_ip()
my_gw = get_def_gw()

# interface address
bhwaddr = []
for key,val in ifaces.iteritems():
  rest = key % bonds
  if rest == 0:
    bhwaddr.append(val['hwaddr'])
  cfg = open('%s/ifcfg-%s' % (network_sysconfig_dir, val['device']), 'w')
  cfg.write('DEVICE=%s\n' % val['device'])
  cfg.write('HWADDR=%s\n' % val['hwaddr'])
  cfg.write('MASTER=bond%s\n' % map_bond(bonds, int(key)))
  cfg.write('NM_CONTROLLED=no\n')
  cfg.write('SLAVE=yes\n')
  cfg.write('ONBOOT=yes\n')
  cfg.close()

for i in range(0, bonds):
  cfg = open('%s/ifcfg-bond%s' % (network_sysconfig_dir, i), 'w')
  cfg.write('DEVICE=bond%s\n' % i)
  cfg.write('NM_CONTROLLED=no\n')
  cfg.write('ONBOOT=yes\n')
  if i == 0:
    cfg.write('BOOTPROTO=static\n')
    cfg.write('IPADDR=%s\n' % my_ip)
    cfg.write('PREFIX=22\n')
    cfg.write('GATEWAY=%s\n' % my_gw)
  else:
    cfg.write('BOOTPROTO=dhcp\n')
  cfg.write('# balance-tlb\n')
  cfg.write('BONDING_OPTS="mode=6 miimon=100"\n')
  cfg.close()

print '=> Restarting Network...'
call(['/sbin/service','network','restart'])

print '=> Done ;)'
