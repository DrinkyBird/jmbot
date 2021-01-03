import sqlite3
from operator import itemgetter
import threading

class Database:
    def __init__(self, filename):
        self.conn = sqlite3.connect(filename, check_same_thread=False)
        self.lockobj = threading.Lock()
        print('Opened website database ', filename)

    def lock(self):
        self.lockobj.acquire()

    def unlock(self):
        self.lockobj.release()

    def get_cursor(self):
        return self.conn.cursor()

    def wad_exists_by_id(self, id):
        self.lock()

        c = self.get_cursor()

        c.execute("SELECT * FROM wads WHERE id=?", (id,))
        row = c.fetchone()

        self.unlock()

        return row != None

    def get_wad_by_id(self, id):
        if not self.wad_exists_by_id(id):
            return None

        self.lock()

        c = self.get_cursor()

        c.execute("SELECT name,slug FROM wads WHERE id=?", (id,))
        row = c.fetchone()

        self.unlock()

        return {
            'id':       id,
            'name':     row[0],
            'slug':     row[1]
        }

    def wad_exists_by_slug(self, id):
        self.lock()

        c = self.get_cursor()

        c.execute("SELECT * FROM wads WHERE slug LIKE ?", (id,))
        row = c.fetchone()

        self.unlock()

        return row != None

    def get_wad_by_slug(self, slug):
        if not self.wad_exists_by_slug(slug):
            return None

        self.lock()

        c = self.get_cursor()

        c.execute("SELECT id,name,slug FROM wads WHERE slug LIKE ?", (slug,))
        row = c.fetchone()

        self.unlock()

        return {
            'id':       row[0],
            'name':     row[1],
            'slug':     row[2]
        }

    def get_wads(self):
        self.lock()

        c = self.get_cursor()

        c.execute("SELECT id,name,slug FROM wads")
        rows = c.fetchall()

        self.unlock()

        res = []
        for row in rows:
            res.append({
                'id':       row[0],
                'name':     row[1],
                'slug':     row[2]
            })

        return res

    def get_wad_maps(self, slug):
        if not self.wad_exists_by_slug(slug):
            return None

        wad = self.get_wad_by_slug(slug)

        self.lock()

        c = self.get_cursor()

        c.execute("SELECT id,wad_id,lump,name,author,type,difficulty,par FROM maps WHERE wad_id=?", (wad['id'],))
        rows = c.fetchall()

        self.unlock()

        res = []

        for row in rows:
            res.append({
                'id':           row[0],
                'lump':         row[2],
                'name':         row[3],
                'author':       row[4],
                'type':         row[5],
                'difficulty':   row[6],
                'par':          row[7],
                'wad':          self.get_wad_by_id(row[1])
            })

        return res

    def map_exists_by_lump(self, lump):
        self.lock()

        c = self.get_cursor()

        c.execute("SELECT * FROM maps WHERE lump LIKE ?", (lump,))
        row = c.fetchone()

        self.unlock()

        return row != None

    def get_map_by_lump(self, lump):
        if not self.map_exists_by_lump(lump):
            return {
                'id':               -1,
                'lump':             lump,
                'name':             'Unknown',
                'author':           'Unknown',
                'difficulty':       'Unknown',
                'par':              'Unknown',
                'wad':              'Unknown'
            }
                

        self.lock()

        c = self.get_cursor()

        c.execute("SELECT id,wad_id,lump,name,author,type,difficulty,par FROM maps WHERE lump LIKE ?", (lump,))
        row = c.fetchone()

        self.unlock()

        return {
            'id':           row[0],
            'lump':         row[2],
            'name':         row[3],
            'author':       row[4],
            'type':         row[5],
            'difficulty':   row[6],
            'par':          row[7],
            'wad':          self.get_wad_by_id(row[1])
        }