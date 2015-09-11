#!/usr/bin/env python
import sys
import ConfigParser
import pexpect

config = ConfigParser.RawConfigParser(allow_no_value=True)
config.readfp(open(sys.argv[1]))

host = config.get('virt-viewer', 'host')
port = config.get('virt-viewer', 'port')
pwd  = config.get('virt-viewer', 'password')

address = '%s:%s' % (host, port)

p = pexpect.spawn('vncviewer %s' % (address))
p.expect('Password:')
p.sendline(pwd)
p.interact()
