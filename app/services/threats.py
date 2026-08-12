import requests


URL = "https://neptun.in.ua/api/v1/threats"


def get_threats():

    try:

        response = requests.get(
            URL,
            timeout=10
        )

        print(
            "THREATS STATUS:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "THREATS ERROR:",
                response.text
            )

            return None

        data = response.json()

        print(
            "THREATS COUNT:",
            len(
                data.get(
                    "threats",
                    []
                )
            )
        )

        return data

    except Exception as e:

        print(
            "❌ Помилка отримання загроз:",
            e
        )

        return None