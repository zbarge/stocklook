import requests
from time import sleep


class APIError(Exception):
    pass


def call_api(url, method='get', _api_exception_cls=None, **kwargs):
    """
    This method is rate limited to ~3 calls per second max.
    It should handle ALL communication with the Gdax API.
    :param url:
    :param method: ('get', 'delete', 'post')
    :param kwargs:
    :return:
    """
    try:
        if method == 'get':
            res = requests.get(url, **kwargs)
        elif method == 'delete':
            res = requests.delete(url, **kwargs)
        elif method == 'post':
            res = requests.post(url, **kwargs)
        else:
            raise NotImplementedError("Method '{}' not available "
                                      "for calling API.".format(method))
    except Exception as e:
        e = str(e)
        retry = '11001' in e \
                or 'unreachable host' in e \
                or ('forcibly' in e
                    and 'existing' in e)\
                or '504' in e

        if retry:
            sleep(1)
            return call_api(url, method=method, **kwargs)

        raise

    if res.status_code != 200:

        if res.status_code == 504:
            return call_api(url, method=method, **kwargs)

        try:
            res_json = res.json()
        except (ValueError, AttributeError):
            res_json = ''

        msg = '<{}>: method: {}:{}, {}'.format(res.status_code,
                                               method,
                                               res.url,
                                               res_json)
        if _api_exception_cls is None:
            _api_exception_cls = APIError

        raise _api_exception_cls(msg)

    return res


