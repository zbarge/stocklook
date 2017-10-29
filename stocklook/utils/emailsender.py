
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