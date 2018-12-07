from json import loads, dumps
from urllib.request import urlopen
from time import time, strftime, localtime
import logging

'''Currency Exchange Rate program written as a AWS lambda routine.

   Makes one request when invoked and returns HTML to calling browser.
'''

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
        """Open URL, read response and confirm query was successful. Otherwise
        exit the program with hopefully helpful diagnostics.
        """
        body_html = ["<h2>Error: validate() failed!</h2>"]

        try:
            webUrl = urlopen (url)
        except:
            print('Error: Not able to open: {}'.format(url))
            return(''.join(body_html))
        else:
            rate_data = webUrl.read()
            rate_dict = loads(rate_data.decode('utf-8'))
            if rate_dict['success'] is False:
                msg = 'Error: code = {}, type = {}, info = {}'.format(
                       rate_dict['error']['code'],
                       rate_dict['error']['type'],
                       rate_dict['error']['info'])
                body_html.append("<pre>" + msg + "</pre>")
            else:
                ts = t_stamp(rate_dict['timestamp'])
                body_html = ["<h3>As of " + ts + "</h3>"]
                for exch, cur_rate in rate_dict['quotes'].items():
                    in_usd = exch[-3:] + '/USD'
                    in_for = 'USD/' + exch[3:]
                    line = "<pre>{}: {:>8.5f}  {}: {:>9.5f}</pre>".format(
                            in_usd, 1/cur_rate, in_for, cur_rate)
                    body_html.append(line)

        return (''.join(body_html))     # Convert list to string

    def get_rates(self):
        try:
            rate_html = self.validate(self.cl_url)
        except:
            rate_html = "<h2>Error: Get Rates attempt failed!</h2>"

        return rate_html


def t_stamp(t):
    """Timestamp utility function to format date and time from passed UNIX time
    """
    return(strftime('%y-%m-%d %H:%M %Z', localtime(t)))



def lambda_handler(event, context):
    #print("In lambda handler")

    logger.info('Event: {}'.format(event));

    # Format the Head section of the DOM including any CSS formatting to
    # apply to the remainder of the document. Break into multiple lines for
    # improved readability

    html_head = "<!DOCTYPE html>"
    html_head += "<head>"
    html_head += "<title>Display Currency Exchange Rates</title>"
    html_head += "<style>"

    html_head += ".button {color: black; background-color: #93B874;}"
    html_head += ".button {text-align: center; padding: 5px 20px;}"
    html_head += ".button {border-radius: 4px; cursor: pointer;}"
    html_head += ".button {margin: 4px 2px; font-size: 18px;}"
    html_head += ".button {border: 2px solid green;}"
    html_head += ".button {display: inline-block; text-decoration: none;}"

    html_head += ".center {text-align: center;}"
    html_head += ".center {border: 3px solid green;}"
    html_head += ".center {border-radius: 10px; padding: 2px;}"
    html_head += "body {background-color: #93B874;}"
    html_head += "body {width: 400px; margin: 0 auto;}"
    html_head += "h1 {text-align: center;}"
    html_head += "h2 {text-align: center;}"
    html_head += "h3 {text_align: center;}"
    html_head += "</style>"
    html_head += "</head>"

    # Main body of code. Define basket of currencies and instantiate
    # currency_layer object and invoke get_rates() method.

    basket = ('EUR', 'GBP', 'CNY', 'CAD', 'AUD', 'JPY')

    key = ' <user api key goes here> '

    c = currency_layer(key, basket)
    rates = c.get_rates()

    html_body = "<body>"
    html_body += "<h1>Exchange Rates</h1>"

    html_body += "<div class=center>"
    html_body += rates
    html_body += "</div>"

    html_body += "<br><div align = center>"
    html_body += "<button class='button' onclick='location.reload();'>"
    html_body += "Refresh Page"
    html_body += "</button></div>"

    html_body += '</body>'

    html_tail = '</html>'

    resp = html_head + html_body + html_tail

    return resp
