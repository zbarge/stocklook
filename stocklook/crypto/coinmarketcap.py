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

Some code on this page was copied from:
https://github.com/mrsmn/coinmarketcap

Copyright 2014-2017 Martin Simon

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import requests
import requests_cache


class CoinMarketCap(object):

    _session = None
    __DEFAULT_BASE_URL = 'https://api.coinmarketcap.com/v1/'
    __DEFAULT_TIMEOUT = 120

    def __init__(self, base_url = __DEFAULT_BASE_URL, request_timeout = __DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.request_timeout = request_timeout

    @property
    def session(self):
        if not self._session:
            self._session = requests_cache.core.CachedSession(
                cache_name='coinmarketcap_cache', 
                backend='sqlite', 
                expire_after=120)
            c = {
                'Content-Type': 'application/json',
                'User-agent': 'coinmarketcap - python wrapper'
                              'around coinmarketcap.com '
                              '(github.com/zbarge/stocklook)'}
            self._session.headers.update(c)
        return self._session

    def __request(self, endpoint, params):
        response_object = self.session.get(
            self.base_url + endpoint,
            params=params,
            timeout=self.request_timeout)

        if response_object.status_code != 200:
            raise Exception('An error occured, please try again.')
        try:
            response = json.loads(response_object.text)
            if isinstance(response, list):
                response = [dict(item, **{u'cached':response_object.from_cache})
                            for item in response]
            if isinstance(response, dict):
                response[u'cached'] = response_object.from_cache
        except requests.exceptions.RequestException as e:
            return e

        return response

    def ticker(self, currency="", **kwargs):
        """
        Returns a dict containing one/all the currencies
        Optional parameters:
        (int) limit - only returns the top limit results.
        (string) convert - return price, 24h volume, and market cap in terms of another currency. Valid values are:
        "AUD", "BRL", "CAD", "CHF", "CNY", "EUR", "GBP", "HKD", "IDR", "INR", "JPY", "KRW", "MXN", "RUB"
        """

        params = {}
        params.update(kwargs)
        response = self.__request('ticker/' + currency, params)
        return response

    def stats(self, **kwargs):
        """
        Returns a dict containing cryptocurrency statistics.
        Optional parameters:
        (string) convert - return 24h volume, and market cap in terms of another currency. Valid values are:
        "AUD", "BRL", "CAD", "CHF", "CNY", "EUR", "GBP", "HKD", "IDR", "INR", "JPY", "KRW", "MXN", "RUB"
        """

        params = {}
        params.update(kwargs)
        response = self.__request('global/', params)
        return response

if __name__ == '__main__':
    m = CoinMarketCap()
    s = m.stats()
    print(s)
    