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
from warnings import warn


class Credentials:
    BITMEX = 'bitmex'
    BITTREX = 'bittrex'
    CRYPTOPIA = 'cryptopia'
    GDAX = 'gdax'
    POLONIEX = 'poloniex'
    GMAIL = 'gmail'
    COINBASE = 'coinbase'
    BFX = 'bitfinex'
    KRAKEN = 'kraken'
    GDAX_DB = 'gdax_db'

    SERVICE_NAMES = [BITTREX, CRYPTOPIA, GDAX,
                     POLONIEX, GMAIL, BFX, KRAKEN]
    CONFIG_TO_OBJECT_MAP = dict()

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

    def _join_password_items(self, pw_items):
        if not pw_items:
            return pw_items
        if len(pw_items) == 1:
            return pw_items[0]
        return self.JOIN_SEP.join(pw_items)

    def _split_password_string(self, pw_string):
        if not pw_string or self.JOIN_SEP not in pw_string:
            return pw_string
        return pw_string.split(self.JOIN_SEP)

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
        self.set(service_name, user,
                 self._join_password_items([secret, phrase]))
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

    @staticmethod
    def register_config_object_mapping(service_name, map_data):
        """
        Registers a map of {CONFIG_KEY: OBJECT_PROPERTY_NAME}
        for a particular service name.

        Objects that need automatic private access key/secret(s) should
        register the configuration key names to object property values.

        Doing this lets the Credentials object know where to look in
        config for a needed key or secret.

        Example:
        ---------

            from mailyo.config import config
            API_KEY1 = 'API_KEY1'
            API_SECRET1 = 'API_SECRET1'
            API_SVC_NAME1 = 'API_SVC_NAME1'

            creds = Credentials()

            class ApiObj1:
                creds.register_config_object_mapping(
                    API_SVC_NAME1,
                    {
                    API_KEY1: 'key',
                    API_SECRET1: 'secret'
                    }

                )
                # Registers configuration keys to
                # object property nammes for ApiObj1

                def __init__(key=None, secret=None):
                    self.key = key
                    self.secret = secret

                    if not all((key, secret)):
                        creds.configure_object_vars(
                            self, API_SVC_NAME1, 'key', ['secret'])
                        # Finds api key and secret (or helps user input)
                        # within config and/or KeyRing.

        :param service_name: (str)
            The name of the service to register map data to.

        :param map_data: (dict)
            A mapping of {CONFIG_KEY: OBJECT_PROPERTY_NAME}
            for the object that will access the service name.

        :return: (None)
        """
        map_data.update({v: k for k, v in map_data.items()})
        Credentials.CONFIG_TO_OBJECT_MAP.update({service_name: map_data})

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

    def get_config_value(self, service_name, key_name):
        """
        Tries returning a raw value from config in the following order:
        1) return a value stored in Credentials.data matching :param key
        2) return a value stored in Credentials.data matching :param key translated via
           Credentials.CONFIG_TO_OBJECT_MAP.

        Retrieving values in this way ensures that we are
        searching all available ways the value
        could/should be stored for the stocklook app.

        :param service_name:
        :param key:
        :return:
        """

        try:
            return self.data[key_name]
        except KeyError:
            pass

        try:
            key_map = self.CONFIG_TO_OBJECT_MAP[service_name]
            key_label = key_map[key_name]
            return self.data[key_label]
        except KeyError:
            pass

    def configure_object_vars(self, dest_obj, service_name, key_name, secret_items):
        """
        Configures an object's username and multiple secret
        items using stocklook.config.config and KeyRing.

        Manual user input may be required but secret items will be joined and registered to
        KeyRing. Usernames manually inputted are lost.

        :param dest_obj: (object)
            An initialized class object with secret variables to set.

        :param service_name: (str)
            The service name for KeyRing.

        :param key_name: (str)
            The username or API key variable name for the :param dest_obj

        :param secret_items: (list)
            A list of one or more secret :param dest_object property
             names to assign secret values to.

        :return: (None)
            The :param dest_object will have matched properties
            assigned with values found in config and/or KeyRing.
        """
        key_value = getattr(dest_obj, key_name)

        if not hasattr(secret_items, '__iter__'):
            secret_items = [secret_items]

        # Get/assign object's username
        if key_value is None:
            key_value = self.get_config_value(service_name, key_name)
            if key_value is None:
                key_value = input("Enter {} username/key:".format(
                    service_name)).strip()
                warn("To avoid manual key input multiple "
                     "times please update stocklook.config.config with "
                     "{}".format(self.CONFIG_TO_OBJECT_MAP[key_name]))
            setattr(dest_obj, key_name, key_value)

        # Set missing secrets via config.
        for s in secret_items:
            if getattr(dest_obj, s, None)is None:
                v = self.get_config_value(service_name, s)
                setattr(dest_obj, s, v)

        # Check for missing secrets
        secrets_avail = {
            s: getattr(dest_obj, s, None)
            for s in secret_items}

        if not all(secrets_avail.values()):
            # Set missing secrets from KeyRing
            v = keyring.get_password(service_name, key_value)
            sets_needed = True
            if v is not None:
                secret_vals = self._split_password_string(v)
                if len(secret_vals) == len(secret_items):

                    for k, v in zip(secret_items, secret_vals):
                        setattr(dest_obj, k, v)
                    sets_needed = False

            if sets_needed:
                # Set missing values to KeyRing (& object) from user input.
                secrets_avail = {k: (v if v is not None
                                     else input("Enter {} {}:".format(
                                                service_name, k)).strip())
                                 for k, v in secrets_avail.items() }
                pw_string = self._join_password_items(
                    [secrets_avail[i] for i in secret_items])
                self.set(service_name, key_value, pw_string)
                [setattr(dest_obj, k, secrets_avail[k]) for k in secret_items]
        else:
            # Log secret values to KeyRing
            pw_string = self._join_password_items(
                [secrets_avail[i] for i in secret_items])
            self.set(service_name, key_value, pw_string)

    def reset_credentials(self, service_name, username, new_secret_items=None):
        """
        Removes a username/password from KeyRing
        and replaces with a new one if desired.

        :param service_name: (str)
            The service name to remove.

        :param username: (str)
            The username to remove the password for.

        :param new_secret_items: (list, default None)
            The new secret item(s) to assign to the username if desired.

        :return: (None)
        """
        try:
            keyring.delete_password(service_name, username)
        except keyring.errors.PasswordDeleteError:
            pass

        if new_secret_items:
            new_pass = self._join_password_items(new_secret_items)
            keyring.set_password(service_name, username, new_pass)

