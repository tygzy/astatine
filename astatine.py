import random

from bottle import Bottle, static_file, redirect
import sqlite3
import functools
import os
import json
import threading
import string

import bottle_pxsession
from Crypto import Random
from Crypto.Cipher import AES
import hashlib
import base64

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

    def __init__(self, host='localhost', port=8080, debug=True, reload=False, server=None, sql_name=None):
        self._port = port
        self._host = host
        self._debug = debug
        self._reload = reload
        self._server = server
        self._cursor = None
        self._sqlName = sql_name
        self._viewDir = 'views/'
        self._cssDir = 'views/css/'
        self._sqlDir = 'views/sql/'
        self._svgDir = 'views/svg/'
        self._jsDir = 'views/js/'
        self._tmp = 'views/data/'
        self._fnt = 'views/fnt/'
        self._img = 'views/img/'
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
        self.ASTATINE_FILE_DIR = None
        self.ASTATINE_FILE_DIRS = []
        if sql_name:
            self._setupSQLite3()
        self.app = Bottle()
        self._setup_astatine()
        self._route()

    def __contains__(self, route):
        if route in self.app.routes:
            return True
        else:
            return False

    def _setupSQLite3(self):
        """Creates SQLite3 database."""
        self._conn = sqlite3.connect('{}/{}'.format(self._sqlDir, self._sqlName), check_same_thread=False)
        self._cursor = self._conn.cursor()
        self.cursor = self._cursor

    def _endSQLite3(self):
        self._conn.commit()

    def _setup_astatine(self):
        """Creates all directories."""
        directories = [self._viewDir, self._jsDir, self._cssDir, self._svgDir, self._sqlDir, self._tmp, self._fnt, self._img]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

    @staticmethod
    def _cssFile(filepath: str = '') -> static_file:
        path = ""
        if len(filepath.split("/")) > 1:
            if "data" in filepath.split("/"):
                path = "views/"
        else:
            path = "views/css/"
        return static_file(filepath, root=path)

    @staticmethod
    def _scssFile(filepath: str = '') -> static_file:
        path = ""
        if len(filepath.split("/")) > 1:
            if "data" in filepath.split("/"):
                path = "views/"
        else:
            path = "views/scss/"
        return static_file(filepath, root=path)

    @staticmethod
    def _jsFile(filepath: str = '') -> static_file:
        path = ""
        if len(filepath.split("/")) > 1:
            if "data" in filepath.split("/"):
                path = "views/"
        else:
            path = "views/js/"
        return static_file(filepath, root=path)

    @staticmethod
    def _svgFile(filepath: str = '') -> static_file:
        path = ""
        if len(filepath.split("/")) > 1:
            if "data" in filepath.split("/"):
                path = "views/"
        else:
            path = "views/svg/"
        return static_file(filepath, root=path)

    @staticmethod
    def _fontFile(filepath: str = '') -> static_file:
        path = ""
        if len(filepath.split("/")) > 1:
            if "data" in filepath.split("/"):
                path = "views/"
        else:
            path = "views/fnt/"
        return static_file(filepath, root=path)

    @staticmethod
    def _imgFile(filepath: str = '') -> static_file:
        path = ""
        if len(filepath.split("/")) > 1:
            if "data" in filepath.split("/"):
                path = "views/"
        else:
            path = "views/img/"
        return static_file(filepath, root=path)

    @staticmethod
    def _jpgFile(filepath: str = '') -> static_file:
        path = ""
        if len(filepath.split("/")) > 1:
            if "data" in filepath.split("/"):
                path = "views/"
        else:
            path = "views/jpg/"
        return static_file(filepath, root=path)

    @staticmethod
    def _faviconFile(filepath: str = '') -> static_file:
        path = ""
        if len(filepath.split("/")) > 1:
            if "data" in filepath.split("/"):
                path = "views/"
        else:
            path = "views/"
        return static_file(filepath, root=path, mimetype='image/x-icon')

    @staticmethod
    def _downloadFile(filepath: str = '') -> static_file:
        return static_file(filepath, root="", download=filepath)


    def _route(self):
        css = functools.partial(self._cssFile, filepath='filepath')
        scss = functools.partial(self._scssFile, filepath='filepath')
        js = functools.partial(self._jsFile, filepath='filepath')
        svg = functools.partial(self._svgFile, filepath='filepath')
        df = functools.partial(self._downloadFile, filepath='filepath')
        fnt = functools.partial(self._fontFile, filepath='filepath')
        img = functools.partial(self._imgFile, filepath='filepath')
        favicon = functools.partial(self._faviconFile, filepath='filepath')
        self.app.route("/<filepath:re:.*\\.css>", method='GET', callback=css)
        self.app.route("/<filepath:re:.*\\.scss>", method='GET', callback=scss)
        self.app.route("/<filepath:re:.*\\.js>", method='GET', callback=js)
        self.app.route("/<filepath:re:.*\\.svg>", method='GET', callback=svg)
        self.app.route("/download/<filepath:path>", method='GET', callback=df)
        self.app.route("/<filepath:re:.*\\.(otf|ttf|svg|eot|woff|woff2)>", method='GET', callback=fnt)
        self.app.route("/<filepath:re:.*\\.(png|jpg|gif|jpeg|tiff|psd|pdf|ai|eps|raw)>", method='GET', callback=img)
        self.app.route("/<filepath:re:.*\\.ico>", method='GET', callback=favicon)

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
        :param code: Error code to pair with the function
        :param function: Function callback
        :return:
        """
        self.app.error_handler[code] = function

    def add_errors_handler(self, code, function):
        """
        :param code: List type to allow multiple error codes to be handled in one function call
        :param function: Function callback
        :return:
        """
        for c in code:
            self.app.error_handler[c] = function

    def random_string(self, string_length):
        letters = string.ascii_letters
        return ''.join(random.choice(letters) for i in range(string_length))

    def generate_unique_id(self, table_name, id_name):
        is_unique = False
        new_id = 0
        while not is_unique:
            new_id = self.random_string(20)
            table = self._cursor.execute("SELECT id FROM {} WHERE {} = ?".format(table_name, id_name), (new_id,))
            for t in table:
                if not t:
                    is_unique = True
                    break
                else:
                    continue
            is_unique = True
        return new_id

    def upload_file(self, bottle_file, allowed_exts, file_dir=None, overwrite=False, rename=None):
        name, ext = os.path.splitext(bottle_file.filename)
        if ext not in allowed_exts:
            redirect('/')
            raise Exception('[ FILE ISSUE ] - File Extension is not allowed.')
        else:
            save_path = 'views/data/'
            if file_dir:
                save_path = save_path + file_dir
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            file_path = "{path}/{file}".format(path=save_path, file=bottle_file.filename)
            bottle_file.save(file_path, overwrite=overwrite, rename=rename)
            self.BASE_FILE_DIR = file_path

    def upload_files(self, bottle_file, allowed_exts, file_dir=None, overwrite=False, rename=None):
        for file in bottle_file:
            name, ext = os.path.splitext(file.filename)
            if ext not in allowed_exts:
                redirect('/')
                raise Exception('[ FILE ISSUE ] - File Extension is not allowed: {}.{}'.format(name, ext))
            else:
                save_path = 'views/data/'
                if file_dir:
                    save_path = save_path + file_dir
                if not os.path.exists(save_path):
                    os.makedirs(save_path)

                file_path = "{path}/{file}".format(path=save_path, file=file.filename)
                file.save(file_path, overwrite=overwrite, rename=rename)
                self.ASTATINE_FILE_DIRS.append(file_path)

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
                         server=self._server)
        else:
            self.app.run(host=self._host,
                         port=self._port,
                         debug=self._debug,
                         reloader=self._reload)
        self._endSQLite3()

    def modify_SQL(self, query, values=None):
        """
        :param query: The SQLite3 query you want to make
        :param values: Any values you need to pass into the SQLite3 query
        :return:
        """
        try:
            self._lock.acquire(True)
            self._cursor.execute(("{}".format(query)), values)
            self._conn.commit()
        finally:
            self._lock.release()

    def return_SQL(self, query, values=None, fetchall=True):
        """
        :param query: The SQLite3 query you want to make
        :param values: Any values you need to pass into the SQLite3 query
        :param fetchall: Whether it should <fetchall> or <fetchone>, default is True
        :return:
        """
        if values is not None:
            if fetchall:
                try:
                    self._lock.acquire(True)
                    return self._cursor.execute("{}".format(query), values).fetchall()
                finally:
                    self._lock.release()
            else:
                try:
                    self._lock.acquire(True)
                    return self._cursor.execute("{}".format(query), values).fetchone()
                finally:
                    self._lock.release()
        elif values is None:
            if fetchall:
                try:
                    self._lock.acquire(True)
                    return self._cursor.execute("{}".format(query)).fetchall()
                finally:
                    self._lock.release()
            else:
                try:
                    self._lock.acquire(True)
                    return self._cursor.execute("{}".format(query)).fetchone()
                finally:
                    self._lock.release()

    def function_SQL(self, name, parameters, callback):
        sqlite3.enable_callback_tracebacks(True)
        self._conn.create_function(name, parameters, callback)


class AstatineSQL(object):
    """ Astatine SQLite3 Class """

    def __init__(self, fileName, sql_dir=None):
        self._sqlName = fileName
        self._sqlDir = sql_dir
        self._cursor = None
        self._conn = None
        self._lock = threading.Lock()

    def Connect(self):
        """Creates SQLite3 database."""
        self._conn = sqlite3.connect('{}/{}'.format(self._sqlDir, self._sqlName), check_same_thread=False)
        self._cursor = self._conn.cursor()

    def Commit(self):
        self._conn.commit()

    def Close(self):
        self._cursor.close()

    def modify_SQL(self, query, values=None):
        """
        :param query: The SQLite3 query you want to make
        :param values: Any values you need to pass into the SQLite3 query
        :return:
        """
        try:
            self._lock.acquire(True)
            self._cursor.execute(("{}".format(query)), values)
            self._conn.commit()
        finally:
            self._lock.release()

    def return_SQL(self, query, values=None, fetchall=True):
        """
        :param query: The SQLite3 query you want to make
        :param values: Any values you need to pass into the SQLite3 query
        :param fetchall: Whether it should <fetchall> or <fetchone>
        :return:
        """
        if values is not None:
            if fetchall:
                return self._cursor.execute("{}".format(query), values).fetchall()
            else:
                return self._cursor.execute("{}".format(query), values).fetchone()
        elif values is None:
            if fetchall:
                return self._cursor.execute("{}".format(query)).fetchall()
            else:
                return self._cursor.execute("{}".format(query)).fetchone()

    def function_SQL(self, name, parameters, callback):
        sqlite3.enable_callback_tracebacks(True)
        self._conn.create_function(name, parameters, callback)


class AstatineAES(object):
    """ Astatine Encryption and Decryption Class """

    def __init__(self, key):
        self.bs = AES.block_size
        self.key = hashlib.sha256(key.encode()).digest()

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
