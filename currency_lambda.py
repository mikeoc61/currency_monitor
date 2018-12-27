from decimal import Decimal, getcontext
from urllib.request import urlopen
from time import strftime, localtime
from json import loads
import logging
import boto3

'''Currency Exchange Rate program deployed as AWS Lambda function.
   Builds a web page based on user specified URI and Currency Exchange rates.
   Allows user to specify spread percentage and add new currencies from a large
   basket of currencies supported by the Currency Layer web service.

   Program utilizes the following external data sources:

   1) Currency Layer Exchange Rate service for latest exchange rates
   2) AWS DynamoDB database to store historical rates and timestamps
   3) AWS API Gateway to provide a formatted query and response to a client
   4) AWS S3 to hold CSS stylesheet

   Program utilizes the following technologies:

   1) Python 3 programming language for logic and to generate HTML
   2) HTML, CSS and Javascript to format the resulting web page
   3) AWS Boto3 and DynamodDB as a persistent data store
   4) AWS Lambda and API Gateway to instantiate and access the function

   Author: Michael O'Connor

   Last update: 12/26/18
'''

logger = logging.getLogger()
logger.setLevel(logging.ERROR)          # Set to INFO for more detail

class CurrencyLayer:

    def __init__(self, base, mode, key, basket):

        """Build URL we will use to query latest exchange rates from
           Currency Layer Web Service

        Args:
          base - base portion of URL
          mode - 'live' or 'list'
          key - Access Key provided when siging up for CurrencyLayer Account
          basket - Comma separated currency abbreviations
        """

        if mode == 'list':
            self.cl_url = base + 'list?' + 'access_key=' + key
        elif mode == 'live':
            self.cl_url = base + 'live?' + 'access_key=' \
                          + key + '&currencies=' + basket

        self.basket = basket
        self.rate_dict = {}

        # Working with Decimal numbers so set precision to prevent strange
        # floating point approximations

        getcontext().prec = 6


    def cl_validate(self):
        """Open supplied URL. If initial open is successful, read contents
           to determine if API call was successful. If successful, rate_dict
           will contain dictionary data structure containing rate quotes. If
           unsuccessful, log errors to CloudWatch and raise exception.
        """
        try:
            webUrl = urlopen (self.cl_url)
        except:
            logger.error('In cl_validate()')
            logger.error('Unable to open: {}'.format(self.cl_url))
            raise Exception
        else:
            rate_data = webUrl.read()
            self.rate_dict = loads(rate_data.decode('utf-8'))
            if self.rate_dict['success'] is False:
                logger.error('In cl_validate()')
                logger.error('Error= {}'.format(self.rate_dict['error']['info']))
                raise Exception
            else:
                logger.info('SUCCESS: In cl_validate(): response= {}'.\
                             format(self.rate_dict))


    def get_rates(self, spread):
        '''Loop through exchange rate raw data and returned formatted HTML.
           Spread is used to provide a percentage delta corresponding to
           costs associated with buying & selling foreign currencies
        '''

        from currency_config import USD_FIRST, DYNAMO_DB_TABLE

        spread = Decimal(spread)

        cl_ts = self.rate_dict['timestamp']
        rate_html = "<h2>As of " + t_stamp(cl_ts) + "</h2>"

        logger.info("Currency Layer Last update: " + t_stamp(cl_ts))

        # Create Form to enable manipulation of Spread within a range
        # This approach also provides input validation

        rate_html += "<div id='inputs' class='myForm' text-align: center>"
        rate_html += "<form id='spread_form' action='#' "
        rate_html +=   "onsubmit=\"changeSpread('text');return false\">"
        rate_html += "<label for='spread_label'>Spread:  </label>"
        rate_html += "<input id='spread_input' type='number' min='.10' \
                             max='2.0' step='.05' size='4' maxlength='4' \
                             value='{:3.2f}'>".format(spread)
        rate_html += "<input type='submit' class='button'>"
        rate_html += "</form></div>"

        spread = spread / 100               # convert to percentage

        # Establish a connection to Persistent AWS Database. We will assume
        # that DynamoDB database has been created and table initialized with
        # Abbr as the HASH Key.
        #
        # Database will look like this:
        #
        #   +---------+-----------+-----------+
        #   | Abbr    | Rate      | Tstamp    |
        #   |{String} | {Decimal} | {Decimal} |
        #   +---------+-----------+------------+
        #   |   AED   |  3.67305 | 1545828846 |
        #   |   AFN   |  74.9502 | 1545828846 |
        #   |   ALL   |   107.62 | 1545828846 |
        #   |   AMD   |   484.53 | 1545828846 |
        #   |   ANG   |  1.77575 | 1545828846 |
        #   ...

        table = db_connect(DYNAMO_DB_TABLE)

        # Itterate over each exchange rate and display results in HTML
        # along with percentage spread and change percentage. We use a
        # persistent database to compare saved values with current quotes

        for exch, cur_rate in self.rate_dict['quotes'].items():

            abbr = exch[-3:]

            # Query Database to determine saved quote value and timestamp

            response = dynamo_query(table, abbr)
            old = (response['Rate'])
            tstamp = (response['Tstamp'])

            # Since we are doing Decimal arithmetic, convert cur_rate to
            # Decimal if necessary

            if not isinstance(cur_rate, Decimal):
                cur_rate = Decimal(str(cur_rate))

            logger.info('For {}: Old Quote= {} New Quote= {}'.\
                         format(abbr, old, cur_rate))

            # Format Exchange label and value so we can display with both
            # USD in the numerator and denominator

            in_usd = exch[-3:] + '/USD'
            in_for = 'USD/' + exch[3:]
            usd_spread = (1/cur_rate)*(1+spread)
            for_spread = cur_rate*(1/(1+spread))

            # Display certain currencies in per USD first as determined
            # by currency abbreviation inclusion in usd_first data set

            if exch[3:] in USD_FIRST:
                msg = "{}: {:>9.4f} ({:>9.4f})  {}: {:>7.4f} ({:>6.4f})".\
                        format(in_usd, 1/cur_rate, usd_spread,
                               in_for, cur_rate, for_spread)
            else:
                msg = "{}: {:>9.4f} ({:>9.4f})  {}: {:>7.4f} ({:>6.4f})".\
                        format(in_for, cur_rate, for_spread,
                               in_usd, 1/cur_rate, usd_spread)

            # Calculate percentage change and use to determine display color.
            # If currency was recently added to basket then old rate may
            # still be '0.0' in the database. If so, set old rate equal to
            # current rate to prevent divide by zero exception and
            # convert to Decimal type to maintain precision.

            old_rate = cur_rate if (old == '0.0') else Decimal(old)

            change_pct = (1 - (cur_rate / old_rate)) * 100

            # Rates are quoted relative to USD. If change color is red
            # then USD has weakened relative to foreign currency. If green then
            # USD has strengthened. If change is less than 0.1%, don't color.
            # Also, add hover to text showing time basis for percentage change.

            if change_pct >= 0.1:
                color = 'red'
            elif change_pct <= -0.1:
                color = 'green'
            else:
                color = 'white'

            rate_html += "<pre>{} <span title='USD % Change since: {}'\
                          style='color:{}'>{:>3.2f}%".\
                          format(msg, t_stamp(tstamp), color, abs(change_pct))
            rate_html += "</span></pre>"

            # If more than 24 hours have passed between the most recent
            # quote timestamp and time quote was last saved to the database,
            # update both the quote and timestamp in the database.

            time_delta = (Decimal(cl_ts - Decimal(tstamp)))
            logger.info("{} hours since last database update".\
                         format(time_delta/(60*60)))

            if time_delta > (24*60*60):
                dynamo_update(table, abbr, cur_rate, cl_ts)
            else:
                logger.info("Less than 24 hours since last quote update")

        return rate_html


    def get_list(self, cl_abbrs):
        '''Loop through basket of currency abbreviations and return with HTML
           list of corresponding definitions. If specific exchange abbreviation
           is specified multiple times, don't repeat in list.
        '''

        rate_html = "<h2>Abbreviations</h2>"

        basket_list = self.basket.split(',')

        unique = []                             # Eliminate redundancy

        for abbr in basket_list:
            if abbr not in unique:
                unique.append(abbr)
                if abbr in cl_abbrs:
                    rate_html += "<p>{} = {}</p>".format(abbr, cl_abbrs[abbr])
                else:
                    rate_html += "<p>{} = {}</p>".format(abbr, "Unknown")

        return rate_html


    def build_select(self, cl_abbrs):
        '''Loop through basket of currency abbreviations and return with an HTML
           form a list of currency options to be added to basket.
        '''

        basket_list = self.basket.split(',')

        select_html = "<div id='cur_select' class='myForm'>"
        select_html += "<form id='currency_form' action='#' "
        select_html += "onsubmit=\"addCurrency('text');return false\">"
        select_html += "<label for='select_label'></label>"
        select_html += "<select id='currency_abbr' type='text' name='abbrSelect'>"
        select_html += "<option disabled selected value>  Add Currency </option>"

        for abbr in cl_abbrs:
            if abbr not in basket_list:
                select_html += "<option value='{}'>{}</option>".\
                                format(abbr, cl_abbrs[abbr])

        select_html += "</select>"
        select_html += "<input type='submit' class='button' onclick = '...'>"
        select_html += "</form></div>"

        return select_html


def db_connect(db_table):
    '''Confirm access to DynamoDB and return table object'''

    try:
        dynamo_db = boto3.resource('dynamodb')
        table = dynamo_db.Table(db_table)
    except:
        logger.error("In db_connect(): Could not connect to DynamoDB.")
    else:
        logger.info("SUCCESS: {} Table created: {}".\
                        format(db_table, table.creation_date_time))
        return table


def dynamo_update(table, abbr, rate, tstamp):
    '''Update DynamoDB values with provided Abbr:Rate (key:value) pair.
       Convert rates to type Decimal before updating by first converting
       rate value to type str.
    '''
    try:
        response = table.update_item(
            Key={'Abbr': abbr},
            UpdateExpression='SET Rate = :r, Tstamp = :t',
            ExpressionAttributeValues={
                ':r': Decimal(str(rate)),
                ':t': Decimal(str(tstamp))
                }
            )
    except:
        logger.error("In dynamo_update()")
        logger.error("Update_item {} response = {}".format(abbr, response))
    else:
        logger.info("SUCCESS: Updated Key= {}".format(abbr))


def dynamo_query(table, abbr):
    '''For a given table value, query database and return result'''

    try:
        response = table.get_item(
            Key={
                'Abbr': str(abbr)
                }
            )
    except:
        logger.error("In dynamo_query()")
        logger.error("get_item {} response = {}".format(abbr, response))
    else:
        logger.info("SUCCESS: Query Key= {}".format(abbr))

    return response['Item']


def t_stamp(t):
    '''Utility function to format date and time from passed UNIX time'''

    #return(strftime('%y-%m-%d %H:%M %Z', localtime(t)))
    return(strftime('%d %b %Y %H:%M %Z', localtime(t)))


def build_resp(event):
    '''Format the Head, Body and Script sections of the DOM including any CSS
       formatting to apply to the remainder of the document. Break into multiple
       lines for improved readability
    '''
    # Import variable definitions associated with CurrencyLayer service

    from currency_config import CL_KEY, BASE, MODE, basket, api_spread

    from currency_config import MAIN_CSS_HREF, CURR_ABBRS

    # If options passed as URL parameters, replace default values accordingly

    try:
        options = event['params']['querystring']
    except:
        options = False
    else:
        for key, val in options.items():
            if key.lower() == "currencies":
                if val:
                     basket = val
            if key.lower() == "spread":
                if val:
                    api_spread = Decimal(val)

    logger.info('Basket: {} Spread: {}'.format(basket, api_spread))

    # Instantiate currency_layer() object and confirm we can access Currency
    # Layer Web Service

    try:
        cl_feed = CurrencyLayer(BASE, MODE, CL_KEY, basket)
        cl_feed.cl_validate()
    except:
        rates = "<h2>Error: unable to instantiate currency_layer()</h2>"
        rates += "<h3>Please see Lambda CloudWatch Logs</h3>"
    else:
        rates = cl_feed.get_rates(api_spread)

    html_head = "<!DOCTYPE html>"
    html_head += "<head>"
    html_head += "<title>Display Currency Exchange Rates</title>"
    html_head += "<meta charset='utf-8'>"
    html_head += "<meta name='viewport' content='width=device-width'>"

    # Stop annoying favicon.ico download attempts / failure

    html_head += "<link rel='icon' href='data:,'>"

    # Import CSS style config from location defined in config file

    html_head += "<link rel='stylesheet' type='text/css' media='screen'"
    html_head += "href={}>".format(MAIN_CSS_HREF)
    html_head += "</head>"

    html_body = "<body>"
    html_body += "<h1>Currency Exchange Rates</h1>"

    # Output list of currency exchange rates

    html_body += "<div class='center'>"
    html_body +=    "<div>"
    html_body +=        rates
    html_body +=    "</div>"

    # Add a new currency to basket

    html_body +=    "<div>"
    html_body +=        cl_feed.build_select(CURR_ABBRS)
    html_body +=    "</div>"

    # Output list of currency definitions

    html_body +=    "<div>"
    html_body +=        cl_feed.get_list(CURR_ABBRS)
    html_body +=    "</div>"

    # Provide button to reset currency basket and spread to default

    html_body +=    "<div>"
    html_body +=        "<button class='button' onclick='resetDefaults()'>"
    html_body +=        "Reset Currencies and Spread"
    html_body +=        "</button>"
    html_body +=    "</div>"

    html_body += "</div>"
    html_body += "<br><br>"
    html_body += "</body>"

    # Note the following section should ideally be moved to a separate file on
    # S3 similar to what was done with the CSS stylesheeet.

    html_js = "<script type='text/javascript'>"
    html_js += "'use strict';"

    html_js += "var _base = getURIbase() + '\u003Fcurrencies={}';".format(basket)

    html_js += "function getURIbase() {"
    html_js +=    "var getUrl = window.location;"
    html_js +=    "var baseUrl = getUrl.origin + getUrl.pathname;"
    html_js +=    "return baseUrl"
    html_js +=    "}"

    html_js += "function resetDefaults() {"
    html_js +=    "location.replace(getURIbase());"
    html_js +=    "return false;"
    html_js +=    "}"

    html_js += "function changeSpread(action) {"
    html_js +=    "var _spr = document.getElementById('spread_input').value;"
    html_js +=    "var _url = _base + '\u0026spread=' + _spr;"
    html_js +=    "location.replace(`${_url}`);"
    html_js +=    "}"

    html_js += "function addCurrency(action) {"
    html_js +=    "var _spr = document.getElementById('spread_input').value;"
    html_js +=    "var _abbr = document.getElementById('currency_abbr').value;"
    html_js +=    "if (_abbr) {"
    html_js +=      "var _url = _base + ',' + _abbr + '\u0026spread=' + _spr;"
    html_js +=      "location.replace(`${_url}`);"
    html_js +=    "} else {"
    html_js +=      "alert('Please select a currency');"
    html_js +=      "}"
    html_js +=    "}"

    html_js += "</script>"
    html_tail = '</html>'

    resp = html_head + html_body + html_js + html_tail

    return resp


def lambda_handler(event, context):
    '''AWS Lambda Event handler'''

    print("In lambda handler")

    logger.info('Event: {}'.format(event))
    logger.info('Context: {}'.format(context))

    return build_resp(event)
