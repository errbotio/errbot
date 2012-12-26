#!/usr/bin/env python2

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from os import getcwd
from sys import maxint
from random import random
from OpenSSL import crypto

print("Generating certificate (this may take a while if you have little entropy available)")
cert = crypto.X509()
cert.set_serial_number(int(random() * maxint))
cert.gmtime_adj_notBefore(0)
cert.gmtime_adj_notAfter(60 * 60 * 24 * 365)

subject = cert.get_subject()
subject.CN = '*'
subject.O = 'Self-Signed Dummy Certificate'

issuer = cert.get_issuer()
issuer.CN = 'Untrusted Authority'
issuer.O = 'Self-Signed'

pkey = crypto.PKey()
pkey.generate_key(crypto.TYPE_RSA, 4096)
cert.set_pubkey(pkey)
cert.sign(pkey, 'sha256')

cwd = getcwd()
certfile = "/".join([cwd, "err-selfsigned.crt"])
keyfile = "/".join([cwd, "err-selfsigned.key"])

print("Saving PEM-encoded certificate to: %s" % certfile)
f = open(certfile, 'w')
f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
f.close()

print("Saving PEM-encoded private key to: %s" % keyfile)
f = open(keyfile, 'w')
f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
f.close()

print("To use your certificate with Err, configure the Webserver plugin with:\n 'SSL': ('%s','%s')" % (certfile, keyfile))
