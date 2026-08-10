import requests

URL = "https://neptun.in.ua/api/v1/alerts"


def get_alerts():
    try:
        response = requests.get(URL, timeout=10)

        print("STATUS:", response.status_code)
        print(response.text)

        if response.status_code != 200:
            return None

        return response.json()

    except Exception as e:
        print(e)
        return None