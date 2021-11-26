"""
CHANGES (Simon Harrison 2018-03-26):
secret_key has been removed and pickle replaced with json.
session['some key'] = 'some value' -- saves the new session

-- Adapted from below:

https://github.com/promek/bottle-pxsession
License: MIT (see LICENSE for details)

bottle_pxsession is a secure pickle based session library

EXAMPLE USAGE
=============
import bottle
import bottle_pxsession

app = bottle.default_app()
plugin = bottle_pxsession.SessionPlugin(cookie_lifetime=600)
app.install(plugin)

@bottle.route('/')
def index(session):
    #print session.items()
    #print session.has_key('test')
    session['test'] = session.get('test', 0) + 1
    session.save() # save session
    return 'Test : %d' % session['test']
bottle.run(app=app)
"""
__author__ = 'ibrahim SEN'
__version__ = '0.1.0'
__license__ = 'MIT'


from bottle import PluginError, request, response
import inspect
import json
import uuid
import os
import time

def getUuid():
    return uuid.uuid4()


MAX_TTL = 14*24*3600 # 14 day maximum cookie limit for sessions


class Session(object):

    def __init__(self, session_dir="/tmp", cookie_name='px.session',
                 cookie_lifetime=None):
        self.session_dir = session_dir
        self.cookie_name = cookie_name
        self.sessionid = None
        if cookie_lifetime is None:
            self.ttl = MAX_TTL
            self.max_age = None
        else:
            self.ttl = cookie_lifetime
            self.max_age = cookie_lifetime

        self.data = None
        
        if self.get_cookie():
            self.load_session(self.get_cookie())
        else:
            self.new_session()

    def get_cookie(self):
        uid_cookie = request.get_cookie(self.cookie_name)
        return uid_cookie

    def set_cookie(self, value):
        response.set_cookie(self.cookie_name, value, 
                            max_age=self.max_age, path='/')

    def get_session(self):
        return self.load_session(self.cookie_value)

    def load_session(self, cookie_value):
        self.sessionid = uuid.UUID(cookie_value).hex
        fileName = os.path.join(self.session_dir, 'sess-px-%s' % self.sessionid)
        if os.path.exists(fileName):
            with open(fileName, 'r') as fp:
                self.data = json.load(fp)
        else:
            self.new_session()

    def new_session(self):
        uid = getUuid()
        self.sessionid = uid.hex
        self.set_cookie(self.sessionid)
        self.data = {'_ttl': self.ttl, '_utm': time.time(), '_sid': self.sessionid}
        self.save()

    def save(self):
        fileName = os.path.join(self.session_dir, 'sess-px-%s' % self.sessionid)
        with open(fileName, 'w') as fp:
            json.dump(self.data, fp)

    def expire(self):
        now = time.time()
        if self.data['_utm'] > (now-self.data['_ttl']):
            self.data['_utm']=now
        else:
            self.regenerate()

    def destroy(self):
        fileName = os.path.join(self.session_dir, 'sess-px-%s' % self.sessionid)
        if os.path.exists(fileName):
            os.remove(fileName)
        response.delete_cookie(self.cookie_name)

    def regenerate(self):
        self.destroy()
        self.new_session()

    def __contains__(self, key):
        if key in self.data:
            return True
        else:
            return False

    def __delitem__(self, key):
        del self.data[key]

    def __getitem__(self, key):
        self.expire()
        if key in self.data:
            return self.data[key]
        else :
            return None

    def __setitem__(self, key,value):
        self.expire()
        self.data[key]=value
        self.save()

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        for t in list(self.data.items()):
            yield t

    def get(self, key, default=None):
        retval = self.__getitem__(key)
        if retval == None:
            retval = default
        return retval

    def has_key(self,key):
        return self.__contains__(key)

    def items(self):
        return list(self.data.items())

    def keys(self):
        return list(self.data.keys())

    def values(self):
        return list(self.data.values())


class SessionPlugin(object):
    name = 'session'
    api = 2

    def __init__(self, session_dir="/tmp", cookie_name='px.session',
                 cookie_lifetime=300, keyword='session'):
        self.session_dir = session_dir
        self.cookie_name = cookie_name
        self.cookie_lifetime = cookie_lifetime
        self.keyword = keyword

    def setup(self, app):
        for other in app.plugins:
            if not isinstance(other, SessionPlugin): continue
            if other.keyword == self.keyword:
                raise PluginError("Found another session plugin with "\
                "conflicting settings (non-unique keyword).")

    def apply(self, callback, context):
        conf = context.config.get('session') or {}
        args = inspect.getfullargspec(context.callback)[0]

        if self.keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            kwargs[self.keyword] = Session(self.session_dir,
                                           self.cookie_name,
                                           self.cookie_lifetime)
            rv = callback(*args, **kwargs)
            return rv
        return wrapper

