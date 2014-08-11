# -*- coding: utf-8 -*-
#
# @file prepare_request.py
#
# @remark Copyright 2014 Philippe Elie
# @remark Read the file COPYING
#
# @author Philippe Elie

import sys
import db
import os
from ws_namespaces import index as index, namespaces as namespaces
import hocr
sys.path.append(os.path.expanduser('~/phe/jobs'))
import sge_jobs
import hashlib
import shutil
import MySQLdb

# FIXME: some other lang can be supported.
supported_lang = set(
    [
        'bn',
        'fr',
        'he',
        'en',
        'de',
        'da',
        'et',
        #'de-f':"deu-frak",
        'la',  # use ita as lang code atm
        'is',
        'it',
        'es',
        'pt',
        'ru',
        'be',
        'ca',
        'eo',
        'hr',
        'hu',
        'sv',
        'no',
        'pl',
        'id',
        ]
)

# FIXME: move that to db.py
def open_db(domain, family, cursor_class = None):
    conn = db.create_conn(domain = domain, family = family)
    cursor = db.use_db(conn, domain, family, cursor_class)

    return conn, cursor

def close_db(conn, cursor):
    if cursor:
        cursor.close()
    if conn:
        conn.close()

def index_ns_nr(lang):
    ns_name = index['wikisource'][lang]
    ns_nr = namespaces['wikisource'][lang][ns_name]

    return ns_nr

def add_hocr_request(lang, book):
    job_req = {
        'jobname' : 'hocr',
        'run_cmd' : 'python',
        'args' : [
            os.path.expanduser('~/phe/hocr/hocr.py'),
            '-lang:' + lang,
            '-book:' + book
            ],
        'max_vmem' : 2048,
        }

    db_obj = sge_jobs.DbJob()

    db_obj.add_request(**job_req)

# FIXME: two bottleneck to remove. First get the sha1 in mass, second avoid
# to touch nfs for each request (reading the sha1.sum). This mean we need
# to build a db ( title, lang, sha1 ). This allow also to handle File:
# renaming in a fast way by copying from the old md5sum to the new title
# md5sum. See prepare_request1() for a faster alternative.
def prepare_request(lang):
    ns_nr = index_ns_nr(lang)

    conn, cursor = open_db(lang, 'wikisource')
    q = 'SELECT page_title FROM page WHERE page_namespace=%s and page_is_redirect=0'
    cursor.execute(q, ns_nr)
    for p in cursor.fetchall():
        title = p[0]
        if title.endswith('.djvu') or title.endswith('.pdf'):
            ret = hocr.is_uptodate(lang, title)
            if ret > 0:
                print ret, lang, title
                add_hocr_request(lang, title)

    close_db(conn, cursor)

def fetch_file_sha1_db(lang, family, titles):
    conn, cursor = open_db(lang, family, MySQLdb.cursors.DictCursor)

    fmt_strs = ', '.join(['%s'] * len(titles))
    q = 'SELECT img_name, img_sha1 FROM image WHERE img_name IN (%s)' % fmt_strs
    cursor.execute(q, titles)
    data = cursor.fetchall()

    result = {}
    for p in data:
        result[p['img_name']] = "%040x" % int(p['img_sha1'], 36)

    close_db(conn, cursor)

    return result

def fetch_file_sha1_block(lang, titles):
    result1 = fetch_file_sha1_db(lang, 'wikisource', titles)

    commons_titles = [ f for f in titles if not f in result1 ]
    result2 = fetch_file_sha1_db('commons', 'wiki', commons_titles)

    result1.update(result2)

    return result1

def fetch_file_sha1(lang, titles):
    result = {}
    for i in range(0, (len(titles) + 999) / 1000):
        temp = fetch_file_sha1_block(lang, titles[i*1000:(i+1) * 1000])
        result.update(temp)

    return result

def prepare_request1(db_hocr, lang):
    ns_nr = index_ns_nr(lang)

    conn, cursor = open_db(lang, 'wikisource')
    q = 'SELECT page_title FROM page WHERE page_namespace=%s and page_is_redirect=0'
    cursor.execute(q, ns_nr)

    titles = [ x[0] for x in cursor.fetchall() if x[0].endswith('.djvu') or x[0].endswith('.pdf') ]
    close_db(conn, cursor)

    file_to_sha1 = fetch_file_sha1(lang, titles)

    q = 'SELECT sha1, title FROM hocr WHERE lang=%s'
    db_hocr.cursor.execute(q, (lang, ))
    temp = db_hocr.cursor.fetchall()
    hocr_sha1 = set()
    for f in temp:
        hocr_sha1.add(f['sha1'])

    for title in file_to_sha1:
        if file_to_sha1[title] not in hocr_sha1:
            print lang, title
            add_hocr_request(lang, title)
        # renaming doesn't works as multiple file can have the same sha1
        #elif hocr_sha1[file_to_sha1[title]] != title:
        #    # sha1 found, but title can change with a rename.
        #    old_path = hocr.cache_path(lang, hocr_sha1[file_to_sha1[title]])
        #    new_path = hocr.cache_path(lang, title)
        #    #os.rename(old_path, new_path)
        #    q = 'UPDATE hocr SET title=%s WHERE sha1=%s'
        #    #db_hocr.cursor.execute(q, (title, sha1))
        #    #db_hocr.conn.commit()
        #    print "File renamed from", hocr_sha1[file_to_sha1[title]], "to", title

    # Attempt to tidy, doesn't work because of redirect ;(
    #for title in hocr_files:
    #    if not title in file_to_sha1:
    #        print "File no longer exists:", title

class DbHocr:
    def __init__(self):
        self.db_name = db.db_prefix() + 'hocr'

    def _open(self):
        self.conn = db.create_conn(server = 'tools-db')
        self.cursor = self.conn.cursor(MySQLdb.cursors.DictCursor)
        self.cursor.execute('use ' + self.db_name)

    def _close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def add_update_row(self, title, lang, sha1):
        sha1 = "%040x" % int(sha1, 16)
        q = """
INSERT INTO hocr (title, lang, sha1) VALUES (%s, %s, %s)
   ON DUPLICATE KEY UPDATE sha1=%s
"""
        self.cursor.execute(q, [ title, lang, sha1, sha1 ])

def read_sha1(path):
    fd = open(path + 'sha1.sum')
    sha1 = fd.read()
    fd.close()

    return sha1

def rebuild_hocr_db(db_hocr, lang):

    db_hocr.cursor.execute("DELETE FROM hocr")
    db_hocr.conn.commit()

    ns_nr = index_ns_nr(lang)

    conn, cursor = open_db(lang, 'wikisource')

    q = 'SELECT page_title FROM page WHERE page_namespace=%s and page_is_redirect=0'
    cursor.execute(q, ns_nr)
    for p in cursor.fetchall():
        title = p[0]
        if title.endswith('.djvu') or title.endswith('.pdf'):
            path = new_cache_path(title, lang)
            if os.path.exists(path + 'sha1.sum'):
                sha1 = read_sha1(path)
                db_hocr.add_update_row(title, lang, sha1)

    db_hocr.conn.commit()

    close_db(conn, cursor)

def bookname_md5(key):
    h = hashlib.md5()
    h.update(key)
    return h.hexdigest()

def old_cache_path(book_name):
    base_dir  = os.path.expanduser('~/cache/hocr/') + '%s/%s/%s/'

    h = bookname_md5(book_name)

    return base_dir % (h[0:2], h[2:4], h[4:])

def new_cache_pathh(book_name, lang):
    base_dir  = os.path.expanduser('~/cache/hocr/') + '%s/%s/%s/'

    h = bookname_md5(book_name + lang)

    return base_dir % (h[0:2], h[2:4], h[4:])


def move_dir(title, count, lang):
    old = old_cache_path(title)
    new = new_cache_path(title, lang)
    if True:
        print "echo " + str(count)

        print "mkdir -p " + new
        print "mv " + old + '* ' + new
        print "rmdir -p --ignore-fail-on-non-empty " + old
    else:
        if not os.path.exists(new):
            print "#misssing data", new
        elif not os.path.exists(new + "sha1.sum"):
            print "#misssing sha1.sum data", new
        if os.path.exists(old):
            print "#old data", old
            print "rm " + old + '*'
            print "rmdir -p --ignore-fail-on-non-empty " + old

def move_tree(lang, count):
    ns_nr = index_ns_nr(lang)

    conn, cursor = open_db(lang, 'wikisource')
    q = 'SELECT page_title FROM page WHERE page_namespace=%s and page_is_redirect=0'
    cursor.execute(q, ns_nr)
    for p in cursor.fetchall():
        title = p[0]
        if title.endswith('.djvu') or title.endswith('.pdf'):
            count += 1
            print >> sys.stderr, count, '\r',
            move_dir(title, count, lang)

    close_db(conn, cursor)

    return count

if __name__ == "__main__":
    arg = sys.argv[1]
    count = 0
    db_hocr = DbHocr()
    db_hocr._open()
    for lang in supported_lang:
        if arg == '-rebuild_hocr_db':
            rebuild_hocr_db(db_hocr, lang)
        elif  arg == '-prepare_request':
            prepare_request1(db_hocr, lang)
        else:
            print >> sys.stderr, "Unknown option:", arg

        #count = move_tree(lang, count)
        #count = prepare_request(lang, count)
    db_hocr._close()

