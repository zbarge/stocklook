from flask import Flask, g, flash, abort, session, request, url_for, redirect, render_template


app = Flask('stocklook')
app.config.from_object(__name__)
try:
    app.config.from_envvar('STOCKLOOK_WEB_SETTINGS', silent=False)
except RuntimeError as e:
    print(e)


@app.route('/')
def index():
    return "Hello"


@app.route('/login')
def login():
    return "Username, Password:"


if __name__ == '__main__':
    app.run()