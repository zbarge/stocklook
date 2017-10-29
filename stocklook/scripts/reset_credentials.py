# You should remove USERNAME/PASSWORD variables after running this script.

SERVICE_NAME = 'coinbase'
USER_NAME = ''
PASSWORD = ''
PASSPHRASE = None


if __name__ == '__main__':
    from stocklook.utils.security import Credentials
    c = Credentials()
    c.reset_credentials(SERVICE_NAME, USER_NAME, PASSWORD, PASSPHRASE)