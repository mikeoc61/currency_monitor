from json import loads
from urllib.request import urlopen
from time import time, strftime, localtime
from currencies import curr_abbrs
import logging

'''Currency Exchange Rate program written as a AWS lambda routine.

   Makes one request when invoked and returns HTML to calling browser.
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


    def cl_validate(self, url):
        """Attempt to open supplied URL. If initial open is successful, read
           contents to determine if API call was successful. If so, return
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
        '''Loop through exchange rate raw data and returned formatted HTML'''

        rates = self.cl_validate(self.cl_url)
        spread = float(spread)

        if isinstance(rates, str):                  # cl_validate returned Error
            rate_html = "<p>" + rates + "</p>"
        elif isinstance(rates, dict):               # cl_validate returned data
            ts = t_stamp(rates['timestamp'])
            rate_html = "<h2>As of " + ts + "</h2>"

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

            spread = spread / 100                    # convert to percentage
            rate_html += "<br>"
            for exch, cur_rate in rates['quotes'].items():
                in_usd = exch[-3:] + '/USD'
                in_for = 'USD/' + exch[3:]
                usd_spread = (1/cur_rate)*(1+spread)
                for_spread = cur_rate*(1/(1+spread))
                _usd = "{}: {:>9.4f} ({:>9.4f})   {}: {:>7.4f} ({:>6.4f})".format(
                        in_usd, 1/cur_rate, usd_spread,
                        in_for, cur_rate, for_spread)
                _for = "{}: {:>9.4f} ({:>9.4f})   {}: {:>7.4f} ({:>6.4f})".format(
                        in_for, cur_rate, for_spread,
                        in_usd, 1/cur_rate, usd_spread)

                if exch[3:] in ['EUR', 'GBP', 'AUD', 'BTC']:
                    rate_html += "<pre>" + _usd + "</pre>"
                else:
                    rate_html += "<pre>" + _for + "</pre>"

        else:
            rate_html = "<p>Expected string or dict in get_rates()<p>"

        return rate_html


def get_list(basket):
    '''Loop through basket of currency abbreviations and return with definitions
       Implemented as a function vs. class as not dependent on web service.
    '''

    rate_html = "<h2>Abbreviations</h2>"

    basket_list = basket.split(',')

    unique = []                 # Used to eliminate redundant currencies

    for abbr in basket_list:
        if abbr not in unique:
            unique.append(abbr)
            if abbr in curr_abbrs:
                rate_html += "<p>{} = {}</p>".format(abbr, curr_abbrs[abbr])
            else:
                rate_html += "<p>{} = {}</p>".format(
                          abbr.upper(), "Sorry, have no idea!")

    return rate_html

def build_select(basket):
    '''Loop through basket of currency abbreviations and return with a list of
       selections to be added to basket.
    '''

    basket_list = basket.split(',')

    select_html = "<div id='cur_select' class='myForm'>"
    select_html += "<form id='currency_form' action='#' "
    select_html += "onsubmit=\"addCurrency('text');return false\">"

    select_html += "<label for='select_label'>Add: </label>"
    select_html += "<select id='currency_abbr' type='text' name='abbrSelect'>"
    select_html += "<option disabled selected value> select currency </option>"

    for abbr in curr_abbrs:
        if abbr not in basket_list:
            select_html += "<option value='{}'>{}</option>".format(
                                           abbr, curr_abbrs[abbr])

    select_html += "</select>"
    select_html += "<input type='submit' class='button' onclick = '...'>"
    select_html += "</form></div>"

    select_html += "<br>"

    return select_html


def t_stamp(t):
    """Utility function to format date and time from passed UNIX time"""
    return(strftime('%y-%m-%d %H:%M %Z', localtime(t)))


def build_resp(event):
    '''Format the Head section of the DOM including any CSS formatting to
       apply to the remainder of the document. Break into multiple lines for
       improved readability
    '''

    # Define key variables defaults associated with CurrencyLayer web service

    cl_key = '<--Your CL Access Code Here -->'
    base = 'http://www.apilayer.net/api/'
    mode = 'list'                           # Use List mode (not implemented)
    basket = 'EUR,GBP,JPY,CHF,AUD,CAD'      # Default Currency basket
    api_spread = 1.0                        # Default spread = 1.0%

    # If options passed as URL parameters replace default values accordingly

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
                    api_spread = val

    logger.info('Basket: {}'.format(basket))
    logger.info('Spread: {}'.format(api_spread))

    # Instantiate currency_layer() object and initialize valiables

    try:
        c = currency_layer(base, 'live', cl_key, basket)
    except:
        rates = "<p>Error: unable to instantiate currency_layer()"
    else:
        rates = c.get_rates(api_spread)

    logger.info('Rates: {}'.format(rates))

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
    html_body +=    "<div style='display: inline;'>"
    html_body +=        rates
    html_body +=    "</div>"

    # Add a new currency to basket
    html_body +=    "<div style='display: inline;'>"
    html_body +=        build_select(basket)
    html_body +=    "</div>"

    # Output list of currency definitions
    html_body +=    "<div style='display: inline;'>"
    html_body +=        get_list(basket)
    html_body +=    "</div>"

    # Provide button to reset currency basket and spread to default
    html_body +=    "<div style='display: inline;'>"
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

    #html_js += "var _spread = {:3.1f};".format(float(api_spread))
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


def lambda_handler(event, context):
    print("In lambda handler")

    logger.info('Event: {}'.format(event))

    return(build_resp(event))
