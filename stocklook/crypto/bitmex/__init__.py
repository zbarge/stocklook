import argparse
import os

import shutil


__version__ = 'v1.3'


def run():
    parser = argparse.ArgumentParser(description='sample BitMEX market maker')
    parser.add_argument('command', nargs='?', help='Instrument symbol on BitMEX or "setup" for first-time config')
    args = parser.parse_args()

    if args.command is not None and args.command.strip().lower() == 'setup':
        copy_files()

    else:
        # import market_maker here rather than at the top because it depends on settings.py existing
        try:
            from market_maker import market_maker
            market_maker.run()
        except ImportError:
            print('Can\'t find settings.py. Run "marketmaker setup" to create project.')


def copy_files():
    package_base = os.path.dirname(__file__)

    if not os.path.isfile(os.path.join(os.getcwd(), 'settings.py')):
        shutil.copyfile(os.path.join(package_base, '_settings_base.py'), 'settings.py')

    try:
        shutil.copytree(package_base, os.path.join(os.getcwd(), 'market_maker'))
        print('Created marketmaker project.\n**** \nImportant!!!\nEdit settings.py before starting the bot.\n****')
    except FileExistsError:
        print('Market Maker project already exists!')
