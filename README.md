# Astatine API

Made by __tygzy__ - [https://github.com/tygzy](https://github.com/tygzy)

## A class for the Bottle API to reduce clutter and difficulty while creating a website.

### Summary of features:

- When adding a file to your html file e.g. CSS you only need to provide the filepath past the 'css' directory,
if the css file is in that main directory you only need to provide the file name.
    - This is the same if you use a file inside your CSS e.g. an svg reference you only need to provide the file name unless the file is embedded further in the directory.
    - This is also the case for other file types such as `.js .css .scss .svg .jpg .png .ttf .eot .ttf .woff .woff2`.
- All basic website directories will be made when you call the class for the first time if the directories don't already exist.
- To use sessions the 'add_session_support()' function, this needs to be called otherwise sessions won't be enabled.
- For allowing a user to download a file make a link with the route '/download/<filename>'.
- When uploading a file to the web server, it will automatically upload to `/views/data`.
- The base class also allows the use of SQLite3 with ease, requiring no setup, just use the `modify_SQL()` and `return_SQL()` functions to interact with your database.
- A function that allows the creation of a UUID that checks in a provided table whether that UUID already exists to make sure it is unique.

## Examples

```
class Website(object):
    def __init__(self):
        debug = True
        reload = True
        port = 8080
        host = "localhost"
        self.astatine = Astatine(host, port, debug, reload)
        self.astatine.enable_sessions()
        self.create_routes()

    def create_routes(self):
        self.astatine.add_route('/', 'GET', self.index, True)
        self.astatine.add_error_handler(404, self.error_page)

    def index(self, session):
        return template('html/index.tpl', session=session)

    def error_page(self, error):
        return "<h1>404 Error!</h1>"

if __name__ == '__main__':
    web = Website()
    web.astatine.run_astatine()
```

__This will create a basic website with an index page and also handle a 404 error__, which may seem like a lot of code, but this allows much easier code writing further on in development. With using static files, interacting with a database, using sessions and uploading files.

Error handling.

```
    # You can use this:
    self.astatine.add_error_handler(404, self.error_page)

    # Or this to handle multiple kinds of errors all in one function
    self.astatine.add_error_handler([400, 401, 402, 403, 404], self.error_page)
```

The two methods of interacting with an SQLite3 database.

```
results = self.astatine.return_SQL("SELECT * FROM table WHERE NOT id = ? LIMIT 3", (1,))

self.astatine.modify_SQL("INSERT INTO table (id, name, age) VALUES (?,?,?)", (1, "tygzy", 18))
```

How to upload a file using Bottle Base API.

```
self.astatine.upload_file(bottle_file=file, allowed_exts=('.jpg', '.png'), file_dir='img/', overwrite=True)
```
