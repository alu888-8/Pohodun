import requests

URL = "https://neptun.in.ua/api/v1/threats"


def get_threats():

    try:

        response = requests.get(
            URL,
            timeout=(3, 7)
        )

        print(
            "🛰 Threats API status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "❌ Threats API error:",
                response.text
            )

            return None

        data = response.json()

        threats = data.get(
            "threats",
            []
        )

        print(
            "🛰 Threats count:",
            len(threats)
        )

        return data

    except requests.Timeout:

        print(
            "⏱️ Threats API: timeout"
        )

        return None

    except Exception as e:

        print(
            f"❌ Помилка отримання загроз: {e}"
        )

        return None