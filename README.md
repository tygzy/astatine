# astatine

Bottle framework to allow use with classes as well as providing extra functionality, this makes making a website with Bottle a lot faster.

How to use astatine:

```py
from astatine import Astatine
from bottle import template

class Website(object):

    def __init__(self):
        self.astatine = Astatine('localhost', 8080, True, True, 'server', True, 'data.db') # initialize class

        self.astatine.enable_sessions() # enable cookies / sessions, not required to create a website
        self.create_routes() 

    def create_routes(self):
        self.astatine.route('/', 'get', self.index, True) # create a route and link it to a function
        
        self.astatine.error(404, self.error) # create an error page and link it to a function

    def index(self, session):
        return template('html/index.html')
    
    def error(self, code):
        return template('html/error.tpl', code=code)

if __name__ == '__main__':
    web = Website()
    web.astatine.run_astatine() # run bottle with a built-in astatine function
```

This will create a website with an index page and an error handler.

Astatine also offers many other functions to make the process of creating a website easier, 
such as file uploads and downloads, static files.
There are also 4 other classes alongside the main Bottle class, one for AES, 
to encrypt things such as passwords, an SMTP class, 
JSON class and a separate SQLite class, to allow multiple sqlite databases on a singular website.
