# currency_monitor

Currency Monitor provide an easy way to monitor a basket of foreign currencies.
Using the Currency Layer Web Service, the program queries the service for the
latest quotations relative to the US dollar (USD) displays results. Using the
free tier, price quotes are guaranteed to be no more than 60 minutes old.
More frequent updates are available at higher price tiers. 

I've implemented both command line and lambda versions of the program.

- exchange.py is a command line version which displays updates once per hour
   to the console (terminal).

- lambda.py is a simplified version for AWS lambda that runs once and returns
  results as a formatted Web page. Program uses HTML, CSS and Javascript. Since
  there is no persistent data store used, this version can only display the most
  recent quotes with no knowledge of how prices have changed over the past 24
  hours.

- currency_lambda.py is an updated Lambda version which uses AWS DynamoDB service
  to hold previous currency quote results and timestamps which are compared
  with current quotes to determine if the dollar has strengthened or weakened.
  If more than 24 hours have elapsed since last database update, the database
  quote and timestamps are updated with most current info from Currency Layer service.

- init_dynamo_table.py is used to initialize the DynamoDB table with Abbreviations,
  Current Rates and Timestamp for each supported Currency. Run this once after
  table is created typically using the AWS console or AWS CLI. This can also be
  used at any time to re-establish a baseline for change comparisons.

- currency_config.py contains various configuration definitions along   
  with currency abbreviations and their associated descriptions. This file is
  only used with the lambda versions.

- main.css contains CSS Stylesheet formatting which is copied to a publicly
  accessible AWS S3 bucket and linked to from both lambda versions.

## Dependencies:

Command line version requires that CL_KEY environment variable be set prior to
execution. The lambda version expects the key and other variable to be defined
in currency_config.py.

To obtain a CL key and review pricing options visit: https://currencylayer.com

The currency_lambda.py version expects to have an AWS DynamoDB database defined
which it uses to store the most recent currency exchange rates.

init_dynamo_table.py expects to find AWS_SECRET_ACCESS_KEY and AWS_ACCESS_KEY_ID
defined in the users shell environment. See AWS IAM for more information.

## Technologies Used

- AWS Lambda, DynamoDB, S3 and API Gateway
- Python 3 with Boto3 module
- HTML, CSS, Javascript and Bootstrap
- Currency Layer Currency Exchange Rate Quote service
