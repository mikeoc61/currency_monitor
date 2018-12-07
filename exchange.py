#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import loads
from os import environ
from hashlib import sha1
from signal import signal, SIGINT
from urllib.request import urlopen
from time import sleep, time, strftime, localtime

"""Monitor basket of currencies relative to the USD and highlight changes

    > python3 exchange.py

    **Note: Requires CL_KEY to be set in OS shell environment

    See: https://currencylayer.com/documentation

    Public domain by Michael OConnor <gmikeoc@gmail.com>
    Also available under the terms of MIT license
    Copyright (c) 2018 Michael E. O'Connor
"""

__version__ = "1.2"

# Ascii sequences used to control console terminal display colors
cur_col = {
    'blue': '\033[94m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'red': '\033[91m',
    'endc': '\033[0m'
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

    def get_rates(self, url):
        """Open URL, read and decode JSON formatted response and confirm query
        was successful. If not, exit the program with some helpful diagnostics.

        Args:
            - url: fully formed URL we want to open and process results from
        """
        try:
            webUrl = urlopen(url)
        except:
            print("Error: Not able to open: {}".format(url))
            raise SystemExit()

        rate_json = webUrl.read()
        rate_dict = loads(rate_json.decode('utf-8'))

        # Check to see if response if valid and display error info if not
        if rate_dict['success'] is False:
            print('Error: code = {}, type = {}, \ninfo = {}'.format(
                rate_dict['error']['code'],
                rate_dict['error']['type'],
                rate_dict['error']['info']))
            raise SystemExit()
        else:
            return (rate_dict)

    def monitor(self, interval):
        """Query currency exchange data and output results to system console.
        For each query, compare current time with timestamp of last quote and
        use the delta to adjust delay until next query.

        Args:
            - interval: Desired query interval in minutes (typically 60)
        """
        first_pass = True

        while True:
            # Open URL provided, read data and onfirm quote data is valid
            rates = self.get_rates(self.cl_url)

            # Calculate hash on quote data structure and use to detect changes
            quote_hash = sha1(str(rates['quotes']).encode("ascii")).hexdigest()

            # Determine number of minutes between last quote and current time
            quote_time = rates['timestamp']
            quote_delay = (time()-quote_time) / 60

            # 1st time through initialize variables and display current rates
            # then loop back to top of while() loop
            if first_pass:
                print('{} Begin monitoring'.format(t_stamp(time())))
                prev_hash = quote_hash
                prev_quote = rates['quotes']

                print('Last quote updated: {}\n'.format(t_stamp(quote_time)))

                for exch, cur_rate in prev_quote.items():
                    in_usd = exch[-3:] + '/USD'
                    in_for = 'USD/' + exch[3:]
                    print('{}: {:>8.5f}   {}: {:>9.5f}'.format(
                           in_usd, 1/cur_rate, in_for, cur_rate))
                first_pass = False

                continue

            # Compare hashs to determine if change has occured and, if so,
            # display exchange rates, including % of change, using color coding
            # such that a relative increase in USD strength is green,
            # a decrease is red and no change is output in yellow text.
            if quote_hash != prev_hash:
                print('\n {}: Change(s) detected\n'.format(t_stamp(time())))
                print(t_stamp(time()))

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

                print(cur_col['endc'], end='')  # Return cursor color to orig
                prev_hash = quote_hash
                prev_quote = rates['quotes']

            # Use time delta between current time and last quote time to
            # calculate number of minutes to wait until next query. Display
            # progress bar to mark passage of time. If for some reason, delay
            # is greater than interval, use absolute value of time delta
            wait_time = int(abs(interval - quote_delay))
            print('\nNext query in {} minutes '.format(wait_time), end='')
            tbar_sleep(wait_time)


def t_stamp(t):
    """Timestamp utility formats date and time from provided UNIX style
    time value.
    """
    return(strftime('%y-%m-%d %H:%M %Z', localtime(t)))


def tbar_sleep(width):
    """Create a progress bar to mark passage of time in minutes"""
    print('[' + '-'*width, end=']', flush=True)
    for i in range(width+1):
        print('\b', end='', flush=True)
        sleep(0.02)
    for i in range(width):
        sleep(60)
        print(u'\u2588', end='', flush=True)    # Display BLOCK character
    print('\n')


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

    interval = 60        # In minutes

    c = currency_layer(key, basket)
    c.monitor(interval)


if __name__ == '__main__':
    """When invoked from shell, call signal() to handle CRTL-C from user
       and invoke main() function
    """
    signal(SIGINT, signal_handler)
    main()
