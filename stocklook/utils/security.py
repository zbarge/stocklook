"""
MIT License

Copyright (c) 2017 Zeke Barge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import keyring


class Credentials:
    GDAX = 'gdax'
    POLONIEX = 'poloniex'
    GMAIL = 'gmail'
    COINBASE = 'coinbase'
    BFX = 'bitfinex'
    KRAKEN = 'kraken'
    GDAX_DB = 'gdax_db'
    SERVICE_NAMES = [GDAX, POLONIEX, GMAIL, BFX, KRAKEN]

    # Used to store multiple variables
    # under one key in KeyRing
    JOIN_SEP = '[>>>$xythismustbeuniqueyx$<<<]'

    def __init__(self, data=None, allow_input=True):
        if data is None:
            try:
                from stocklook.config import config as data
            except ImportError:
                print("stocklook.utils.security.Credentials"
                      "(Error retrieving default config dictionary.)")
                data = dict()
        self.data = data
        self.allow_input = allow_input

    def set_with_input(self, service_name, user=None, api=False):
        """
        Guides the user through entering credentials for a particular service
        via the terminal.
        :param service_name:
        :param api: (bool, default False)
            False asks for username/password.
            True asks for key/secret/passphrase
        :return:
        """
        msg = "Please enter credentials for '{}'.".format(service_name)
        print(msg)

        if not api:
            if user is None:
                user = input("Username:").strip()
            pw = input("Password:").strip()
            self.set(service_name, user, pw)
            return user

        if user is None:
            user = input("API Key:").strip()
        secret = input("API Secret:").strip()
        phrase = input("API Passphrase:").strip()
        self.set_api(service_name, user, secret, phrase)
        return user

    def get(self, service_name, username=None, api=False):
        """
        Gets a password from secure storage.
        :param service_name:
        :param username:
        :param api: (bool, default False)
            True will request user input for key, secret, and passphrase if no
            entry has been stored in secure storage.
            False will request user input for only username and password.
        :return:
        """
        if username is None:
            try:
                username = self.data[service_name]
            except KeyError:
                username = input("{} Key/Username:".format(service_name))

        try:
            # Just try getting and returning the password
            # if it's found
            pw = keyring.get_password(service_name, username)
            if pw is not None:
                self.data[service_name] = username
                return pw
        except:
            pw = None
            if not self.allow_input:
                raise

        if pw is None and not self.allow_input:
            raise KeyError("No password found for "
                           "'{}' service.".format(service_name))
        elif pw is None:
            # Securely set password with input.
            username = self.set_with_input(service_name, user=username, api=api)
            self.data[service_name] = username
            return self.get(service_name, username, api)

    def set(self, service_name, username, password):
        """
        Sets a password securely under the username.
        :param service_name:
        :param username:
        :param password:
        :return:
        """
        keyring.set_password(service_name, username, password)
        self.data[service_name] = username

    def set_api(self, service_name, key, secret, passphrase):
        """
        Stores api_secret and api_passphrase securely under the key.
        :param service_name:
        :param key:
        :param secret:
        :param passphrase:
        :return:
        """
        pw = secret + self.JOIN_SEP + passphrase
        self.set(service_name, key, pw)

    def get_api(self, service_name, key=None):
        """
        Returns api_secret, api_passphrase from secure storage.
        :param service_name:
        :param key:
        :return:
        """
        pw = self.get(service_name, username=key, api=True)
        return pw.split(self.JOIN_SEP)

    def reset_credentials(self, service_name, username, new_pass=None, api_pass=None):
        try:
            keyring.delete_password(service_name, username)
        except keyring.errors.PasswordDeleteError:
            pass

        if new_pass is not None:
            if api_pass is not None:
                new_pass = new_pass + self.JOIN_SEP + api_pass
            keyring.set_password(service_name, username, new_pass)

