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
from stocklook.utils.security import Credentials
from stocklook.config import config, GMAIL_EMAIL, STOCKLOOK_NOTIFY_ADDRESS, GMAIL_PASSWORD


class EmailSender:
    """
    Wraps yagmail with stocklook.utils.security.Credentials
    for secure access/storage of credentials. You should
    make a free gmail account to use this and set the
    GMAIL_EMAIL via stocklook.config.update_config(dict).
    """
    Credentials.register_config_object_mapping(Credentials.GMAIL, {GMAIL_EMAIL: 'email',
                                                                   GMAIL_PASSWORD: 'password'})
    def __init__(self, email=None, password=None, **kwargs):
        self.email = email
        self._kwargs = kwargs
        self._smtp = None
        self.password = password
        if not all((email, password)):
            c = Credentials()
            c.configure_object_vars(
                self, c.GMAIL, 'email', ['password'])
            self._kwargs['password'] = self.password


    @property
    def smtp(self):
        if self._smtp is None:
            from yagmail import SMTP
            self._smtp = SMTP(self.email, **self._kwargs)
        return self._smtp




def send_message(to_addr, msg, sender=None):
    """
    This function is used by internal notification methods throughout
    stocklook. Pretty much dead-locked to gmail users & EmailSender at this time.
    No plans to change that soon.
    :param to_addr:
    :param msg:
    :param sender:
    :return:
    """
    if sender is None:
        close = True
        sender = EmailSender()
    else:
        close = False

    smtp = sender.smtp
    smtp.send(to=to_addr, contents=msg)

    if close:
        smtp.close()
    return True