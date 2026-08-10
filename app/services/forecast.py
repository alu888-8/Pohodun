import requests

from config import WEATHER_API_KEY, DEFAULT_CITY


def get_forecast(city=None):

    if city is None:
        city = DEFAULT_CITY

    url = "https://api.weatherapi.com/v1/forecast.json"

    params = {
        "key": WEATHER_API_KEY,
        "q": city,
        "days": 3,
        "lang": "uk"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            print(response.text)
            return None

        return response.json()

    except Exception as e:
        print(e)
        return None