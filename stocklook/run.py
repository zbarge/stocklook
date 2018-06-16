from flask import Flask, g, flash, abort, session, request, url_for, redirect, render_template
import jinja2, os


app = Flask('stocklook',
            #template_folder=os.path.join(os.path.dirname(__file__), 'templates')
            )
app.config.from_object(__name__)

try:
    app.config.from_envvar('STOCKLOOK_WEB_SETTINGS', silent=False)
except RuntimeError as e:
    print(e)


@app.route('/')
def index():
    for dirname, subdirs, files in os.walk('/static'):
        for f in files:
            print(f)
    print("walked static dir.")
    return render_template('index.html')


@app.route('/login')
def login():
    return "Username, Password:"


if __name__ == '__main__':
    app.run()