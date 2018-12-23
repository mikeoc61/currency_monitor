from json import loads
from urllib.request import urlopen
from time import time, strftime, localtime
from signal import signal, SIGINT
from decimal import Decimal, getcontext
import pymysql
import logging
import boto3

'''Currency Exchange Rate program intended to be deployed as AWS Lambda function
   Builds a web page based on user specific URI and Currency Exchange rates.
   Allows user to specific spread percentage and add from a large basket of
   currencies supported by the Currency Layer service.

   Program utilizes four external data sources:

   1) Currency Layer Exchange Rate service for latest exchange rates
   2) AWS RDS MySQL or DynamoDB database to store old rates for change determination
   3) AWS API Gateway to provide a formatted query and response to a browser
   4) AWS S3 to hold CSS stylesheet

   Program utilizes the following technologies:

   1) Python 3 programming language for logic and to generate HTML
   2) HTML, CSS and Javascript to format the resulting web page
   3) Mypysql Python module and AWS RDS or DynamoDB to save quote data
   4) AWS Lambda and API Gateway to instantiate the function

   Author: Michael O'Connor

   Last update: 12/23/18
'''

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class currency_layer:

    def __init__(self, base, mode, key, basket):

        """Build URL we will use to get latest exchange rates

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

        # Working with Decimal numbers so set precision to prevent strange
        # floating point approximations

        getcontext().prec = 6


    def cl_validate(self, url):
        """Open supplied URL. If initial open is successful, read contents
           to determine if API call was successful. If so, return
           dictionary object with rates, else return error string
        """
        try:
            webUrl = urlopen (url)
        except:
            err_msg = 'In cl_validate(): url() open failed'
            return err_msg
        else:
            rate_data = webUrl.read()
            rate_dict = loads(rate_data.decode('utf-8'))
            if rate_dict['success'] is False:
                err_msg = 'CL Error: {}'.format(rate_dict['error']['info'])
                return err_msg
            else:
                return rate_dict


    def get_rates(self, spread):
        '''Loop through exchange rate raw data and returned formatted HTML
           Spread is used to provide a percentage delta corresponding to
           costs associated with buying & selling foreign currencies

           Note this routine can use either AWS RDS MySQL or AWS DynamoDB
        '''

        from currency_config import usd_first, db_table, dynamo_db_table

        rates = self.cl_validate(self.cl_url)
        spread = Decimal(spread)

        if isinstance(rates, str):                  # cl_validate returned Error
            rate_html = "<p>" + rates + "</p>"
        elif isinstance(rates, dict):               # cl_validate returned data
            ts = t_stamp(rates['timestamp'])
            rate_html = "<h2>As of " + ts + "</h2>"

            logger.info("Currency Layer Last update: " + ts)

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
            rate_html += "<br>"

            # Establish a connection to Persistent AWS Database
            # Assume database has been created and tables initialized
            #
            # Database will look like this:
            #
            #   +------+----------+
            #   | Abbr | Rate     |
            #   +------+----------+
            #   | AED  |  3.67305 |
            #   | AFN  |  74.9502 |
            #   | ALL  |   107.62 |
            #   | AMD  |   484.53 |
            #   | ANG  |  1.77575 |
            #   ...

            table = db_connect('DynamoDB')

            #db_conn = db_connect('sql')

            # Itterate over each current rate and display results in HTML
            # along with percentage spread and change percentage

            for exch, cur_rate in rates['quotes'].items():

                # Note DynamoDB nominally returns an object of type Decimal

                old = dynamo_query(table, exch[-3:])

                #old = sql_query(db_conn, db_table, exch[-3:])

                # If currency recently added to basket then old rate will still
                # be '0.0' string instead of a Decimal value. If so, set old to
                # new value to prevent devide by zero exception and convert to
                # Decimal type to maintain precision.

                old_rate = Decimal(cur_rate) if (old[1] == '0.0') else Decimal(old[1])

                # Convert current rate float to fixed point decimal value by
                # first converting to string. This is required to maintain
                # desired precision.

                cur_rate = Decimal(str(cur_rate))

                logger.info('For {}: Old= {} New= {}'.format(exch, old[1], cur_rate))

                in_usd = exch[-3:] + '/USD'
                in_for = 'USD/' + exch[3:]
                usd_spread = (1/cur_rate)*(1+spread)
                for_spread = cur_rate*(1/(1+spread))

                # Depending on display preference, format certain currencies
                # with per USD version first, otherwise Foreign first.

                if exch[3:] in usd_first:
                    msg = "{}: {:>9.4f} ({:>9.4f})  {}: {:>7.4f} ({:>6.4f})".\
                            format(in_usd, 1/cur_rate, usd_spread,
                                   in_for, cur_rate, for_spread)
                else:
                    msg = "{}: {:>9.4f} ({:>9.4f})  {}: {:>7.4f} ({:>6.4f})".\
                            format(in_for, cur_rate, for_spread,
                                   in_usd, 1/cur_rate, usd_spread)

                # Calculate Change and use to determine color output

                change = (1 - (cur_rate / old_rate)) * 100

                #logger.info('Change percentage = {}'.format(change))

                if change >= 0.25:
                    color = 'green'
                elif change <= -0.25:
                    color = 'red'
                else:
                    color = 'white'

                rate_html += "<pre> {} <span style='color:{}'>{:>3.1f}%".\
                              format(msg, color, abs(change))
                rate_html += "</span></pre>"

            # Done with loop so bulk update database table with latest rates

            dynamo_update(table, rates['quotes'])

            #sql_update(db_conn, db_table, rates['quotes'])

        else:
            rate_html = "<p>Error: Expected string or dict in get_rates()<p>"
            logger.error("In get_rates(): Expected string or dict")

        # Close previously opened DB connection if using AWS MySQL Database

        #db_conn.close()

        return rate_html


def get_list(basket):
    '''Loop through basket of currency abbreviations and return with definitions
       Implemented as a function vs. class as not dependent on web service.
    '''

    from currency_config import curr_abbrs  # Import abbreviations

    rate_html = "<h2>Abbreviations</h2>"

    basket_list = basket.split(',')

    unique = []                             # Eliminate redundant currencies

    for abbr in basket_list:
        if abbr not in unique:
            unique.append(abbr)
            if abbr in curr_abbrs:
                rate_html += "<p>{} = {}</p>".format(abbr, curr_abbrs[abbr])
            else:
                rate_html += "<p>{} = {}</p>".format(abbr, "Unknown")

    return rate_html


def build_select(basket):
    '''Loop through basket of currency abbreviations and return with a list of
       selections to be added to basket.
    '''

    from currency_config import curr_abbrs

    basket_list = basket.split(',')

    select_html = "<div id='cur_select' class='myForm'>"
    select_html += "<form id='currency_form' action='#' "
    select_html += "onsubmit=\"addCurrency('text');return false\">"

    select_html += "<label for='select_label'></label>"
    select_html += "<select id='currency_abbr' type='text' name='abbrSelect'>"
    select_html += "<option disabled selected value>  Add Currency </option>"

    for abbr in curr_abbrs:
        if abbr not in basket_list:
            select_html += "<option value='{}'>{}</option>".\
                            format(abbr, curr_abbrs[abbr])

    select_html += "</select>"
    select_html += "<input type='submit' class='button' onclick = '...'>"
    select_html += "</form></div>"

    return select_html


def t_stamp(t):
    """Utility function to format date and time from passed UNIX time"""

    return(strftime('%y-%m-%d %H:%M %Z', localtime(t)))


def build_resp(event):
    '''Format the Head section of the DOM including any CSS formatting to
       apply to the remainder of the document. Break into multiple lines for
       improved readability
    '''
    # Import variables definitions associated with CurrencyLayer service

    from currency_config import cl_key, base, mode, basket, api_spread

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

    # Instantiate currency_layer() object and initialize valiables

    try:
        c = currency_layer(base, mode, cl_key, basket)
    except:
        rates = "<p>Error: unable to instantiate currency_layer()"
    else:
        rates = c.get_rates(api_spread)

    # Variables used by Javascript routines to refresh page content

    api_params = '\u003F{}{}'.format('currencies=', basket)

    html_head = "<!DOCTYPE html>"
    html_head += "<head>"
    html_head += "<title>Display Currency Exchange Rates</title>"
    html_head += "<meta charset='utf-8'>"
    html_head += "<meta name='viewport' content='width=device-width'>"

    # Stop annoying favicon.ico download attempts / failure

    html_head += "<link rel='icon' href='data:,'>"

    # Import CSS style config from publically readable S3 bucket

    html_head += "<link rel='stylesheet' type='text/css' media='screen'"
    html_head += "href='https://s3.amazonaws.com/mikeoc.me/CSS/Currency/main.css'>"
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
    html_body +=        build_select(basket)
    html_body +=    "</div>"

    # Output list of currency definitions

    html_body +=    "<div>"
    html_body +=        get_list(basket)
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
    # S3 similar to what was done with the CSS stylesheeet. Given the small
    # amount of Javascript code and the need to enforce strict JS loading with
    # approximately the same amount of JS, decision is to leave inline for now

    html_js = "<script type='text/javascript'>"
    html_js += "'use strict';"

    html_js += "var _base = getURIbase() + '{}';".format(api_params)

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


def db_connect(database='sql'):
    '''Open a connection to AWS RDS MySQL DB or confirm DynamoDB access'''

    from currency_config import db_host, db_port, db_user, db_pass, db_name
    from currency_config import dynamo_db_table

    if database == 'sql':           # Connect to DynamoDB
        try:
            conn = pymysql.connect(host=db_host, port=db_port, user=db_user, \
                            passwd=db_pass, db=db_name, connect_timeout=5)
        except:
            logger.error("ERROR: Could not connect to MySql instance.")
        else:
            logger.info("SUCCESS: Connection to RDS mysql instance succeeded")
            return conn

    elif database == 'DynamoDB':    # Connect to DynamoDB
        try:
            db = boto3.resource('dynamodb')
            table = db.Table(dynamo_db_table)
        except:
            logger.error("ERROR: Could not connect to DynamoDB.")
        else:
            logger.info("SUCCESS: DynamoDB Table {} created: {}".\
                            format(dynamo_db_table, table.creation_date_time))
            return table


def sql_update(conn, table, rates):
    '''Itterate through currency exchange rates and update RDS MySQL table'''

    with conn.cursor() as cur:
        for exch, cur_rate in rates.items():
            query = "UPDATE {} SET Rate = '{}' WHERE Abbr = '{}'".\
                     format(table, cur_rate, exch[-3:])
            cur.execute(query)
            logger.info(query)

        conn.commit()

    # Clean up
    cur.close()


def dynamo_update(table, data):
    '''Update DynamoDB values with provided Abbr:Rate (key:value) pair
       Convert rates to type Decimal before updating by first converting
       rate value to type str.
    '''

    for abbr, rate in data.items():
        response = table.update_item(
            Key={'Abbr': abbr[-3:]},
            UpdateExpression="set Rate = :r",
            ExpressionAttributeValues={':r': Decimal(str(rate))},
            ReturnValues="UPDATED_NEW"
            )


def sql_query(conn, table, abbr):
    '''For a given table value, query database and return result'''

    with conn.cursor() as cur:
        query = "SELECT * FROM {} WHERE Abbr = '{}'".format(table, abbr)
        cur.execute(query)
        for row in cur:
            logger.info("In db_query(): cur (row) = " + str(row))

    cur.close()             # Clean everything up

    return row


def dynamo_query(table, abbr):
    '''For a given table value, query database and return result'''

    response = table.get_item(
        Key={
            'Abbr': str(abbr)
            }
        )

    item = response['Item']
    rate = (abbr, item['Rate'])     # Build response to match SQL format

    return rate


def lambda_handler(event, context):
    '''AWS Lambda Event handler'''

    print("In lambda handler")

    logger.info('Event: {}'.format(event))

    return(build_resp(event))


# Signal handler for CTRL-C manual termination
def signal_handler(signal, frame):
    print(cur_col['endc'] + '\nProgram terminated manually', '', '\n')
    raise SystemExit()


def main():
    '''Main() used to simulate lambda event handler. Constructs event dict,
       calls build_resp and prints HTML/CSS/Javascript to console which can
       then be sent to a file and opened by a web browser.
    '''

    event = {
        'params': {
            'querystring': {
                'currencies': '',
                'spread': '1.00'
                }
            }
        }
    #event = {'params': {}}

    print(build_resp(event))


if __name__ == '__main__':
    """When invoked from shell, call signal() to handle CRTL-C from user
       and invoke main() function
    """
    signal(SIGINT, signal_handler)

    main()
