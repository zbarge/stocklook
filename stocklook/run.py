from flask import Flask, g, flash, abort, session, request, url_for, redirect, render_template
import jinja2, os
from stocklook.controls.crypto import CryptoController


app = Flask('stocklook',
            #template_folder=os.path.join(os.path.dirname(__file__), 'templates')
            )
app.config.from_object(__name__)
cctrl = CryptoController()
try:
    app.config.from_envvar('STOCKLOOK_WEB_SETTINGS', silent=False)
except RuntimeError as e:
    print(e)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return "Username, Password:"


@app.route('/portfolio')
def portfolio():
    data = cctrl.get_balances()['data']
    totals = {ex: round(sum([d['value'] for d in k.values()]), 2)
              for ex, k in data.items()}
    grand_total = sum(totals.values())
    return render_template(
        'portfolio.html', account_data=data,
         totals=totals, grand_total=grand_total)


@app.route('/orders')
def orders():
    return render_template('orders.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


if __name__ == '__main__':
    cctrl.build_accounts(acc_types=['gdax'])
    app.run(debug=True)