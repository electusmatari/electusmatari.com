import time

import eveapi

memory_cache = None # See end of file

def root():
    return eveapi.EVEAPIConnection(cacheHandler=memory_cache)


class EVEAPI(object):
    def __init__(self, sender, channel):
        self.sender = sender
        self.channel = channel

    def __enter__(self):
        return eveapi.EVEAPIConnection(cacheHandler=memory_cache)

    def __exit__(self, type_, value, traceback):
        if isinstance(value, eveapi.Error):
            self.reply(self.sender, self.channel,
                       "Error {0} during EVE API call: {1}"
                       .format(value.code, str(value)))
        elif type_ is not None:
            self.reply(self.sender, self.channel,
                       "There was an error processing your command. "
                       "Please try again later.")
            return False
        return True


class MemoryCache(object):
    def __init__(self):
        self.cache = {}

    def _key(self, host, path, params):
        return (host, path, tuple(sorted(params.items())))

    def retrieve(self, host, path, params):
        key = self._key(host, path, params)
        if key not in self.cache:
            return None
        obj = self.cache[key]
        if time.time() > obj.cachedUntil:
            del self.cache[key]
            return None
        return obj

    def store(self, host, path, params, doc, obj):
        self.cache[self._key(host, path, params)] = obj

memory_cache = MemoryCache()
