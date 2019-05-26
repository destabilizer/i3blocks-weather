#!/usr/bin/env python

import os
import forecastio

def get_options():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-f', '--farenheit', dest='farenheit',
                      action='store_true', default=False,
                      help='Report degrees in Farenheit')
    parser.add_option('-c', '--celsius', dest='celsius',
                      action='store_true', default=False,
                      help='Report degrees in Celsius')
    parser.add_option('-u', '--units', dest='units',
                      action='store', help='Unit system you prefer. Could be "us", "ca", "uk", "si"')
    parser.add_option('-k', '--api-key', dest='api_key',
                      action='store', help='Dark Sky API key')
    parser.add_option('-a', '--address', dest='address',
                      action='store', help='Your address')
    parser.add_option('-t', '--temperature', dest='temperature',
                      action='store_true', default=True)
    parser.add_option('-g', '--general', dest='general',
                      action='store_true', default=True)
    parser.add_option('-w', '--wind', dest='wind',
                      action='store_true', default=False)
    parser.add_option('--humidity', dest='humidity',
                      action='store_true', default=False)
    parser.add_option('-r', '--round', dest='round',
                      action='store', help='Number of digits in temperature after point, default is 0')
    parser.add_option('--wind_round', dest='wind_round',
                      action='store', help='Number of digits in wind speed after point, default is 0')

    (options, args) = parser.parse_args()

    # Validate options
    if not options.api_key:
        raise RuntimeError('A Dark Sky API key is required. Go to darksky.net/dev')
    #if options.farenheit and options.celsius:
    #    raise RuntimeError('Only one degree unit may be specified')
    
    # Set units properly
    if options.units == 'us':
        options.farenheit = True
    elif options.units in ['ca', 'uk', 'si']:
        options.celsius = True
    elif options.farenheit:
        options.units = 'us'
    elif options.celsius:
        options.units = 'si'
    else:
        raise RuntimeError('No valid unit system was specified')
    
    return options

def get_ip_location():
    '''Get location as determined by IP address'''

    import requests
    import json

    send_url = 'http://ip-api.com/json'
    r = requests.get(send_url)
    j = json.loads(r.text)
    lat = j['lat']
    lon = j['lon']
    location = "{}, {}".format(j['city'], j['region'])
    return (lat, lon, location)

def get_addr_location(address):
    '''Get location from input string'''

    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent='i3blocks-weather')
    location = geolocator.geocode(address)
    return (location.latitude, location.longitude, address)

def round_temp(options, temp):
    if not options.round:
        temp = round(temp)
    else:
        p = int(options.round)
        temp = round(temp, p)
    return temp

def round_wind(options, wind_speed):
    if not options.wind_round:
        wind_speed = round(wind_speed)
    else:
        p = int(options.wind_round)
        wind_speed = round(wind_speed, p)
    return wind_speed

def notify_forecast(location, daily_summary, hourly_summary):
    '''Send notification with detailed forecast'''
    
    import subprocess
    
    title = u"Weather - {}".format(location)
    message = u"Hourly Summary:\n{0}\n\n".format(hourly_summary)
    message += u"Daily Summary:\n{0}".format(daily_summary)
    subprocess.Popen(['notify-send', title, message])

def get_icon_hex(options, icon_str):
    ''' Returns the appropriate icons for current weather and unit indication
       All Hex Codes from https://erikflowers.github.io/weather-icons/'''

    # Hex codes for the "degrees F" or "degrees C" icons.
    if options.farenheit:
        degrees_hex = 'f045'
    elif options.celsius:
        degrees_hex = 'f03c'
    else:
        raise RuntimeError('A degree unit must be specified')

    # Hex codes for the icon which indicates the current weather.
    if icon_str == 'clear-day':
        icon_hex='f00d'
    elif icon_str == 'clear-night':
        icon_hex='f02e'
    elif icon_str == 'rain':
        icon_hex='f019'
    elif icon_str == 'snow':
        icon_hex='f01b'
    elif icon_str == 'sleet':
        icon_hex='f0b5'
    elif icon_str == 'wind':
        icon_hex='f050'
    elif icon_str == 'fog':
        icon_hex='f014'
    elif icon_str == 'cloudy':
        icon_hex='f013'
    elif icon_str == 'partly-cloudy-day':
        icon_hex = 'f002'
    elif icon_str == 'partly-cloudy-night':
        icon_hex = 'f083'
    elif icon_str == 'thunderstorm':
        icon_hex = 'f016'
    elif icon_str == 'hail':
        icon_hex = 'f015'
    elif icon_str == 'tornado':
        icon_hex = 'f056'
    else:
        icon_hex = 'f07b' # N/A
    return (degrees_hex, icon_hex)

def generate_weather_status_line(options):
    icon = "&#x{0};"
    temp = "{4}&#x{1};"
    humd = "{5}&#x{2};"
    wind = "{6}{3}"
    status_line = []
    if options.humidity:    status_line.append(humd)
    if options.general:     status_line.append(icon)
    if options.temperature: status_line.append(temp)
    if options.wind:        status_line.append(wind)
    return "<span font='Weather Icons'>" + '  '.join(status_line) +"</span>" 

def main ():
    # Parse command line arguments
    options = get_options()

    # Get user's location either from IP address or command line arguments
    if options.address:
        (lat, lon, location) = get_addr_location(options.address)
    else:
        (lat, lon, location) = get_ip_location()

    # Load the forecast from Dark Sky (aka forecastio)
    forecast = forecastio.load_forecast(options.api_key, lat, lon, units=options.units)
    forecast_data = forecast.currently().d.copy()
    
    # If the weather icon is pressed, this environment variable will be set.
    buttonPressed = os.environ.get('BLOCK_BUTTON', None)
    
    # Send a notification with a more detailed forecast
    if buttonPressed:
        notify_forecast(location, forecast.daily().summary, forecast.hourly().summary)
    
    # Weather variables
    temp = round_temp(options, forecast_data['temperature'])
    humidity = round(100*forecast_data['humidity'])
    wind_speed = round_wind(options, forecast_data['windSpeed'])
    wind_degree = forecast_data['windBearing']
    #bscale = beafourt(wind_speed, options.units)

    # Translate icon & unit information into hex codes
    (degrees_hex, icon_hex) = get_icon_hex(options, forecast_data['icon'])
    humidity_hex = 'f07a'
    wind_degree_hex = 'f0b1'
    #bscale_hex = get_beafourt_icon_hex(bscale)

    # i3blocks uses pango to render the following output into the desired icons
    status_line = generate_weather_status_line(options)
    print(status_line.format(icon_hex, degrees_hex, humidity_hex, "m/s",
                                       temp,        humidity,     wind_speed))

if __name__ == "__main__":
    main()
    
