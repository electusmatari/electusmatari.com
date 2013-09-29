import ConfigParser
import os

cfg = None

def config():
    global cfg
    if cfg is None:
        cfg = ConfigParser.ConfigParser()
        cfg.read(['/etc/emcom/kgi.cfg'])
    return cfg
