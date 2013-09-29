import logging
import ConfigParser
from mrintel import bot


def main():
    conf = ConfigParser.SafeConfigParser()
    conf.read(["/etc/emcom/mrintel.conf"])
    logging.basicConfig(format="%(asctime)s %(message)s",
                        level=logging.DEBUG)
    logging.info("MrIntel, at your service")
    threads = []
    for sec in conf.sections():
        if not sec.startswith("network "):
            continue
        mrintel = bot.MrIntel(conf,
                              conf.get(sec, 'server'),
                              conf.getint(sec, 'port'),
                              conf.get(sec, 'nick'),
                              conf.get(sec, 'user'),
                              conf.get(sec, 'realname'),
                              [channel.strip()
                               for channel
                               in conf.get(sec, 'channels').split(",")])
        mrintel.daemon = True
        mrintel.start()
        threads.append(mrintel)
    while len(threads) > 0:
        threads[-1].join(60)
        if not threads[-1].is_alive():
            threads.pop()


if __name__ == '__main__':
    main()
