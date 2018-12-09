from json import loads, dumps
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
          basket - Tuple of comma separated currency abbreviations
        """

        if mode == 'list':
            self.cl_url = base + 'list?' + 'access_key=' + key
        elif mode == 'live':
            self.cl_url = base + 'live?' + 'access_key=' + key + '&currencies='
            for c in basket:
                self.cl_url += c + ','       # OK to leave trailing ','

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


    def get_rates(self):
        '''Loop through exchange rate raw data and returned formatted HTML'''

        rates = self.cl_validate(self.cl_url)

        if isinstance(rates, str):                  # cl_validate returned Error
            rate_html = "<p>" + rates + "</p>"
        elif isinstance(rates, dict):               # cl_validate returned data
            ts = t_stamp(rates['timestamp'])
            rate_html = "<h2>Rates as of " + ts + "</h2>"
            rate_html += "<br>"
            for exch, cur_rate in rates['quotes'].items():
                in_usd = exch[-3:] + '/USD'
                in_for = 'USD/' + exch[3:]
                rate_html += "<pre>{}: {:>10.5f}   {}: {:>9.5f}</pre>".format(
                              in_usd, 1/cur_rate, in_for, cur_rate)
        else:
            rate_html = "<p>Expected string or dict in get_rates()<p>"

        return rate_html

def get_list(basket):
    '''Loop through basket of currency abbreviations and return with definitions
       Implemented as a function vs. class as not dependent on web service.
    '''

    rate_html = "<h2>Abbreviations</h2>"

    for abbr in basket:
        if abbr in curr_abbrs:
            rate_html += "<p>{} = {}</p>".format(abbr, curr_abbrs[abbr])
        else:
            rate_html += "<p>{} = {}</p>".format(
                          abbr.upper(), "Sorry, have no idea!")

    return rate_html


def t_stamp(t):
    """Timestamp utility function to format date and time from passed UNIX time
    """
    return(strftime('%y-%m-%d %H:%M %Z', localtime(t)))


def build_resp(event):
    '''Format the Head section of the DOM including any CSS formatting to
       apply to the remainder of the document. Break into multiple lines for
       improved readability
    '''

    html_head = "<!DOCTYPE html>"
    html_head += "<head>"
    html_head += "<title>Display Currency Exchange Rates</title>"
    html_head += "<style>"

    html_head += ".button {color: black; background-color: #93B874;}"
    html_head += ".button {padding: 5px 20px; margin: 4px 2px;}"
    html_head += ".button {text-align: center; font-size: 12pt;}"
    html_head += ".button {border-radius: 5px; cursor: pointer;}"
    html_head += ".button {border: 2px solid green;}"
    html_head += ".button {display: inline-block; text-decoration: none;}"

    html_head += ".center {text-align: center; font-size: 11pt;}"
    html_head += ".center {line-height: 0.5;}"
    html_head += ".center {border: 3px solid green;}"
    html_head += ".center {border-radius: 10px; padding: 2px;}"

    html_head += "body {background-color: #93B874;}"
    html_head += "body {width: 400px; margin: 0 auto;}"

    html_head += "h1 {text-align: center; text-decoration: none;}"
    html_head += "h2 {text-align: center; text-decoration: underline;}"
    html_head += "h3 {text_align: center; text-decoration: underline;}"

    html_head += "</style>"
    html_head += "</head>"

    # Define key variables associated with CurrencyLayer API web service

    cl_key = '<--- Your Code Goes Here --->'
    base = 'http://www.apilayer.net/api/'
    mode = 'list'
    basket = ['EUR', 'GBP', 'CNY', 'CAD', 'AUD', 'BTC']

    # If options passed as URL parameters, loop creating basket of currenciies

    try:
        options = event['params']['querystring']
    except:
        options = False
    else:
        for key, v in options.items():
            if key.lower() == "currencies":
                if v:
                    basket = v.split(',')

    # Instantiate currency_layer() object and initialize valiables

    try:
        c = currency_layer(base, 'live', cl_key, basket)
    except:
        rates = "<p>Error: unable to instantiate currency_layer()"
    else:
        rates = c.get_rates()

    html_body = "<body>"
    html_body += "<h1>Currency Exchange Rates</h1>"

    # Add a refresh button

    html_body += "<div align = center>"
    html_body += "<button class='button' onclick='location.reload();'>"
    html_body += "Refresh Page"
    html_body += "</button></div><br>"

    # Output list of currency exchange rates

    html_body += "<div class=center>"
    html_body += rates
    html_body += "</div>"

    html_body += "<br>"

    # Output list of currency definitions

    html_body += "<div class=center>"
    html_body += get_list(basket)
    html_body += "</div>"

    # Add a button to point to GitHub package

    html_body += "<br><div align = center>"
    html_body += "<button class='button' onclick=onlick='#'>"
    html_body += "<a href='https://github.com/mikeoc61/currency_monitor'>"
    html_body += "View Project on GitHub"
    html_body += "</button></div>"

    html_body += '</body>'

    html_tail = '</html>'

    resp = html_head + html_body + html_tail

    return resp


def lambda_handler(event, context):
    print("In lambda handler")

    logger.info('Event: {}'.format(event));

    return(build_resp(event))
