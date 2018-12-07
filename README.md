# currency_monitor
Monitors basket of foreign currencies for changes relative to USD and displays changes on console. There are 2 implementations of the program:

 - exchange.py is a command line version which displays updates once per hour
   to the console (terminal).

 - lambda.py is a simplified version for AWS lambda that runs once and returns
   results as a formatted Web page. Program uses HTML, CSS and Javascsript.

## Dependencies:

Command line version requires that CL_KEY environment variable be set prior to execution. The lambda version expects the key to be hard coded into the program code.

To obtain a key and compare price options visit: https://currencylayer.com
