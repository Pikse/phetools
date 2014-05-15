# -*- coding: utf-8 -*-                                                        

import sys 
import pywikibot
from pywikibot import config
from pywikibot.data import api

def gen_lang(dict_name, result):
    for family in dict_name:
        for lang in dict_name[family]:
            result.add( (family, lang) )

def gen_all_lang():
    result = set()

    gen_lang(config.sysopnames, result)
    gen_lang(config.usernames, result)

    return result

def name_from_ns(namespaces, ns):
    return namespaces[ns][0]

def gen_namespace(fam, lang):
    site = pywikibot.Site(code=lang, fam=fam)
    text = u'namespaces["' + fam + u'"]["' + lang + '"] = {\n'
    
    namespaces = site.namespaces()
    for ns in namespaces:
        for name in namespaces[ns]:
            if name:
                text += u'    "' + name + u'" : ' + unicode(ns) + u',\n'
    text += u'}\n'

    request = api.Request(
        site=site,
        action="query",
        meta="proofreadinfo",
        piprop="namespaces")

    data = request.submit()[u'query'][u'proofreadnamespaces']

    text += u'index["' + fam + u'"]["' + lang + '"] = '
    text += u'"' + name_from_ns(namespaces, data[u'index'][u'id']) + u'"\n'

    text += u'page["' + fam + u'"]["' + lang + '"] = '
    text += u'"' + name_from_ns(namespaces, data[u'page'][u'id']) + u'"\n'

    return text

def gen_all_namespace(wiki_fam_lang):
    text  = u'# -*- coding: utf-8 -*-\n'
    text += u'# auto-generated by %s, do not edit manually.\n\n' % sys.argv[0]

    text += u"namespaces = {}\n"
    # FIXME: not really correct, works only for wikisource atm, no big deal
    text += u'namespaces["wikisource"] = {}\n\n'

    text += u'index = {}\n'
    text += u'index["wikisource"] = {}\n\n'

    text += u'page = {}\n'
    text += u'page["wikisource"] = {}\n\n'

    for f in wiki_fam_lang:
        text += gen_namespace( f[0], f[1] )
    return text

if __name__ == "__main__":
    wiki_fam_lang = gen_all_lang()
    text = gen_all_namespace(wiki_fam_lang)

    fd = open('/data/project/phetools/wikisource/namespaces.py', 'w')
    fd.write(text.encode('utf-8'))
    fd.close()
