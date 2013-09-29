import kgi

def unauthorized(user, reason):
    if not user.is_authenticated():
        reason = 'Please log in to the forums.'
    elif not user.has_permission('em'):
        reason = 'You are not a member of Electus Matari.'
    return kgi.template('403.html', reason=reason)
                 
def notfound():
    return kgi.template('404.html')
