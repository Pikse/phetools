# -*- coding: utf-8 -*-

import socket
import sys
import os

port = 12346

# configuration: to run the daemon on your local box define an alias of the
# wikisource family and do the setup according to this name in
# pywikipedia/families/ by deriving a class Family(wikisource_family.Family):
if socket.gethostname() == 'zaniah':
    sys.path.append("/usr/src/phe/pywikipedia")
    family = 'wikisourcelocal'
    djvutxtpath = "djvutxt"
    servername_filename = '/usr/src/phe/botpywi/thomasv/public_html/match_and_split.server'
else: # toolserver, solaris currently
    sys.path.append("/home/phe/pywikipedia")
    family = 'wikisource'
    djvutxtpath = "/opt/ts/bin/djvutxt"
    servername_filename = os.getenv('HOME') + '/public_html/match_and_split.server'
