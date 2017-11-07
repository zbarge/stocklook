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
class EmailSender:
    """
    Wraps yagmail with stocklook.utils.security.Credentials
    for secure access/storage of credentials. You should
    make a free gmail account to use this and set the
    GMAIL_EMAIL via stocklook.config.update_config(dict).
    """
    def __init__(self, email=None, **kwargs):
        self.email = email
        self._kwargs = kwargs
        self._smtp = None

    @property
    def smtp(self):
        if self._smtp is None:
            from yagmail import SMTP
            self.set_credentials()
            self._smtp = SMTP(self.email, **self._kwargs)
        return self._smtp

    def set_credentials(self):
        pw = self._kwargs.get('password', None)

        if self.email is None:
            from ..config import config
            self.email = config.get('GMAIL_EMAIL', None)
            if pw is None:
                pw = config.get('GMAIL_PASSWORD', None)
                if pw is not None:
                    self._kwargs['password'] = pw

        if not self.email or not pw:
            # We'll retrieve one or both from secure storage.
            from .security import Credentials
            c = Credentials(allow_input=True)
            pw = c.get(c.GMAIL, username=self.email, api=False)
            self._kwargs['password'] = pw
            self.email = c.data[c.GMAIL]


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