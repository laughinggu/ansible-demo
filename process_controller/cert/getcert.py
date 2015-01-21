#!/usr/bin/python

import sys
import commands
import optparse
import os

pwd=os.getcwd()

parser = optparse.OptionParser()
parser.add_option('-d','--domain', action="store", dest="domain")
options, args = parser.parse_args()
if options.domain == None:
	parser.error("should use -d or --domain to assign a value of domain")

domain=options.domain
os.system("bash -x "+pwd+"/generatecertwithopenssl.sh "+domain)

certfile=open(domain+".crt")
certcontent=certfile.readlines()
certfile.close()

keyfile=open(domain+".key")
keycontent=keyfile.readlines()
keyfile.close()

haproxy=open('haproxy.out','w')
sys.stdout=haproxy
for l1 in certcontent:
	l1=l1.replace('\n','\\r\\n')
	sys.stdout.write(l1)

for l11 in keycontent:
	l11=l11.replace('\n','\\r\\n')
	sys.stdout.write(l11)


login=open('login.out','w')
sys.stdout=login
for l2 in certcontent:
	l2=l2.replace('\n','\\r\\n')
	sys.stdout.write(l2)