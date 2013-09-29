import os
import tempita

import config

TEMPLATE_NAMESPACE = {}

def template(filename, **kwargs):
    """
    Mark up a template with keyword arguments.
    """
    cfg = config.config()
    full = os.path.join(cfg.get('templates', 'directory'),
                        filename)
    t = tempita.HTMLTemplate.from_filename(full, encoding='utf-8',
                                           get_template=get_file_template,
                                           namespace=TEMPLATE_NAMESPACE)
    return t.substitute(**kwargs)

def template_function(function):
    """
    A decorator to register a template function.
    """
    TEMPLATE_NAMESPACE[function.__name__] = function
    return function

def get_file_template(name, from_template):
    """
    Fixed tempita.get_file_template to check the parent directory of a
    template.
    """
    path = os.path.join(os.path.dirname(from_template.name),
                        name)
    return from_template.__class__.from_filename(
        path, namespace=from_template.namespace,
        get_template=from_template.get_template)
