import string, threading, json, os, functools, sqlite3, random
import smtplib, requests, ssl, hashlib, base64, bottle_pxsession

from bottle import Bottle, static_file, redirect
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

aes_disabled = False
try:
    from Crypto import Random
    from Crypto.Cipher import AES
    aes_disabled = False
except ModuleNotFoundError:
    aes_disabled = True

sqlDir = '/views/sql'


class Astatine(object):
    """
    This is my bottle website Astatine class, used to make making websites easier and faster, especially first setting up a new website.

    Information:
        - When adding a file to your html file e.g. CSS you only need to provide the filepath past the 'css' directory,
        if the css file is in that main directory you only need to provide the file name.
            - This is the same if you use a file inside your CSS e.g. an svg reference you only need to provide the file name unless the file is embedded further in the directory.
            - This is also the case for other file types such as .js .css .scss .svg .jpg .png .ttf .eot .ttf .woff .woff2.
        - All basic website directories will be made when you call the class for the first time if the directories don't already exist.
        - To use sessions the 'addSessionSupport()' function, this needs to be called otherwise sessions won't be enabled.
        - For allowing a user to download a file make a link with the route '/download/<filename>'.
        - When uploading a file to the web server, it will automatically upload to `/views/data`.
        - The Astatine class also allows the use of SQLite3 with ease, requiring no setup, just use the `modifySQL()` and `returnSQL()` functions to interact with your database.
        - A function that allows the creation of a UUID that checks in a provided table whether that UUID already exists to make sure it is unique.
    """

    def __init__(self, host='localhost', port=8080, debug=True, reload=False, server=None, quiet=None, sql_name=None):
        self._port = port
        self._host = host
        self._debug = debug
        self._reload = reload
        self._server = server
        self._quiet = quiet
        self._cursor = None
        self._sqlName = sql_name
        self._dirs = ['views/', 'views/sql/', 'views/css/',  'views/svg/',
                      'views/js/', 'views/data/', 'views/fnt/', 'views/img/',
                      'user_data/']
        self._pluginManager = None
        self._sessionPlugin = None
        self._lock = threading.Lock()
        self._days = 100
        self._hours = 24
        self._minutes = 60
        self._seconds = 60
        self._life = self._days * self._hours * self._minutes * self._seconds
        self.ss = None
        self.cursor = self._cursor
        self.hasSessions = False
        self.ASTATINE_ALL_DOC_EXTS = (
            '.doc', '.dot', '.wbk', '.docx', '.docm', '.dotm', '.docb', '.xls', '.xlsx', '.xlsm', '.xlt', '.xltx', '.xltm',
            '.xla', '.xlam', '.one', '.pptx', '.ppt', '.pptjpeg', '.pptpng', '.odt', '.ott', '.fodt', '.uot', '.ods',
            '.ots', '.fods', '.uos', '.odp', '.otp', '.odg', '.fodp', '.uop', '.odg', '.otg', '.fodg', '.odf', '.mml')

        self._static_files_ext = {
            'css': ['css', 'scss', 'less'],
            'img': ['png', 'jpg', 'jpeg', 'gif', 'tiff', 'psd', 'raw'],
            'svg': ['svg'],
            'fav': ['ico'],
            'js': ['js'],
            'fnt': ['otf', 'ttf', 'eot', 'woff', 'woff2']
        }

        self.ASTATINE_FILE_DIR = None
        self.ASTATINE_FILE_DIRS = []
        if self._sqlName:
            self._setup_sql()
        self.app = Bottle()
        self._setup_astatine()
        self._route()

    def __contains__(self, route):
        if route in self.app.routes:
            return True
        else:
            return False

    def _setup_sql(self):
        """Creates SQLite3 database."""
        self._conn = sqlite3.connect('{}/{}'.format(self._dirs[1], self._sqlName), check_same_thread=False)
        self._cursor = self._conn.cursor()
        self.cursor = self._cursor

    def _end_sql(self):
        self._conn.commit()

    def _setup_astatine(self):
        """Creates all directories."""
        for directory in self._dirs:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def _download_file(self, filepath: str = '') -> static_file:
        return static_file(filepath, root="", download=filepath)

    def _static_files(self, filepath) -> static_file:
        path = None
        favicon = False
        if '.' in filepath:
            name, ext = filepath.split('.')
            for k, v in self._static_files_ext.items():
                if ext in v:
                    path = "views/{}/".format(k)
                    favicon = True if k == 'fav' else False

            if '/' in filepath:
                if 'user_data' in filepath.split('/'):
                    path = ''
            return static_file(filepath, root=path) if not favicon else static_file(filepath, root=path, mimetype='image/x-icon')

    def _route(self):
        static_files = functools.partial(self._static_files, filepath='filepath')
        df = functools.partial(self._download_file, filepath='filepath')

        all_extensions = []
        for v in self._static_files_ext.values():
            for i in v:
                all_extensions.append(i)

        self.app.route("/download/<filepath:path>", method='GET', callback=df)
        self.app.route("/<filepath:re:.*\\.({})>".format("|".join(all_extensions)), method='GET', callback=static_files)

    def enable_sessions(self):
        """
        This is so you can enable session support for your routes.
        :return:
        """
        self._sessionPlugin = bottle_pxsession.SessionPlugin(cookie_lifetime=self._life)
        self.ss = self.app.install(self._sessionPlugin)
        self.hasSessions = True

    def add_route(self, name: str, method: str, function: object, sessions=False):
        """
        :param name: The route/name
        :param method: 'GET' or 'POST'
        :param function: The function/method to link to the route
        :param sessions: Whether this route should use sessions.
        :return:
        """
        if not sessions:
            self.app.route(name, method=method, callback=function)
        elif sessions and self.hasSessions:
            self.app.route(name, method=method, callback=function, apply=[self.ss])
        else:
            raise Exception('[ FATAL ISSUE ] - Route could not be created.')

    def add_route_args(self, name, method, function, arg):
        fn = functools.partial(function, arg)
        self.app.route(name, method=method, callback=fn, apply=[self.ss])

    def add_error_handler(self, code, function):
        """
        :param code: Error code to pair with the function, can pass singular code or list of codes
        :param function: Function callback
        :return:
        """
        if type(code) == list:
            for c in code:
                self.app.error_handler[c] = function
        else:
            self.app.error_handler[code] = function

    def random_string(self, string_length, special=False):
        letters = string.ascii_letters
        numbers = '0123456789'
        specials = '!£$%&*;:@~#<>,./?'
        combo = numbers + letters
        if special:
            combo += specials
        return ''.join(random.choice(combo) for i in range(string_length))

    def generate_unique_id(self, table_name, id_name):
        is_unique = False
        new_id = 0
        while not is_unique:
            new_id = self.random_string(20)
            table = self._cursor.execute("SELECT {} FROM {} WHERE {} = ?".format(id_name, table_name, id_name), (new_id,))
            for t in table:
                if not t:
                    is_unique = True
                    break
                else:
                    continue
            is_unique = True
        return new_id

    def generate_uuid(self, table_name, id_name):
        is_unique = False
        new_id = 0
        while not is_unique:
            new_id = self.random_string(40, True)
            table = self._cursor.execute("SELECT {} FROM {} WHERE {} = ?".format(id_name, table_name, id_name), (new_id,))
            for t in table:
                if not t:
                    is_unique = True
                    break
                else:
                    continue
            is_unique = True
        return new_id

    def upload_file(self, file, extensions, path, overwrite=False, rename=None):
        name, ext = file.filename.split('.')
        if ext in extensions or extensions is '*':
            if path:
                path = path + rename + '.' + ext or file.filename
            else:
                path = rename + '.' + ext or file.filename
            file.save(path, overwrite=overwrite)
        else:
            raise Exception('[ FILE ISSUE ] - File Extension is not allowed.')

    def upload_files(self, files, extensions, path, overwrite=False, rename=None):
        for file in files:
            name, ext = file.filename.split('.')
            if ext in extensions or extensions is '*':
                if path:
                    path = path + rename + '.' + ext or file.filename
                else:
                    path = rename + '.' + ext or file.filename
                file.save(path, overwrite=overwrite)
            else:
                raise Exception('[ FILE ISSUE ] - File Extension is not allowed.')

    @staticmethod
    def remove_file(fileName):
        os.remove(str(fileName))

    def run_astatine(self):
        """
        Run the bottle website.
        :return:
        """
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
        self._end_sql()

    def execute_sql(self, query, values=None, fetchall=True):
        """
        :param query: The SQLite3 query you want to make
        :param values: Any values you need to pass into the SQLite3 query
        :param fetchall: Whether it should <fetchall> or <fetchone>, default is True
        :return:
        """
        try:
            self._lock.acquire(True)
            if values:
                execution =  self._cursor.execute("%s" % query, values).fetchall() if fetchall else self._cursor.execute("%s" % query, values).fetchone()
                self._conn.commit()
                return execution
            else:
                execution = self._cursor.execute("%s" % query).fetchall() if fetchall else self._cursor.execute("%s" % query).fetchone()
                self._conn.commit()
                return execution
        finally:
            self._lock.release()

    def function_SQL(self, name, parameters, callback):
        sqlite3.enable_callback_tracebacks(True)
        self._conn.create_function(name, parameters, callback)


class AstatineSQL(object):
    """ Astatine SQLite3 Class """

    def __init__(self, fileName, sql_dir=None):
        self._sqlName = fileName
        self._sql_dir = sql_dir
        self._cursor = None
        self._conn = None
        self._lock = threading.Lock()

    def connect(self):
        """Creates SQLite3 database."""
        self._conn = sqlite3.connect('{}/{}'.format(self._sql_dir, self._sqlName), check_same_thread=False)
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
        try:
            self._lock.acquire(True)
            if values:
                return self._cursor.execute("%s" % query, values).fetchall() if fetchall else self._cursor.execute(
                    "%s" % query, values).fetchone()
            else:
                return self._cursor.execute("%s" % query).fetchall() if fetchall else self._cursor.execute(
                    "%s" % query).fetchone()
        finally:
            self._lock.release()

    def function_SQL(self, name, parameters, callback):
        sqlite3.enable_callback_tracebacks(True)
        self._conn.create_function(name, parameters, callback)


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

    def __init__(self, fromEmail, password):
        self.toEmail = None
        self.fromEmail = fromEmail
        self.port = 465
        self.smtpServer = 'smtp.gmail.com'
        self.senderPSWD = password

    def send_message(self, receiver, subject, plain=None, html=None):
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = self.fromEmail
        message['To'] = receiver
        message.add_header('Content-Type', 'text/html')

        plain1 = MIMEText(plain, 'plain')
        html1 = MIMEText(html, 'html')

        message.attach(plain1)
        message.attach(html1)

        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(self.smtpServer, self.port, context=context) as server:
            server.login(self.fromEmail, self.senderPSWD)
            server.sendmail(self.fromEmail, receiver, message.as_string())


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
