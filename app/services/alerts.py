import requests


URL = "https://neptun.in.ua/api/v1/alerts"


def get_alerts():

    try:

        response = requests.get(
            URL,
            timeout=(3, 5)
        )

        print(
            f"🚨 Alerts API status: {response.status_code}"
        )

        if response.status_code != 200:

            print(
                f"❌ Alerts API error: {response.text}"
            )

            return None

        return response.json()

    except requests.Timeout:

        print(
            "⏱️ Alerts API: перевищено час очікування"
        )

        return None

    except Exception as e:

        print(
            f"❌ Помилка Alerts API: {e}"
        )

        return None