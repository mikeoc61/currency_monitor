# currency_monitor

Monitors basket of foreign currencies for changes relative to USD and displays changes on console. There are several implementations of the program:

- exchange.py is a command line version which displays updates once per hour
   to the console (terminal).

- lambda.py is a simplified version for AWS lambda that runs once and returns
  results as a formatted Web page. Program uses HTML, CSS and Javascript.

- currency_lambda.py is an updated Lambda version which uses AWS DynamoDB service
  to hold previous currency exchange rate quotes and timestamps which are compared
  with current quotes to determine if the dollar has strengthened or weakened
  relative to the last update. If more than 24 hours have elapsed since last
  database update, the database quote and timestamps are updated with most
  current info from Currency Layer service.

- init_dynamo_table.py is used to initialize the DynamoDB table with Abbreviations,
  Current Rates and Timestamp for each supported Currency. Run this once after
  table is created typically using the AWS console or AWS CLI.

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

The currency_lambda.py version expects to have an AWS DynamoDB database defined
which it uses to store the most recent currency exchange rates.

## Technologies Used

- AWS Lambda, DynamoDB, S3 and API Gateway
- Python 3 with Boto3 module
- HTML, CSS and Javascript
- Currency Layer Currency Exchange Quote service
