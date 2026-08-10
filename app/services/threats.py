import requests

URL = "https://neptun.in.ua/api/v1/threats"


def get_threats():
    try:
        response = requests.get(URL, timeout=10)

        print("THREATS STATUS:", response.status_code)

        if response.status_code != 200:
            return None

        return response.json()

    except Exception as e:
        print(e)
        return None