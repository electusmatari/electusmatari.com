import emtools.ccpeve.igb as igb

class IGBMiddleware(object):
    def process_request(self, request):
        request.igb = igb.IGB(request)

def context_processor(request):
    return {'igb': request.igb}
