import datetime
import os

from lib.astatine import Astatine, AstatineJSON, AstatineSQL, AstatineAES, AstatineSMTP
from lib.bottle import template, request, abort, redirect
import re


class Mercury(object):

    def __init__(self):
        self.aj = AstatineJSON('data.json')

        self.server_settings = self.aj.read()['server_settings']
        self.email_settings = self.aj.read()['email_settings']
        self.error_codes = self.aj.read()['error_codes']

        self.spam = self.aj.read()['spam']

        debug = self.server_settings['debug']
        reload = self.server_settings['reload']
        port = self.server_settings['port']
        host = self.server_settings['host']
        quiet = self.server_settings['quiet']
        server = self.server_settings['server']

        self.astatine = Astatine(host, port, debug, reload, server, quiet, 'sql/data.db')
        self.aes = AstatineAES('987xg12kghIKasx87hYUGI7b09zxb')

        self.astatine.enable_sessions()
        self.create_routes()

        self.astatine.create_function_sql('decrypt', 1, self.aes.decrypt)

    def create_routes(self):
        self.astatine.route('/', 'get', self.index, True)

        self.astatine.route('/gallery', 'get', self.gallery, True)
        self.astatine.route('/gallery/upload', 'get', self.post_gallery, True)
        self.astatine.route('/gallery/upload', 'post', self.post_gallery_post, True)
        self.astatine.route('/gallery/<uid>/delete', 'delete', self.delete_gallery, True)

        self.astatine.route('/projects', 'get', self.projects, True)
        self.astatine.route('/projects/<uid>', 'get', self.get_project, True)
        self.astatine.route('/projects/post', 'get', self.post_project, True)
        self.astatine.route('/projects/post', 'post', self.post_project_post, True)
        self.astatine.route('/projects/<uid>/edit', 'get', self.edit_project, True)
        self.astatine.route('/projects/<uid>/edit', 'post', self.edit_project_post, True)
        self.astatine.route('/projects/<uid>/delete', 'delete', self.delete_project, True)

        self.astatine.route('/albums/<uid>', 'get', self.get_album, True)
        self.astatine.route('/album/create', 'get', self.post_album, True)
        self.astatine.route('/album/create', 'post', self.post_album_post, True)
        self.astatine.route('/album/append/<uid>', 'get', self.append_album, True)
        self.astatine.route('/album/append/<uid>', 'post', self.append_album_post, True)

        self.astatine.route('/blogs', 'get', self.blogs, True)
        self.astatine.route('/blogs/<uid>', 'get', self.get_blog, True)
        self.astatine.route('/blogs/post', 'get', self.post_blog, True)
        self.astatine.route('/blogs/post', 'post', self.post_blog_post, True)

        self.astatine.route('/admin', 'get', self.admin, True)

        self.astatine.route('/login', 'get', self.get_code, True)
        self.astatine.route('/login', 'post', self.get_code_post, True)
        self.astatine.route('/code', 'get', self.send_code, True)
        self.astatine.route('/code', 'post', self.send_code_post, True)

        self.astatine.route('/trace', 'get', self.trace, True)

        self.astatine.error(self.error_codes, self.errors)

    def _check_visit(self, session):
        date_current = datetime.datetime.now().timestamp()
        date_start = datetime.datetime.combine(datetime.datetime.now(), datetime.time.min).timestamp()

        check_date_start = self.astatine.execute_sql('SELECT * FROM visit_stats WHERE datetime = ?', (int(date_start), ))

        if not session['last_visit']:
            self.astatine.execute_sql('''UPDATE unique_visit_stats SET visits = visits + 1''')

        if not check_date_start:
            self.astatine.execute_sql('''
                INSERT INTO visit_stats (uid, datetime, visits) VALUES (?,?,?)
            ''', (self.astatine.generate_uid('visit_stats', 'uid'), int(date_start), 1))
        else:
            if session['last_visit']:
                if session['last_visit'] < date_start:
                    self.astatine.execute_sql('''
                        UPDATE visit_stats SET visits = visits + 1 WHERE datetime = ?
                    ''', (int(date_start),))
            else:
                self.astatine.execute_sql('''
                    UPDATE visit_stats SET visits = visits + 1 WHERE datetime = ?
                ''', (int(date_start),))

        session['last_visit'] = date_current

    def _authenticate_user(self, session):
        if session['uid']:
            user = self.astatine.execute_sql(
                'SELECT user_uid FROM sessions WHERE session_uid = ?', (session['uid'], )
            )
            if not user:
                abort(403)
        else:
            abort(403)

    def _is_user(self, session):
        is_user = False
        if session['uid']:
            user = self.astatine.execute_sql(
                'SELECT user_uid FROM sessions WHERE session_uid = ?', (session['uid'], )
            )
            if user:
                is_user = True
        return is_user

    def errors(self, code):
        return template('html/error.tpl', code=code)

    def index(self, session):
        self._check_visit(session)
        projects = self.astatine.execute_sql('SELECT * FROM projects ORDER BY timestamp DESC')
        blogs = self.astatine.execute_sql('SELECT * FROM blogs ORDER BY timestamp DESC LIMIT 2')
        gallery = self.astatine.execute_sql('''
                    SELECT a.*, b.footnote, b.uid FROM files a 
                    INNER JOIN gallery b ON a.uid = b.file_uid
                    ORDER BY timestamp DESC''')
        albums = self.astatine.execute_sql('''
            SELECT a.*, b.path
            FROM image_albums a 
            INNER JOIN files b 
                ON a.thumbnail = b.uid
            ORDER BY timestamp DESC 
            LIMIT 2''')
        return template('html/index.tpl', path=request.url, projects=projects, blogs=blogs, gallery=gallery, albums=albums)

    def admin(self, session):
        self._authenticate_user(session)
        self._is_user(session)
        self._check_visit(session)

        date_start = datetime.datetime.combine(datetime.datetime.now(), datetime.time.min).timestamp()

        date_7_days_ago = datetime.datetime.combine((datetime.datetime.now() - datetime.timedelta(days=7)).date(), datetime.time.min).timestamp()
        date_30_days_ago = datetime.datetime.combine((datetime.datetime.now() - datetime.timedelta(days=30)).date(),
                                                    datetime.time.min).timestamp()

        statistics = self.astatine.execute_sql('''
            SELECT
                (SELECT sum(visits) FROM visit_stats) AS total_visits, 
                (SELECT visits FROM visit_stats WHERE datetime = ?) AS today_visits,
                (SELECT sum(visits) FROM visit_stats WHERE datetime >= ?) AS week_visits,
                (SELECT sum(visits) FROM visit_stats WHERE datetime >= ?) AS month_visits,
                (SELECT visits FROM unique_visit_stats) AS unique_visits
        ''', (date_start, date_7_days_ago, date_30_days_ago), False)

        stats_graph = self.astatine.execute_sql('''SELECT visits, datetime FROM visit_stats ORDER BY datetime ASC''')

        tracking_statistics = self.astatine.execute_sql('''
            SELECT a.site, sum(a.visits) AS total_visits, 
                IFNULL(
                    (SELECT b.visits FROM visit_tracing b WHERE datetime >= ? AND a.site = b.site), 0) 
                AS week_visits
            FROM visit_tracing a
            GROUP BY a.site
            ORDER BY total_visits DESC
        ''', (date_7_days_ago, ))

        return template('html/admin.tpl', path=request.url, statistics=statistics, tracking_statistics=tracking_statistics, stats_graph=stats_graph)

    def trace(self):
        site = request.query.site
        route = request.query.route
        date_start = datetime.datetime.combine(datetime.datetime.now(), datetime.time.min).timestamp()

        check = self.astatine.execute_sql('SELECT * FROM visit_tracing WHERE site = ? AND datetime = ?', (site, date_start))

        if not check:
            self.astatine.execute_sql('''
                INSERT INTO visit_tracing (uid, datetime, site, visits) VALUES (?,?,?,?)
            ''', (self.astatine.generate_uid('visit_tracing', 'uid'), date_start, site, 1))
        else:
            self.astatine.execute_sql('''
                UPDATE visit_tracing SET visits = visits + 1 WHERE site = ? AND datetime = ?
            ''', (site, date_start))
        redirect(f'/{route if route else ""}')

    def get_code(self, session):
        self._check_visit(session)
        return template('html/user/login.tpl', path=request.url)

    def get_code_post(self, session):
        self._check_visit(session)
        email = request.forms.get('email')
        user = self.astatine.execute_sql('SELECT * FROM users WHERE decrypt((SELECT email FROM users)) = ?', (email, ), False)
        html = None
        if user:
            code = self.astatine.random_string(6)
            self.astatine.execute_sql('INSERT INTO user_codes (uid, user_uid) VALUES (?,?)', (code, user[0]))
            with open('views/email/login_code.html', 'r') as f:
                html = f.read().replace('%1', code)
            self.smtp.send_email(email, 'login code', html=html)
            redirect('/code')
        else:
            redirect('/')

    def send_code(self, session):
        self._check_visit(session)
        return template('html/user/code.tpl', path=request.url)

    def send_code_post(self, session):
        self._check_visit(session)
        code = request.forms.get('code')
        check = self.astatine.execute_sql('SELECT * FROM user_codes WHERE uid = ?', (code, ), False)
        if check:
            self.astatine.execute_sql('DELETE FROM user_codes WHERE uid = ?', (code, ))
            session_uid = self.astatine.generate_uid('sessions', 'session_uid')
            session['uid'] = session_uid
            self.astatine.execute_sql('INSERT INTO sessions (uid, session_uid, user_uid) VALUES (?,?,?)', (self.astatine.generate_uid('sessions', 'uid'), session_uid, check[1]))
            redirect('/admin')
        else:
            redirect('/')

    def post_blog(self, session):
        self._check_visit(session)
        self._authenticate_user(session)
        return template('html/blogs/create.tpl', session=session, path=request.url, old_blog=None)

    def post_blog_post(self, session):
        self._check_visit(session)
        self._authenticate_user(session)
        title = request.forms.get('title')
        content = request.forms.get('content')
        uid = self.astatine.generate_uid('blogs', 'uid')
        hashtags = request.forms.get('hashtags')
        self.astatine.execute_sql('INSERT INTO blogs (uid, title, content, hashtags, timestamp) VALUES (?,?,?,?,?)', (uid, title, content, hashtags, datetime.datetime.now().timestamp()))
        redirect(f'/blogs/{uid}')

    def edit_blog(self, session, uid):
        self._check_visit(session)
        self._authenticate_user(session)
        blog = self.astatine.execute_sql('SELECT * FROM blogs WHERE uid = ?', (uid, ), False)
        return template('html/blogs/create.tpl', session=session, path=request.url, old_blog=blog)

    def edit_blog_post(self, session, uid):
        self._check_visit(session)
        self._authenticate_user(session)
        title = request.forms.get('title')
        content = request.forms.get('content')
        self.astatine.execute_sql('UPDATE blogs SET title = ?, content = ? WHERE uid = ?', (title, content, uid))
        redirect(f'/blogs/{uid}')

    def delete_blog(self, session, uid):
        self._check_visit(session)
        self._authenticate_user(session)
        self.astatine.execute_sql('DELETE FROM blogs WHERE uid = ?', (uid,))
        redirect('/blogs')

    def post_project(self, session):
        self._check_visit(session)
        self._authenticate_user(session)
        return template('html/projects/create.tpl', session=session, path=request.url, old_project=None)

    def post_project_post(self, session):
        self._check_visit(session)
        self._authenticate_user(session)
        title = request.forms.get('title')
        description = request.forms.get('description')
        link = request.forms.get('link')
        content = request.forms.get('content')
        uid = self.astatine.generate_uid('projects', 'uid')
        self.astatine.execute_sql('INSERT INTO projects (uid, title, description, hyperlink, content, timestamp) '
                                  'VALUES (?,?,?,?,?,?)', (uid, title,
                                                           description, link, content,
                                                           datetime.datetime.now().timestamp()))
        redirect(f'/projects/{uid}')

    def edit_project(self, session, uid):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        project = self.astatine.execute_sql('SELECT * FROM projects WHERE uid = ?', (uid, ), False)
        return template('html/projects/create.tpl', session=session, path=request.url, old_project=project)

    def edit_project_post(self, session, uid):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        title = request.forms.get('title')
        description = request.forms.get('description')
        link = request.forms.get('link')
        content = request.forms.get('content')
        self.astatine.execute_sql('UPDATE projects SET title = ?, description = ?, hyperlink = ?, content = ? WHERE uid = ?', (title, description, link, content, uid))
        redirect(f'/projects/{uid}')

    def delete_project(self, session, uid):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        self.astatine.execute_sql('DELETE FROM projects WHERE uid = ?', (uid,))
        redirect('/projects')

    def get_album(self, session, uid):
        files = self.astatine.execute_sql('''
            SELECT b.*
            FROM album_files a
            INNER JOIN files b
                ON b.uid = a.file_uid
            WHERE a.album_uid = ?
            ORDER BY b.timestamp DESC
        ''', (uid, ))
        album_name = self.astatine.execute_sql('SELECT name FROM image_albums WHERE uid = ?', (uid,), False)
        return template('html/albums/album.tpl', session=session, path=request.url, files=files, uid=uid, admin=self._is_user(session), album_name=album_name)

    def post_album(self, session):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        return template('html/albums/create.tpl', session=session, path=request.url)

    def post_album_post(self, session):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        title = request.forms.get('title')
        thumbnail = request.files.get('thumbnail')
        album_uid = self.astatine.generate_uid('image_albums', 'uid')
        thumbnail_uid = self.astatine.generate_uid('files', 'uid')
        self.astatine.upload_files([thumbnail], '*', f'user_data/albums/{album_uid}/thumbnail/')
        self.astatine.execute_sql('''
            INSERT INTO files (uid, path, type, timestamp) VALUES (?,?,?,?)
        ''', (thumbnail_uid, f'/user_data/albums/{album_uid}/thumbnail/{thumbnail.filename}', 102, datetime.datetime.now().timestamp()))
        self.astatine.execute_sql('''
            INSERT INTO image_albums (uid, name, thumbnail, timestamp) VALUES (?,?,?,?)
        ''', (album_uid, title, thumbnail_uid, datetime.datetime.now().timestamp()))
        redirect(f'/album/append/{album_uid}')

    def append_album(self, session, uid):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        album_name = self.astatine.execute_sql('SELECT name FROM image_albums WHERE uid = ?', (uid, ), False)
        return template('html/albums/append.tpl', session=session, uid=uid, path=request.url, album_name=album_name)

    def append_album_post(self, session, uid):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        file = request.files.get('file')
        file_uid = self.astatine.generate_uid('files', 'uid')
        self.astatine.upload_files([file], '*', f'user_data/albums/{uid}/')
        self.astatine.execute_sql('''
            INSERT INTO files (uid, path, type, timestamp) VALUES (?,?,?,?)
        ''', (file_uid, f'/user_data/albums/{uid}/{file.filename}', 103,
              datetime.datetime.now().timestamp()))
        self.astatine.execute_sql('''
            INSERT INTO album_files (uid, album_uid, file_uid) VALUES (?,?,?)
        ''', (self.astatine.generate_uid('album_files', 'uid'), uid, file_uid))
        redirect(f'/album/append/{uid}')

    def blogs(self, session):
        self._check_visit(session)
        hashtags = request.query.tags

        if hashtags:
            blogs = self.astatine.execute_sql('SELECT * FROM blogs WHERE hashtags LIKE ? ORDER BY timestamp DESC', ('%' + hashtags + '%', ))
        else:
            blogs = self.astatine.execute_sql('SELECT * FROM blogs ORDER BY timestamp DESC')
        return template('html/blogs.tpl', blogs=blogs, path=request.url, hashtags=hashtags)

    def get_blog(self, session, uid):
        self._check_visit(session)
        blog = self.astatine.execute_sql('''SELECT * FROM blogs WHERE uid = ?''', (uid,), False)
        return template('html/blogs/blog.tpl', blog=blog, path=request.url, admin=self._is_user(session))

    def gallery(self, session):
        self._check_visit(session)
        gallery = self.astatine.execute_sql('''
            SELECT a.*, b.footnote, b.uid FROM files a 
            INNER JOIN gallery b ON a.uid = b.file_uid
            ORDER BY timestamp DESC''')
        return template('html/gallery.tpl', path=request.url, gallery=gallery, admin=self._is_user(session))

    def post_gallery(self, session):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        return template('html/gallery/create.tpl', path=request.url)

    def post_gallery_post(self, session):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        image = request.files.get('image')
        footnote = request.forms.get('footnote')
        file_uid = self.astatine.generate_uid('files', 'uid')
        self.astatine.execute_sql('INSERT INTO files (uid, path, type, timestamp) VALUES(?,?,?,?)', (
        file_uid, '/user_data/gallery/{}'.format(file_uid + os.path.splitext(image.filename)[1]), 101, datetime.datetime.now().timestamp()))
        self.astatine.execute_sql('INSERT INTO gallery (uid, file_uid, footnote) VALUES (?,?,?)',
                                  (self.astatine.generate_uid('gallery', 'uid'), file_uid, footnote))
        self.astatine.upload_files([image], '*', 'user_data/gallery/', rename=file_uid)
        redirect('/gallery/upload')

    def delete_gallery(self, session, uid):
        self._check_visit(session)
        self._authenticate_user(session)
        self._is_user(session)
        file_uid = self.astatine.execute_sql('SELECT file_uid, path FROM gallery WHERE uid = ?', (uid, ), False)
        self.astatine.execute_sql('DELETE FROM gallery WHERE uid = ?', (uid, ))
        self.astatine.execute_sql('DELETE FROM files WHERE uid = ?', (file_uid[0], ))
        os.remove(file_uid[1])
        redirect('/gallery')

    def projects(self, session):
        self._check_visit(session)
        projects = self.astatine.execute_sql('SELECT * FROM projects ORDER BY timestamp DESC')
        return template('html/projects.tpl', path=request.url, projects=projects)

    def get_project(self, session, uid):
        self._check_visit(session)
        project = self.astatine.execute_sql('SELECT * FROM projects WHERE uid = ?', (uid, ), False)
        return template('html/projects/project.tpl', project=project, path=request.url, admin=self._is_user(session))


if __name__ == '__main__':
    webapp = Mercury()
    webapp.astatine.run_astatine()
