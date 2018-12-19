# currency_monitor
Monitors basket of foreign currencies for changes relative to USD and displays changes on console. There are 2 implementations of the program:

 - exchange.py is a command line version which displays updates once per hour
   to the console (terminal).

 - lambda.py is a simplified version for AWS lambda that runs once and returns
   results as a formatted Web page. Program uses HTML, CSS and Javascript.

 - currencies.py contains dictionary containing currency abbreviations and associated
   descriptions. Used by lambda.py version to display a mapping of selected
   currencies.

 - main.css contains CSS Stylesheet formatting which is copied to a publically
   accessable AWS S3 bucket and linked to by lambda.py

## Dependencies:

Command line version requires that CL_KEY environment variable be set prior to execution. The lambda version expects the key to be hard coded into the program.

To obtain a key and review pricing options visit: https://currencylayer.com
