from decimal import Decimal, getcontext
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from time import strftime, localtime
from json import loads
import logging
import boto3

'''Currency Exchange Rate program deployed as AWS Lambda function. Returns
   a web page based on URL options and an external Currency Exchange service.
   User can specify spread percentage and add new currencies from a large
   basket of currency options supported by the Currency Layer web service.
'''

################################################################################
#
# Program utilizes the following external data sources:
#
# 1) Currency Layer Exchange Rate service for latest exchange rates
# 2) AWS DynamoDB database to store historical rates and timestamps
# 3) AWS API Gateway to provide a formatted query and response to a client
# 4) AWS S3 to store CSS stylesheet, HTML header, footer, nav bar, and Javascript
#
# Program utilizes the following technologies:
#
# 1) Python 3 programming language for logic and to generate HTML
# 2) HTML, CSS, Bootstrap and Javascript to format the resulting web page
# 3) AWS Boto3 and DynamodDB as a persistent data store
# 4) AWS Lambda and API Gateway to instantiate and access the function
#
# Author: Michael O'Connor
#
# Last update: 02/01/2019
#
################################################################################

# Set logging level to INFO for more detail, ERROR for less
# See CloudWatch service for logging detail

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        self.cl_ts = 12345678

        # Working with Decimal numbers so set precision to prevent strange
        # floating point approximations

        getcontext().prec = 6


    def cl_validate(self):
        """Open supplied URL. If initial open is successful, read contents
           to determine if API call was successful. If successful, rate_dict
           will contain dictionary data structure containing rate quotes and
           quote timestamp. If unsuccessful, log errors to CloudWatch and
           raise exception.
        """

        try:
            webUrl = urlopen (self.cl_url)
        except HTTPError as e:
            logger.error('In cl_validate()')
            logger.error('Unable to open: %s', self.cl_url)
            logger.error('Error code: %s', e.code)
            raise Exception
        except URLError as e:
            logger.error('Reason: %s', e.reason)
            raise Exception
        else:
            rate_data = webUrl.read()
            self.rate_dict = loads(rate_data.decode('utf-8'))
            if self.rate_dict['success'] is False:
                logger.error('In cl_validate()')
                logger.error('Error= %s', self.rate_dict['error']['info'])
                raise Exception
            else:
                self.cl_ts = self.rate_dict['timestamp']
                logger.info('SUCCESS: API response= %s', self.rate_dict)


    def get_rates(self, spread):
        '''Loop through exchange rate raw data and returned formatted HTML.
           Spread is used to provide a percentage delta corresponding to
           costs associated with buying & selling foreign currencies
        '''

        from currency_config import USD_FIRST, DYNAMO_DB_TABLE

        spread = Decimal(spread)

        # Create Form to enable manipulation of Spread within a range
        # This approach also provides input validation

        rate_html = "<div id='inputs' class='myForm' text-align: center>"
        rate_html += "<form id='spread_form' action='#' "
        rate_html +=   "onsubmit=\"changeSpread('text');return false\">"
        rate_html += "<label for='spread_label'>Spread:  </label>"
        rate_html += "<input id='spread_input' type='number' min='.10' "
        rate_html +=  "max='2.0' step='.05' size='4' maxlength='4' "
        rate_html +=  "value='{:3.2f}'>".format(spread)
        rate_html += "<input type='submit' class='mybutton'>"
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

        rate_html += "<div class='quotes'>"

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

            logger.info('For %s: Old= %s New= %s', abbr, old, cur_rate)

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
                color = '#f44141'           # Bright Red
            elif change_pct <= -0.1:
                color = '#62f442'           # Bright Green
            else:
                color = 'white'

            rate_html += "<pre>{}<span ".format(msg)
            rate_html += "title='Change since: {}' ".format(t_stamp(tstamp))
            rate_html += "style='color:{}'> {:>3.2f}%".format(color, abs(change_pct))
            rate_html += "</span></pre>"

            # If more than 24 hours have passed between the most recent
            # quote timestamp and time quote was last saved to the database,
            # update both the quote and timestamp in the database.

            time_delta = (Decimal(self.cl_ts - Decimal(tstamp)))
            logger.info("%s hours since last DB update", time_delta/(60*60))

            if time_delta > (24*60*60):
                logger.info("Updating table: %s for %s", table, abbr)
                dynamo_update(table, abbr, cur_rate, self.cl_ts)

        rate_html += "</div>"       # class='quotes'

        return rate_html


    def get_list(self, cl_abbrs):
        '''Loop through basket of currency abbreviations and return list of
           corresponding definitions.
        '''

        # If specific exchange abbreviation is specified multiple times, don't
        # repeat in list. Note this routine uses Bootstrap classes to display
        # multiple columns on wider displays.

        rate_html = "<div id='abbreviations' class='collapse'>"
        rate_html += "<div class='container-fluid'>"
        rate_html +=  "<div class='abbr row'>"

        basket_list = self.basket.split(',')

        unique = []                             # Eliminate redundancy

        for abbr in basket_list:
            if abbr not in unique:
                unique.append(abbr)
                rate_html += "<section class='col-sm-6'>"
                desc = cl_abbrs[abbr] if (abbr in cl_abbrs) else "Unknown"
                rate_html += "<p>{} = {}</p>".format(abbr, desc)
                rate_html += "</section>"

        rate_html += "</div></div></div>"     # collapse, container, row

        return rate_html


    def build_select(self, cl_abbrs):
        '''Loop through basket of currency abbreviations and return with an HTML
           form containing a list of currencies which can be added to basket.
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
        select_html += "<input type='submit' class='mybutton'>"
        select_html += "</form></div>"

        return select_html


def db_connect(db_table):
    '''Confirm access to specified DynamoDB table and return table object'''

    try:
        dynamo_db = boto3.resource('dynamodb')
        table = dynamo_db.Table(db_table)
    except:
        logger.error("In db_connect(): Could not connect to DynamoDB.")
    else:
        logger.info("Table: %s created: %s", db_table, table.creation_date_time)
        return table


def dynamo_update(table, abbr, rate, tstamp):
    '''Update DynamoDB table with specified rate and timestamp using abbr key'''

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
        logger.error("Update_item: %s response = %s", abbr, response)
    else:
        logger.info("Updated Key: %s", abbr)


def dynamo_query(table, abbr):
    '''For a given table key, query database and return associated values'''

    try:
        response = table.get_item(
            Key={
                'Abbr': str(abbr)
                }
            )
    except:
        logger.error("In dynamo_query()")
        logger.error("get_item %s response = %s", abbr, response)

    return response['Item']


def t_stamp(t):
    '''Utility function to format date and time from passed UNIX time'''

    return(strftime('%b %d, %Y, %H:%M %Z', localtime(t)))


def fetch_html(url):
    '''Given a Web URL, read and remove leading whitespace, return as string'''

    response = []
    with urlopen(url) as html:
        for line in html:
            line = line.decode("utf-8")
            response.append(line.lstrip())

    return ''.join(response)


def build_resp(event):
    '''Format the Head, Body and Script sections of the DOM including any CSS'''

    # Import variable definitions associated with CurrencyLayer service

    from currency_config import CL_KEY, BASE, MODE, basket, api_spread
    from currency_config import CURR_ABBRS, CURRENCY_HEAD_HTML, CURRENCY_NAV_BAR
    from currency_config import CURRENCY_FOOTER, CURRENCY_JS
    from currency_config import CURRENCY_CSS, CURRENCY_ICO

    # If options passed as URL parameters, use to replace default values

    try:
        options = event['params']['querystring']
        if not options:
            logger.info('No optional parameters found, using defaults')
    except:
        logger.critical('Error parsing event detail')
    else:
        for key, val in options.items():
            if key.lower() == "currencies":
                if val:
                     basket = val
            if key.lower() == "spread":
                if val:
                    api_spread = Decimal(val)

    logger.info('Basket: %s Spread: %s', basket, api_spread)

    try:
        logger.info('Client IP address is: %s', event['context']['source-ip'])
    except:
        logger.error('Unable to parse client IP address')

    # Load HTML Header as defined in config file

    html_head = fetch_html(CURRENCY_HEAD_HTML)

    # Load CSS Stylesheet & Favicon as defined in config file

    CSS_LINK = "rel='stylesheet' type='text/css' href='{}'".format(CURRENCY_CSS)
    ICO_LINK = "rel='icon' type='image/x-icon' href='{}'".format(CURRENCY_ICO)

    html_head += "<link " + CSS_LINK + ">"
    html_head += "<link " + ICO_LINK + ">"

    # Place a Navigation bar at top of page

    html_body = fetch_html(CURRENCY_NAV_BAR)

    # Build main HTML body of program

    html_body += "<main class='mycontainer'>"
    html_body +=  "<section class='center' style='margin-top: 70px'>"

    # Instantiate currency_layer() object and confirm access to Currency Service
    # If successful, cl_ts will be updated with latest quote timestamp. Call
    # get_rates() method called to convert raw quote date to formatted HTML

    # Note: Javascript is used to replace the UTC time with local time so
    # we use 'title=' option in <H2> tag to show UTC time when user hovers

    try:
        cl_feed = CurrencyLayer(BASE, MODE, CL_KEY, basket)
        cl_feed.cl_validate()
    except:
        html_body += "<h2>Error when attempting to access Rate Service</h2>"
        html_body += "<h3>Please see CloudWatch Logs for detail</h3>"
    else:
        html_body += "<h2 id='t_stamp' title='" + t_stamp(cl_feed.cl_ts) + "'>"
        html_body += "As of " + t_stamp(cl_feed.cl_ts) + "</h2>"

        html_body += cl_feed.get_rates(api_spread) + "\n"

    # Provide button to add new currencies to basket

    html_body += cl_feed.build_select(CURR_ABBRS) + "\n"

    # Display list of abbreviation definitions for currency basket

    html_body += "<div class='text-center'>"
    html_body +=  "<button class='abbr-btn' data-toggle='collapse' "
    html_body +=    "data-target='#abbreviations' title='Toggle Definitions'>"
    html_body +=    "Currency Abbreviations"
    html_body +=  "</button>"
    html_body += "</div>"

    html_body += cl_feed.get_list(CURR_ABBRS)

    # Provide button to reset currency basket and spread % to defaults

    html_body += "<button class='reset mybutton' onclick='resetDefaults()'>"
    html_body +=    "Reset Currencies and Spread"
    html_body += "</button>"

    html_body +=  "</section>"       # class = 'center'
    html_body += "</main>"       # class = 'mycontainer'

    # Add a footer section to end of page

    html_body += "\n" + fetch_html(CURRENCY_FOOTER)

    # Javascript used to rebuild Lambda URI, handle user events and convert
    # UTC Epoch timestamp to user's local timezone. Initialize key variables
    # used by functions defined in external .js file as defined by CURRENCY_JS

    html_js  = "<script>"
    html_js +=   "const BASKET = '" + basket + "';"
    html_js +=   "const CL_TS = '" + str(cl_feed.cl_ts) + "';"
    html_js += "</script>\n"

    html_js += "<script src='" + CURRENCY_JS + "'></script>\n"

    # Load jQuery scripts from CDN (necessary for Bootstrap's JavaScript plugins)

    html_js += "<script src='https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js'></script>\n"

    # Include all compiled Bootstrap plugins using external CDN

    html_js += "<script src='https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js' crossorigin='anonymous'></script>\n"

    # Assemble DOM and return to caller, either main() or lambda_handler()
    # main() will then output code to stdout and lambda_handler() will return
    # output HTML/CSS/JS to trigger function, typically API Gateway -> browser

    resp = "<!DOCTYPE html>\n" \
            + "<html lang='en'>\n" \
            + "<head>" + html_head + "</head>\n" \
            + "<body>" + html_body + "\n" \
            + html_js + "</body>\n" \
            + "</html>"

    return resp


def lambda_handler(event, context):
    '''AWS Lambda Event handler'''

    logger.info('Event: %s', event)
    logger.info('Context: %s', context)

    return build_resp(event)
