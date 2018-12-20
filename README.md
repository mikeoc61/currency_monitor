# currency_monitor
Monitors basket of foreign currencies for changes relative to USD and displays changes on console. There are 2 implementations of the program:

- exchange.py is a command line version which displays updates once per hour
   to the console (terminal).

- lambda.py is a simplified version for AWS lambda that runs once and returns
  results as a formatted Web page. Program uses HTML, CSS and Javascript.

- currency_lambda.py is an updated version which uses and AWS RDS hosted MySQL
  database to hold previous currency exchange rate quotes which are compared
  with current quotes to determine if the dollar has strengthened or weakened
  relative to the last update.

- currency_config.py contains various configuration variable definitions along   
  with currency abbreviations and associated descriptions. Used with the lambda
  versions.

- main.css contains CSS Stylesheet formatting which is copied to a publicly
  accessible AWS S3 bucket and linked to from the lambda.py and currency_lambda.py

## Dependencies:

Command line version requires that CL_KEY environment variable be set prior to
execution. The lambda version expects the key and other variable to be defined
in currency_config.py

To obtain a key and review pricing options visit: https://currencylayer.com

The currency_lambda.py version expects to have an AWS RDS MySQL database defined
which it uses to store the most recent currency exchange rates.

## Technologies Used

- AWS Lambda, RDS, S3 and API Gateway
- Python 3 with Mypysql module
- HTML, CSS and Javascript
- Currency Layer Currency Exchange Quote service
