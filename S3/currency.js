'use strict';

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
 * External dependencies set in parent HTML file
 *
 *  _basket: List of foreign currencies currently in basket
 *  _cl_ts: Currency Layer timestamp return by API call
 */

console.log('basket = ' + basket);
console.log('cl_ts = ' + cl_ts);

// Define global variables used in functions below

var url = window.location;
var baseUrl = url.origin + url.pathname;
var urlBasket = baseUrl + '?currencies=' + basket;

// Reset currency basket and spread percentage to defaults
// by calling Lambda function without optional parameters

function resetDefaults() {
  location.replace(baseUrl);
  return false;
  }

// Take user selected spread percentage and use that
// value to form new URL before calling Lambda function

function changeSpread(action) {
  var _spr = document.getElementById('spread_input').value;
  var _url = urlBasket + '&spread=' + _spr;
  location.replace(_url);
  }

// Read user selection and append that currency abbr.
// to the URL Parameter section of URL before calling Lambda function

function addCurrency(action) {
  var _spr = document.getElementById('spread_input').value;
  var _abbr = document.getElementById('currency_abbr').value;
  if (_abbr) {
    var _url = urlBasket + ',' + _abbr + '&spread=' + _spr;
    location.replace(_url);
    } else {
      alert('Please select a currency before submitting');
    }
  }

// Replace GMT timestamp in header with local TZ representation
// For 12 hour (AM/PM) format, set options.hour12 to true

function showDate(tstamp) {
  var options = {year: 'numeric', month: 'short', day: 'numeric'}
  options.hour = 'numeric';
  options.minute = 'numeric';
  options.timeZoneName ='short';
  options.hour12 = false;
  var _date = new Date(tstamp);
  var new_ts = 'Rates as of ' + _date.toLocaleDateString("en-US", options);
  document.getElementById('t_stamp').innerHTML = new_ts;
  console.log('Resetting tstamp to: ' + new_ts);
  }

// Once DOM has fully loaded, reset the Timestamp header using local TZ
// Use timestamp from Currency Layer call to initialize JS variable

window.onload = showDate(cl_ts * 1000);
