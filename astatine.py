import base64
import bottle_pxsession as bottle_pxsession
import subprocess, threading, string, sqlite3, random, os, json, hashlib, functools, hashlib, datetime
from urllib.parse import urlparse

from bottle import Bottle, static_file, abort, request, redirect

aes_disabled = False
try:
    from Cryptodome import Random
    from Cryptodome.Cipher import AES
    aes_disabled = False
except ModuleNotFoundError:
    aes_disabled = True

sqlDir = '/views/sql'


class Astatine(object):
    """
    bottle mini framework to allow bottle to be used in a class with useful functions implemented to be used easily

    Information:
        - static files are already implemented into astatine
        - uploading files with different conditions is now a single function, e.g. renaming or overwriting
        - default directories are created on first start of the server
        - downloading files is implemented
        - easily define routes and error pages
        - check a value type and throw code 422 if it isn't the desired type, to be used on form values
        - sqlite functionality
    """

    def __init__(self, host='localhost', port=8080, debug=True, reload=False, server=None, quiet=None, sql_name=None):
        self._port = port
        self._host = host
        self._debug = debug
        self._reload = reload
        self._server = server
        self._quiet = quiet
        self._cursor = None
        self._sql_name = sql_name
        self._dirs = ['views/', 'views/css/',  'views/svg/',
                      'views/js/', 'views/data/', 'views/fnt/', 'views/img/',
                      'user_data/', 'sql/']
        self._plugin_manager = None
        self._session_plugin = None
        self._lock = threading.Lock()
        self._days = 100
        self._hours = 24
        self._minutes = 60
        self._seconds = 60
        self._life = self._days * self._hours * self._minutes * self._seconds
        self.ss = None
        self.cursor = self._cursor
        self.has_sessions = False
        self.uid_length = 20
        self._db = None
        self._db_c = None

        self._static_files_ext = ['css', 'scss', 'less', 'png', 'jpg', 'jpeg', 'gif', 'tiff',
                                  'psd', 'raw', 'svg', 'ico', 'js', 'otf', 'ttf', 'eot', 'webp',
                                  'woff', 'woff2', 'mp4', 'mov', 'wmv', 'avi', 'mkv', 'mpeg-2', 'webm',
                                  'mp3', 'wav', 'ogg', 'pdf']
        self._image_ext = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'ico', '']

        if self._sql_name:
            self._setup_sql()
        self.app = Bottle()
        self._setup_astatine()
        self._setup_db()
        self._route()

    def __contains__(self, route):
        if route in self.app.routes:
            return True
        else:
            return False

    def _setup_sql(self):
        """Creates SQLite3 database."""
        self._conn = sqlite3.connect('{}'.format(self._sql_name), check_same_thread=False)
        self._cursor = self._conn.cursor()
        self.cursor = self._cursor

    def _setup_db(self):
        self._db = sqlite3.connect('sql/site_data.db', check_same_thread=False)
        self._db_c = self._db.cursor()
        self._db_c.execute('''
            CREATE TABLE IF NOT EXISTS ip_bans (
                uid TEXT PRIMARY KEY UNIQUE NOT NULL,
                ip_hash TEXT UNIQUE NOT NULL
            )
        ''')
        self._db_c.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                datetime INTEGER NOT NULL,
                visits INTEGER NOT NULL DEFAULT 0
            )
        ''')
        self._db_c.execute('''
            CREATE TABLE IF NOT EXISTS unique_visitors (
                datetime INTEGER NOT NULL,
                visits INTEGER NOT NULL DEFAULT 0
            )
        ''')
        self._db_c.execute('''
            CREATE TABLE IF NOT EXISTS visitor_referral (
                datetime INTEGER NOT NULL,
                referral TEXT NOT NULL,
                visits INTEGER NOT NULL DEFAULT 0
            )
        ''')

    def _end_sql(self):
        self._db_c.close()
        self._db.commit()
        self._conn.commit()

    def _setup_astatine(self):
        """Creates all directories."""
        for directory in self._dirs:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def _download_file(self, filepath) -> static_file:
        if filepath.split('/')[0] == 'user_data':
            return static_file(filepath, root="", download=filepath)
        else:
            abort(403)

    def _static_files(self, filepath) -> static_file:
        name, ext = os.path.splitext(filepath)
        favicon = False
        if ext[1:] in self._static_files_ext:
            favicon = True if ext[1:] == 'ico' else False
            return static_file(filepath, '', parameters=request.query) if not favicon else static_file(filepath, '', mimetype='image/x-icon', parameters=request.query)
        else:
            print('Error 404: Could not find file "{}"'.format(filepath))

    def _route(self):
        static_files = functools.partial(self._static_files, filepath='filepath')
        df = functools.partial(self._download_file, filepath='filepath')

        all_extensions = []
        for i in self._static_files_ext:
            all_extensions.append(i)

        # self.app.route("/download/<filepath:path>", method='GET', callback=df)
        self.app.route("/s/<filepath:re:.*\\.({})>".format("|".join(all_extensions)), method='GET', callback=static_files)

    def track_visitor(self, session, domains: list):
        """
            :param session: Session object.
            :param domains: List of domains that are exempt from the check, i.e. to see whether the referral is from outside of this domain.
            :return:
        """

        target_ip = request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')
        hashed_ip = hashlib.sha256(bytes(target_ip, 'utf-8')).hexdigest()

        if self._db_c.execute('SELECT TRUE FROM ip_bans WHERE ip_hash = ?', (hashed_ip,)).fetchone():
            abort(403)
        date_current = datetime.datetime.now().timestamp()
        date_start = datetime.datetime.combine(datetime.datetime.now(), datetime.time.min).timestamp()

        check_date_start = self._db_c.execute('SELECT * FROM visitors WHERE datetime = ?', (int(date_start),))

        if urlparse(request.environ.get('HTTP_REFERER')).netloc not in domains:
            if not check_date_start.fetchone():
                self._db_c.execute('''
                    INSERT INTO visitor_referral (datetime, referral, visits) VALUES (?,?,?)
                ''', (int(date_start), request.environ.get('HTTP_REFERER'), 1))
            else:
                if session['last_visit'] and session['last_visit'] < date_start:
                    self._db_c.execute('''
                        UPDATE visitor_referral SET visits = visits + 1 WHERE datetime = ? AND referral = ?
                    ''', (int(date_start), request.environ.get('HTTP_REFERER')))
                    session['last_visit'] = date_start
                elif not session['last_visit']:
                    self._db_c.execute('''
                        UPDATE visitor_referral SET visits = visits + 1 WHERE datetime = ? AND referral = ?
                    ''', (int(date_start), request.environ.get('HTTP_REFERER')))
                    session['last_visit'] = date_start

        if not session['last_visit']:
            self._db_c.execute('''UPDATE unique_visitors SET visits = visits + 1''')

        if not check_date_start.fetchone():
            self._db_c.execute('''
                INSERT INTO visitors (datetime, visits) VALUES (?,?)
            ''', (int(date_start), 1))
        else:
            if session['last_visit'] and session['last_visit'] < date_start:
                self._db_c.execute('''
                    UPDATE visitors SET visits = visits + 1 WHERE datetime = ?
                ''', (int(date_start),))
                session['last_visit'] = date_start
            elif not session['last_visit']:
                self._db_c.execute('''
                    UPDATE visitors SET visits = visits + 1 WHERE datetime = ?
                ''', (int(date_start),))
                session['last_visit'] = date_start

        self._db.commit()

        session['last_visit'] = date_current

    def enable_sessions(self):
        """
        Enable session usage in routes.
        :return:
        """
        self._session_plugin = bottle_pxsession.SessionPlugin(cookie_lifetime=self._life)
        self.ss = self.app.install(self._session_plugin)
        self.has_sessions = True

    def route(self, name, method, function, sessions=False, **kwargs):
        """
        :param name: The route/name
        :param method: 'GET', 'PUT', 'DELETE' or 'POST'
        :param function: The function/method to link to the route.
        :param sessions: Whether this route should use sessions.
        :param args: provide extra arguments to the function.
        :return:
        """
        fn = functools.partial(function, kwargs) if kwargs else function
        if not sessions:
            self.app.route(name, method=method, callback=fn)
        elif sessions and self.has_sessions:
            self.app.route(name, method=method, callback=fn, apply=[self.ss])

    def error(self, code, function):
        """
        :param code: Error code to pair with the function, can pass singular code or list of codes
        :param function: Function callback
        :return:
        """
        if isinstance(code, list):
            for c in code:
                self.app.error_handler[c] = function
        else:
            self.app.error_handler[code] = function

    @staticmethod
    def random_string(string_length, special=False):
        letters = string.ascii_letters
        numbers = string.digits
        specials = '!£$%&*;:@~#<>,./?'
        combo = numbers + letters + specials if special else numbers + letters
        return ''.join(random.choice(combo) for i in range(string_length))

    def generate_uid(self, table_name, id_name, length=20):
        is_unique, new_id = False, None
        off_length = length or self.uid_length
        while not is_unique:
            new_id = self.random_string(off_length)
            table = self._cursor.execute(f"SELECT {id_name} FROM {table_name} WHERE {id_name} = ?", (new_id,))
            for t in table:
                if not t:
                    is_unique = False
                else:
                    is_unique = True
            is_unique = True if not [t for t in table] else False
        return new_id

    @staticmethod
    def upload_files(files, extensions, path, max_file_size=52428800, rename=None):
        """
        :param files: A list of the files
        :param extensions: Any list of extensions or '*' to allow any
        :param path: The path the file will be saved to.
        :param max_file_size: The maximum file size per file.
        :param rename: provide extra arguments to the function.
        :return:
        """
        if not os.path.exists(path):
            os.makedirs(path)

        FILEPATH = None
        BUF_SIZE = 8192

        try:
            for file in files:
                name, ext = os.path.splitext(file.filename)
                filename = name + ext.lower()
                if ext in extensions or extensions == '*':
                    if rename:
                        FILEPATH = path + rename + ext if path else rename + ext
                    else:
                        FILEPATH = path + filename if path else filename
                    byte_count = 0
                    data_blocks = []
                    buf = file.file.read(BUF_SIZE)
                    while buf:
                        byte_count += len(buf)
                        if byte_count > max_file_size:
                            abort(413)
                        data_blocks.append(buf)
                        buf = file.file.read(BUF_SIZE)
                    data = b''.join(data_blocks)
                    with open(FILEPATH, 'wb') as f:
                        f.write(data)
        except IOError:
            redirect(request.environ['HTTP_REFERER'])

    @staticmethod
    def remove_file(file_name):
        os.remove(str(file_name))

    def ip_ban(self, ip=None):
        target_ip = ip if ip else request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')
        hashed_ip = hashlib.sha256(bytes(target_ip, 'utf-8')).hexdigest()
        self._db_c.execute('INSERT INTO ip_bans (uid, ip_hash) VALUES (?,?)', (self.random_string(8), hashed_ip))

    @staticmethod
    def check_type(var, var_type):
        if isinstance(var, var_type):
            return var
        else:
            abort(422)

    def run_astatine(self):
        """
        Run the bottle website.
        """
        try:
            if self._server:
                self.app.run(host=self._host,
                             port=self._port,
                             debug=self._debug,
                             reloader=self._reload,
                             server=self._server,
                             quiet=self._quiet)
            else:
                self.app.run(host=self._host,
                             port=self._port,
                             debug=self._debug,
                             reloader=self._reload,
                             quiet=self._quiet)
        finally:
            if self._sql_name:
                self._end_sql()
            self._db.commit()

    def execute_sql(self, query, values=None, fetchall=True):
        """
        :param query: The SQLite3 query you want to make
        :param values: Any values you need to pass into the SQLite3 query
        :param fetchall: Whether it should <fetchall> or <fetchone>, default is True
        :return
        """
        execution = None
        try:
            self._lock.acquire(True)
            if values:
                execution = self._cursor.execute(query, values).fetchall() if fetchall else self._cursor.execute(query, values).fetchone()
                self._conn.commit()
            else:
                execution = self._cursor.execute(query).fetchall() if fetchall else self._cursor.execute(query).fetchone()
                self._conn.commit()
        finally:
            self._lock.release()
            return execution

    def create_function_sql(self, name, parameters, callback):
        sqlite3.enable_callback_tracebacks(True)
        self._conn.create_function(name, parameters, callback)


class AstatineSQL(object):
    """ Astatine SQLite3 Class """

    def __init__(self, path):
        self._path = path
        self._cursor = None
        self._conn = None
        self._lock = threading.Lock()
        self.connect()

    def connect(self):
        """Creates SQLite3 database."""
        self._conn = sqlite3.connect('{}'.format(self._path), check_same_thread=False)
        self._cursor = self._conn.cursor()

    def commit(self):
        self._conn.commit()

    def close(self):
        self._cursor.close()

    def execute_sql(self, query, values=None, fetchall=True):
        """
        :param query: The SQLite3 query you want to make
        :param values: Any values you need to pass into the SQLite3 query
        :param fetchall: Whether it should <fetchall> or <fetchone>
        :return:
        """
        execution = None
        try:
            self._lock.acquire(True)
            if values:
                execution = self._cursor.execute(query, values).fetchall() if fetchall else self._cursor.execute(query, values).fetchone()
                self._conn.commit()
            else:
                execution = self._cursor.execute(query).fetchall() if fetchall else self._cursor.execute(query).fetchone()
                self._conn.commit()
        finally:
            self._lock.release()
            return execution

    def create_function_sql(self, name, parameters, callback):
        sqlite3.enable_callback_tracebacks(True)
        self._conn.create_function(name, parameters, callback)

    @staticmethod
    def random_string(string_length, special=False):
        specials = '!£$%&*;:@~#<>,./?'
        combo = string.ascii_letters + string.digits + (specials if special else None)
        return ''.join(random.choice(combo) for i in range(string_length))

    def generate_uid(self, table_name, id_name, length=20):
        is_unique, new_id = False, None
        while not is_unique:
            new_id = self.random_string(length)
            table = self._cursor.execute(f"SELECT {id_name} FROM {table_name} WHERE {id_name} = ?", (new_id,))
            for t in table:
                if not t:
                    is_unique = False
                else:
                    is_unique = True
            is_unique = True if not [t for t in table] else False
        return new_id


class AstatineAES(object):
    """ Astatine Encryption and Decryption Class """

    def __init__(self, key):
        if not aes_disabled:
            self.bs = AES.block_size
            self.key = hashlib.sha256(key.encode()).digest()
        else:
            print("""
                Error: pycrypto could not be found.
            """)

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw.encode()))

    def decrypt(self, enc):
        # print(enc)
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s) - 1:])]


class AstatineSMTP(object):
    """ Astatine Email Class """

    def __init__(self, sender):
        self.email_to = None
        self.sender = sender

    def send_email(self, receiver, subject, content=None):
        subprocess.run(['mail', '--content-type=text/html', '-s', subject, '-r', self.sender, receiver,], input=content, text=True)

    def set_sender(self, sender):
        self.sender = sender


class AstatineJSON(object):
    """ Astatine JSON Class """

    def __init__(self, file):
        self.file = file

    def read(self):
        with open(self.file) as f:
            return json.load(f)

    def write(self, data):
        with open(self.file) as f:
            json.dump(data, f)