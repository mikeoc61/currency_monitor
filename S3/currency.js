/*
 * Currency.js v0.9
 * Code is specific to the Currency Exchange Rate Project
 *
 * File is read into the main program with the following code:
 *
 *      html_js += "<script src='{}'></script>".format(CURRENCY_JS)
 *
 *      CURRENCY_JS is defined in currency_config.py and should point to
 *      its hosted location on AWS S3
 *
 * Copyright 2019 Michael O'Connor
 * Licensed under the MIT license
 */

/*
 * External dependencies defined in parent HTML file generated by Python
 *
 *  BASKET: List of foreign currencies currently in basket
 *  CL_TS: Currency Layer timestamp return by API call
 */

// Define global constants used in functions below. Using constants
// as this code reloads and runs once with each button press event

const URL = window.location;
const URL_BASE = URL.origin + URL.pathname;
const URL_BASKET = URL_BASE + '?currencies=' + BASKET;

const SPREAD = document.getElementById('spread_input');

console.log('Currency basket = ' + BASKET);
console.log('Currency spread = ' + SPREAD.value);

// Reset currency basket and spread percentage to defaults
// by calling Lambda function without optional parameters

function resetDefaults() {
  location.replace(URL_BASE);
  return false;
  }

// Take user selected spread percentage and use that
// value to form new URL before calling Lambda function

function changeSpread(action) {
  let newSpread = SPREAD.value;
  let newUrl = URL_BASKET + '&spread=' + newSpread;
  location.replace(newUrl);
  }

// Read user selection and append that currency abbr.
// to the URL Parameter section of URL before calling Lambda function

function addCurrency(action) {
  var spread = SPREAD.value;
  var newAbbr = document.getElementById('currency_abbr').value;
  if (newAbbr) {
    let newUrl = URL_BASKET + ',' + newAbbr + '&spread=' + spread;
    location.replace(newUrl);
    } else {
      alert('Please select a currency before submitting');
    }
  }

// If window.onload has not already been assigned a function, the function
// passed to addLoadEvent is simply assigned to window.onload. If window.onload
// has already been set, a brand new function is created which first calls the
// original onload handler, then calls the new handler afterwards.
// Reference:
//  https://www.htmlgoodies.com/beyond/javascript/article.php/3724571/Using-Multiple-JavaScript-Onload-Functions.htm

function addLoadEvent(func) {
  var oldonload = window.onload;
  if (typeof window.onload != 'function') {
    window.onload = func;
  } else {
    window.onload = function() {
      if (oldonload) {
        oldonload();
      }
      func();
    }
  }
}

// Once DOM has fully loaded, reset the Timestamp header using local TZ
// Use timestamp from Currency Layer call to initialize JS variable.
// Since Javascript time representations are in milliseconds, multiply
// seconds since the epoch times 1000

addLoadEvent(function() {
  const OPTIONS = {year: 'numeric', month: 'short', day: 'numeric'}
  OPTIONS.hour = 'numeric';
  OPTIONS.minute = 'numeric';
  OPTIONS.timeZoneName ='short';
  OPTIONS.hour12 = false;
  let date = new Date(CL_TS * 1000);
  let newTS = date.toLocaleDateString("en-US", OPTIONS);
  console.log('Old Header: ' + document.getElementById('t_stamp').outerHTML);
  document.getElementById('t_stamp').innerHTML = 'Rates as of ' + newTS;
  console.log('New Header: ' + document.getElementById('t_stamp').outerHTML);
  })
