#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Monitor a basket of currencies relative to the USD and highlight changes

    > python3 exchange.py

    ** Requires CL_KEY to be set in OS shell environment **

    See: https://currencylayer.com/documentation

    Public domain by Michael OConnor <gmikeoc@gmail.com>
    Also available under the terms of MIT license
    Copyright (c) 2018 Michael O'Connor
"""

__version__ = "1.1"

from json import loads
from os import environ
from hashlib import sha1
from signal import signal, SIGINT
from urllib.request import urlopen
from time import sleep, time, strftime, localtime

# Ascii sequences used to control console terminal display colors

cur_col = {
    'blue' : '\033[94m',
    'green' : '\033[92m',
    'yellow' : '\033[93m',
    'red' : '\033[91m',
    'endc' : '\033[0m'
    }

class currency_layer:

    def __init__(self, key, basket):
        """Build URL we will use to get latest exchange rates

        Args:
          key - Access Key provided when siging up for CUrrencyLayer Account
          basket - Tuple of comma separated currency abbreviations
        """

        base_url = 'http://www.apilayer.net/api/live?'
        self.cl_url = base_url + 'access_key=' + key + '&currencies='

        for c in basket:
            self.cl_url += c + ','       # OK to leave trailing ','

    def validate(self, url):
        """Open URL, read and decode JSON formatted response and confirm query
        was successful. If not, exit the program with some helpful diagnostics.
        """

        try:
            webUrl = urlopen (url)
        except:
            print ("Error: Not able to open: {}".format(url))
            raise SystemExit()

        rate_json = webUrl.read()
        rate_dict = loads(rate_json.decode('utf-8'))
        if rate_dict['success'] == False:
            print('Error: code = {}, type = {}, \ninfo = {}'.format(
                rate_dict['error']['code'],
                rate_dict['error']['type'],
                rate_dict['error']['info']))
            raise SystemExit()
        else:
            return (rate_dict)

    def monitor(self, interval):
        """At specified interval, query exchange data, watch for changes
        and output updated results to system console.
        """
        first_pass = True

        while True:

            # Open URL provided, read data and onfirm quote data is valid

            rates = self.validate(self.cl_url)

            # Calculate hash on quote data structure and use to detect changes

            quote_hash = sha1(str(rates['quotes']).encode("ascii")).hexdigest()

            # 1st time through initialize variables and display current rates

            if first_pass:
                print('{} Begin monitoring'.format(t_stamp()))
                prev_hash = quote_hash
                prev_quote = rates['quotes']
                for exch, cur_rate in prev_quote.items():
                    in_usd = exch[-3:] + '/USD'
                    in_for = 'USD/' + exch[3:]
                    print('{}: {:>8.5f}   {}: {:>9.5f}'.format(
                           in_usd, 1/cur_rate, in_for, cur_rate))
                first_pass = False
                continue

            # Compare hashs to determine if change has occured and, if so, display
            # exchange rates, including % of change, using color coding such that
            # a relative increase in USD strength is green, a decrease is red and
            # no change is output in yellow text.

            if quote_hash != prev_hash:

                print('\n' + t_stamp() + ': Change(s) detected\n')

                for exch, cur_rate in rates['quotes'].items():

                    prev_rate = prev_quote[exch]
                    delta = abs((1 - (cur_rate / prev_rate)) * 100)

                    if cur_rate == prev_rate:
                        color = 'yellow'            # No change
                    elif cur_rate > prev_rate:
                        color = 'green'             # Strong USD
                    else:
                        color = 'red'               # Weaker USD

                    # Display both 'Foreign/USD' and 'USD/Foreign' results

                    in_usd = exch[-3:] + '/USD'
                    in_for = 'USD/' + exch[3:]
                    print('{}{}: {:>8.5f}   {}: {:>9.5f}   {:>5.2f}%'.format(
                           cur_col[color], in_usd, 1/cur_rate,
                           in_for, cur_rate, delta))

                print(cur_col['endc'])
                prev_hash = quote_hash
                prev_quote = rates['quotes']

            else:
                print('{} No change'.format(t_stamp()))

            sleep (interval)              # Take 5 before trying again


def t_stamp():
    """Timestamp utility function to read and format current date and time"""
    _time=strftime('%y-%m-%d %H:%M %Z', localtime(time()))
    return (_time)


def signal_handler(signal, frame):
    """Signal handler for CTRL-C manual termination"""
    print(cur_col['endc'] + '\nProgram terminated manually', '', '\n')
    raise SystemExit()


def main():
    """
    Read API key from from os.environ(), exit if not set. Define basket of
    currencies we wish to monitor. Set monitoring interval, instantiate
    currency_layer() object and invoke monitoring() method with desired
    interval.
    """

    try:
        key = environ['CL_KEY']
    except KeyError:
        print('Error: CL_KEY environment valiable not set')
        print('Command: export CL_KEY=<key value>')
        raise SystemExit()

    basket = ('EUR', 'GBP', 'CNY', 'CAD', 'AUD', 'JPY')

    interval = 60 * 60          # In seconds

    c = currency_layer(key, basket)
    c.monitor(interval)


if __name__ == '__main__':
    """When invoked from shell, call signal() to handle CRTL-C from user
       and invoke main() function
    """
    signal(SIGINT, signal_handler)
    main()
