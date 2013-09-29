from emtools.ccpeve.models import apiroot
from emtools.ccpeve import eveapi

def get_ownerid(arg):
    if '<' in arg or '>' in arg:
        return None
    api = apiroot()
    try:
        charid = api.eve.CharacterID(names=arg).characters[0].characterID
        if charid == 0:
            return None
        return charid
    except eveapi.Error as e:
        if e.code == 122: # Invalid or missing list of names
            return None
        raise
    except NameError: # Encoding error
        return None
    except UnicodeEncodeError:
        return None
