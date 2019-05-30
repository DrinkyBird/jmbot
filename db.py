import sqlite3
from operator import itemgetter
import threading

TABLENAME = "Zandronum"

# Read-only implementation of Zandronum's database functions, plus some extra
# stuff for Jumpmaze
class Database:
    def __init__(self, filename):
        self.conn = sqlite3.connect(filename, check_same_thread=False)
        self.lockobj = threading.Lock()
        print('Opened database ', filename)

    def lock(self):
        self.lockobj.acquire()

    def unlock(self):
        self.lockobj.release()

    def get_cursor(self):
        return self.conn.cursor()

    def namespace_exists(self, namespace):
        """Returns True if this namespace exists, otherwise returns False"""
        self.lock()

        c = self.get_cursor()

        c.execute("SELECT * FROM "+TABLENAME+" WHERE Namespace=?", (namespace,))
        row = c.fetchone()

        self.unlock()

        return row != None

    def entry_exists(self, namespace, key):
        """Returns True if this key exists in this namespace exists, otherwise returns False"""
        self.lock()

        c = self.get_cursor()

        c.execute("SELECT * FROM "+TABLENAME+" WHERE Namespace=? AND KeyName=?", (namespace, key))
        row = c.fetchone()

        self.unlock()

        return row != None

    def get_entry(self, namespace, key):
        """Returns the value of the this key in this namespace, or None if it does not exist"""
        if not self.entry_exists(namespace, key):
            return None

        self.lock()

        c = self.get_cursor()
        c.execute("SELECT Value FROM "+TABLENAME+" WHERE Namespace=? AND KeyName=?", (namespace, key))
        row = c.fetchone()

        self.unlock()

        return row[0]

    def get_entries(self, namespace):
        """Returns a dictionary of all key: value entries in this namespace"""

        self.lock()

        c = self.get_cursor()
        c.execute("SELECT KeyName,Value FROM "+TABLENAME+" WHERE Namespace=?", (namespace,))
        rows = c.fetchall()

        self.unlock()

        return dict(rows)

    def get_entry_rank(self, namespace, key, descending):
        """
        Returns the rank of this key.
        
        descending is a boolean specifying whether ranks are in descending order.
        """

        if not self.entry_exists(namespace, key):
            return -1

        self.lock()

        c = self.get_cursor()

        cmd = "SELECT COUNT(*) FROM "+TABLENAME+" WHERE Namespace=? AND CAST(Value AS INTEGER)"
        cmd = cmd + (">" if descending else "<")
        cmd = cmd + "(SELECT CAST(Value AS INTEGER) FROM "+TABLENAME+" WHERE Namespace=? and KeyName=?)"
        c.execute(cmd, (namespace, namespace, key))
        row = c.fetchone()

        self.unlock()

        if row is None:
            return -1

        return row[0] + 1

    def get_map_names(self):
        """
        Jumpmaze utility function: returns all map names recorded in the database.
        Not these may not be lump names, especially if a map has multiple routes
        (e.g. JPX2BDEM)
        """

        self.lock()

        c = self.get_cursor()

        c.execute("SELECT DISTINCT Namespace FROM "+TABLENAME+" WHERE Namespace NOT LIKE '%_pbs'")
        rows = c.fetchall()

        self.unlock()

        return [i[0] for i in rows]

    def get_solo_map_names(self):
        """
        Returns the lump names for all solo maps
        """

        self.lock()

        c = self.get_cursor()

        c.execute("SELECT DISTINCT Namespace FROM "+TABLENAME+" WHERE Namespace LIKE '%_pbs'")
        rows = c.fetchall()

        self.unlock()

        return [i[0][:-4] for i in rows]

    def get_map_records(self, map):
        """
        Jumpmaze utility function: returns all records for the specified map.
        This is a list of tuples (username, time), sorted ascendingly.
        Returns None if this map has no recorded records.
        """

        ns = map.upper() + "_pbs"
        if not self.namespace_exists(ns):
            return None

        self.lock()

        c = self.get_cursor()
        c.execute("SELECT KeyName,CAST(Value AS INTEGER) FROM "+TABLENAME+" WHERE Namespace=? ORDER BY CAST(Value AS INTEGER) ASC", (ns,))
        rows = c.fetchall()

        self.unlock()

        return rows

    def get_solo_map_record(self, map):
        """
        Jumpmaze utility function: returns the record time for this map.

        Returns a dict containing the record's author, time, and date; or None
        if this map is not in the database, has no record, or is not a solo map.
        """

        map = map.upper()

        if not self.namespace_exists(map) or self.get_map_type(map) != "solo" or not self.entry_exists(map, 'jrs_hs_author') or not self.entry_exists(map, 'jrs_hs_time') or not self.entry_exists(map, 'jrs_hs_rdate'):
            return None

        return {
            'author':       self.get_entry(map, 'jrs_hs_author'),
            'time':         int(self.get_entry(map, 'jrs_hs_time')),
            'date':         self.get_entry(map, 'jrs_hs_rdate')
        }

    def get_jmrun_map_record(self, map):
        """
        Jumpmaze utility function: returns the record time for this map.

        Returns a dict containing the record's author, time, and date; or None
        if this map is not in the database, has no record, or is not a jmrun map.
        """

        map = map.upper()

        if not self.namespace_exists(map) or self.get_map_type(map) != "jmrun" or not self.entry_exists(map, 'JMR_hs_author') or not self.entry_exists(map, 'JMR_hs_time') or not self.entry_exists(map, 'JMR_hs_rdate'):
            return None

        return {
            'author':       self.get_entry(map, 'JMR_hs_author'),
            'time':         int(self.get_entry(map, 'JMR_hs_time')),
            'date':         self.get_entry(map, 'JMR_hs_rdate')
        }

    def get_team_map_record(self, map):
        """
        Jumpmaze utility functions: returns the team points for this map.

        Returns a dict mapping helper names to the amount of points they 
        contributed, or None if this map is not in the database, has no
        record, or is not a team map.
        """

        map = map.upper()

        if not self.namespace_exists(map) or self.get_map_type(map) != "team" or not self.entry_exists(map, 'jrt_hs_time') or not self.entry_exists(map, 'jrt_hs_rdate') or not self.entry_exists(map, 'jrt_hs_total_players'):
            return None

        helpers = {}       
        helpersbyname = {} 

        helpercount = int(self.get_entry(map, 'jrt_hs_total_players'))
        
        self.lock()

        c = self.get_cursor()

        c.execute("SELECT KeyName,Value FROM "+TABLENAME+" WHERE Namespace=? AND (KeyName LIKE 'jrt_hs_helper_%' OR KeyName LIKE 'jrt_hs_points_%')", (map,))

        rows = c.fetchall()

        for key, value in rows:
            i = int(key[len("jrt_hs_helper_"):])

            if i >= helpercount:
                continue

            if i not in helpers:
                helpers[i] = {}

            if key.startswith("jrt_hs_helper_"):
                helpers[i]['name'] = value
            elif key.startswith("jrt_hs_points_"): 
                helpers[i]['points'] = int(value)

        for i, v in helpers.items():
            k = v['name']
            p = v['points']
            helpersbyname[k] = p

        self.unlock()

        return {
            'time':                 int(self.get_entry(map, 'jrt_hs_time')),
            'date':                 self.get_entry(map, 'jrt_hs_rdate'),
            'helpers':              helpersbyname
        }

    def get_map_type(self, map):
        """
        Guesses the type of a map from its high score keys.
        Can return \"solo\" or \"team\", or None if this could not be inferred.
        """

        map = map.upper()

        if not self.namespace_exists(map):
            return None

        if self.entry_exists(map, "JMR_hs_time"):
            return "jmrun"
        elif self.entry_exists(map, "jrs_hs_time"):
            return "solo"
        elif self.entry_exists(map, "jrt_hs_time"):
            return "team"

        return None

    def get_all_players(self):
        """
        Returns a list of all players who have set personal best times for any
        map.
        """

        self.lock()

        c = self.get_cursor()

        c.execute("SELECT DISTINCT KeyName FROM "+TABLENAME+" WHERE Namespace LIKE '%_pbs'")

        rows = c.fetchall()

        self.unlock()

        for i in range(len(rows)):
            rows[i] = rows[i][0]

        return rows

    def get_player_maps(self, player):
        """
        Returns a list of maps this player has set personal best times for.
        """

        self.lock()

        c = self.get_cursor()

        c.execute("SELECT DISTINCT Namespace FROM "+TABLENAME+" WHERE Namespace LIKE '%_pbs' AND KeyName=?", (player,))

        rows = c.fetchall()

        self.unlock()

        for i in range(len(rows)):
            rows[i] = rows[i][0][:-4]

        return rows