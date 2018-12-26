#!/usr/bin/python3
# -*- coding: utf-8 -*-

from urllib.request import urlopen
from decimal import Decimal, getcontext
from json import loads
import boto3

""" Python utility to initialize AWS DynamoDB table with Currency Abbreviations,
    Currency Exchange Rates and timestamp of latest update from Currency Layer.

    This program should be run once prior to running any version of the
    currency exchange monitoring program which relies on DynamoDB for
    persistent storage.

    Requires that Table be previously created with basic schema defined e.g:

    dynamo_db_table {
             Abbr: String,
             Rate: Decimal,
             Tstamp: Decimal
             }

    Author: Michael O'Connor

    Last update: 12/26/18
"""

class CurrencyLayer:
    """[summary]

    """

    def __init__(self, base, mode, key):
        """Build URL we will use to query latest exchange rates from
           Currency Layer Web Service

        Args:
          base - base portion of URL
          mode - 'live' or 'list'
          key - Access Key provided when siging up for CurrencyLayer Account
        """

        self.cl_url = base + mode + '?access_key=' + key
        self.rate_dict = {}

        # Working with Decimal numbers so set precision to prevent strange
        # floating point approximations

        getcontext().prec = 6


    def cl_validate(self):
        """Open URL constructed in init(). If initial open is successful, read
           contents to determine if API call was successful. If read is
           successful, self.rate_dict will contain dictionary data structure
           containing current rate quotes. Successful call will return:

            {
                "success":true,
                "terms":"https://currencylayer.com/terms",
                "privacy":"https://currencylayer.com/privacy",
                "timestamp":1545855246,
                "source":"USD",
                "quotes":{
                    "USDAED":3.67295,
                    "USDAFN":74.3977,
                    "USDALL":107.949718
                    ...
                    }
                }
        """

        try:
            web_url = urlopen(self.cl_url)
        except:
            print('Sorry, unable to open: {}'.format(self.cl_url))
            raise Exception
        else:
            rate_data = web_url.read()
            self.rate_dict = loads(rate_data.decode('utf-8'))
            if self.rate_dict['success'] is False:
                print('Error= {}'.format(self.rate_dict['error']['info']))
                raise Exception
            else:
                print('SUCCESS: In cl_validate()')


    def get_rates(self):
        """Simply return the data structure created in cl_validate()"""

        return self.rate_dict


def db_batch_update(table, data):
    """DynamoDB Batch update function which takes DynamoDB table and a
       dictionary data structure in the format returned by Currency
       Layer Web Service and updates an existing table with Currency
       Abbreviation, Rate and Timestamp for each supported currency.
    """

    t_stamp = data['timestamp']

    with table.batch_writer() as batch:
        for exch, cur_rate in data['quotes'].items():
            abbr = exch[-3:]
            print('Updating: {}...'.format(abbr))
            batch.put_item(
                Item={
                    'Abbr': str(abbr),
                    'Rate': Decimal(str(cur_rate)),
                    'Tstamp': Decimal(t_stamp)
                }
            )


def main():
    """Query Currency Layer service for complete list of available Currencies
       along with current exchange rate relative to USD and update timestamp.
       Use resulting data dictionary to populate the DynamoDB table with initial
       values for Abbr, Rate and Timestamp.
    """

    from currency_config import BASE, MODE, CL_KEY
    from currency_config import DYNAMO_DB_TABLE

    try:
        cl_feed = CurrencyLayer(BASE, MODE, CL_KEY)
        cl_feed.cl_validate()
    except:
        print('Unable to instantiate or validate currency_layer object')
        raise Exception
    else:
        cl_rates = cl_feed.get_rates()
        print('Call to Currency Layer Service was Successful')

    print('Accessing DynamoDB Table...')
    _db = boto3.resource('dynamodb')
    cl_table = _db.Table(DYNAMO_DB_TABLE)
    print("Table {} created: {}".format(DYNAMO_DB_TABLE, cl_table.creation_date_time))

    print('Starting Batch update of DynamoDB Table...')
    db_batch_update(cl_table, cl_rates)

    print('All done!')

if __name__ == "__main__":
    main()
