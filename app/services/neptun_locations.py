import requests
from functools import lru_cache


RAIONS_URL = "https://neptun.in.ua/raions.geojson"
OBLASTS_URL = "https://neptun.in.ua/oblasts.geojson"


# Севастополь залишається в даних NEPTUN,
# але поки не показується як окрема область у меню.
HIDDEN_MENU_OBLASTS = {
    "севастополь",
}


# =====================================================
# ЗАВАНТАЖЕННЯ JSON
# =====================================================

def _download_json(url):

    response = requests.get(
        url,
        timeout=20,
    )

    response.raise_for_status()

    return response.json()


# =====================================================
# ГЕОМЕТРІЯ
# =====================================================

def _ring_area_and_centroid(ring):

    """
    Обчислює площу та центроїд кільця GeoJSON.

    GeoJSON:
    [
        [lon, lat],
        ...
    ]
    """

    if not ring or len(ring) < 3:
        return 0.0, None

    area = 0.0
    centroid_x = 0.0
    centroid_y = 0.0

    for index in range(
        len(ring) - 1
    ):

        x1, y1 = ring[index]
        x2, y2 = ring[index + 1]

        cross = (
            x1 * y2
            - x2 * y1
        )

        area += cross

        centroid_x += (
            x1 + x2
        ) * cross

        centroid_y += (
            y1 + y2
        ) * cross

    area /= 2.0

    if abs(area) < 1e-12:

        # Запасний варіант
        xs = [
            point[0]
            for point in ring
        ]

        ys = [
            point[1]
            for point in ring
        ]

        return (
            0.0,
            (
                sum(xs) / len(xs),
                sum(ys) / len(ys),
            )
        )

    centroid_x /= (
        6.0 * area
    )

    centroid_y /= (
        6.0 * area
    )

    return (
        abs(area),
        (
            centroid_x,
            centroid_y,
        )
    )


def _representative_point(
    geometry
):

    """
    Отримуємо репрезентативну точку
    для Polygon або MultiPolygon.
    """

    if not geometry:
        return None

    geometry_type = geometry.get(
        "type"
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if not coordinates:
        return None

    # =================================================
    # POLYGON
    # =================================================

    if geometry_type == "Polygon":

        if not coordinates:
            return None

        outer_ring = coordinates[0]

        _, centroid = (
            _ring_area_and_centroid(
                outer_ring
            )
        )

        return centroid

    # =================================================
    # MULTIPOLYGON
    # =================================================

    if geometry_type == "MultiPolygon":

        largest_area = 0.0
        largest_centroid = None

        for polygon in coordinates:

            if not polygon:
                continue

            outer_ring = polygon[0]

            area, centroid = (
                _ring_area_and_centroid(
                    outer_ring
                )
            )

            if (
                centroid is not None
                and area > largest_area
            ):

                largest_area = area
                largest_centroid = centroid

        return largest_centroid

    return None


def _point_in_ring(
    lon,
    lat,
    ring
):

    """
    Ray casting для перевірки:
    чи знаходиться точка всередині Polygon ring.
    """

    inside = False

    if not ring or len(ring) < 3:
        return False

    previous = len(ring) - 1

    for current in range(
        len(ring)
    ):

        x1, y1 = ring[current]
        x2, y2 = ring[previous]

        intersects = (
            ((y1 > lat) != (y2 > lat))
            and
            (
                lon
                <
                (
                    (x2 - x1)
                    *
                    (lat - y1)
                    /
                    (
                        (y2 - y1)
                        if y2 != y1
                        else 1e-12
                    )
                    +
                    x1
                )
            )
        )

        if intersects:
            inside = not inside

        previous = current

    return inside


def _point_in_geometry(
    point,
    geometry
):

    """
    Перевіряє точку всередині Polygon/MultiPolygon.
    """

    if not point or not geometry:
        return False

    lon, lat = point

    geometry_type = geometry.get(
        "type"
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if not coordinates:
        return False

    # =================================================
    # POLYGON
    # =================================================

    if geometry_type == "Polygon":

        if not coordinates:
            return False

        outer_ring = coordinates[0]

        if not _point_in_ring(
            lon,
            lat,
            outer_ring
        ):
            return False

        # Перевіряємо дірки Polygon.
        for hole in coordinates[1:]:

            if _point_in_ring(
                lon,
                lat,
                hole
            ):
                return False

        return True

    # =================================================
    # MULTIPOLYGON
    # =================================================

    if geometry_type == "MultiPolygon":

        for polygon in coordinates:

            if not polygon:
                continue

            outer_ring = polygon[0]

            if not _point_in_ring(
                lon,
                lat,
                outer_ring
            ):
                continue

            inside_hole = False

            for hole in polygon[1:]:

                if _point_in_ring(
                    lon,
                    lat,
                    hole
                ):

                    inside_hole = True
                    break

            if not inside_hole:
                return True

    return False


# =====================================================
# ЗАВАНТАЖЕННЯ ЛОКАЦІЙ
# =====================================================

@lru_cache(maxsize=1)
def get_locations():

    """
    Завантажує області та райони
    безпосередньо з NEPTUN.

    Додатково автоматично визначає,
    до якої області належить кожний район.
    """

    raions_data = _download_json(
        RAIONS_URL
    )

    oblasts_data = _download_json(
        OBLASTS_URL
    )

    oblasts = []
    raions = []

    # =================================================
    # ОБЛАСТІ
    # =================================================

    for feature in oblasts_data.get(
        "features",
        []
    ):

        properties = feature.get(
            "properties",
            {}
        )

        key = properties.get(
            "key"
        )

        name = properties.get(
            "region"
        )

        geometry = feature.get(
            "geometry"
        )

        if (
            not key
            or not name
            or not geometry
        ):
            continue

        oblasts.append(
            {
                "key": key,
                "name": name,
                "geometry": geometry,
            }
        )

    # =================================================
    # РАЙОНИ
    # =================================================

    for feature in raions_data.get(
        "features",
        []
    ):

        properties = feature.get(
            "properties",
            {}
        )

        key = properties.get(
            "key"
        )

        name = properties.get(
            "rayon"
        )

        geometry = feature.get(
            "geometry"
        )

        if (
            not key
            or not name
            or not geometry
        ):
            continue

        raions.append(
            {
                "key": key,
                "name": name,
                "geometry": geometry,
            }
        )

    # =================================================
    # ЗВ'ЯЗУЄМО РАЙОНИ З ОБЛАСТЯМИ
    # =================================================

    oblast_lookup = {}

    for oblast in oblasts:

        oblast_lookup[
            oblast["key"]
        ] = oblast

    for raion in raions:

        point = _representative_point(
            raion["geometry"]
        )

        raion["oblast_key"] = None
        raion["oblast_name"] = None

        if point is None:
            continue

        for oblast in oblasts:

            if _point_in_geometry(
                point,
                oblast["geometry"]
            ):

                raion["oblast_key"] = (
                    oblast["key"]
                )

                raion["oblast_name"] = (
                    oblast["name"]
                )

                break

        if (
            raion["oblast_key"]
            is None
        ):

            print(
                "⚠️ NEPTUN | "
                "Не вдалося визначити область "
                f"для району: {raion['name']}"
            )

    return {
        "oblasts": oblasts,
        "raions": raions,
    }


# =====================================================
# ОБЛАСТІ ДЛЯ МЕНЮ
# =====================================================

def get_oblasts():

    data = get_locations()

    result = []

    for item in data["oblasts"]:

        if item["key"] in (
            HIDDEN_MENU_OBLASTS
        ):
            continue

        result.append(
            {
                "key": item["key"],
                "name": item["name"],
            }
        )

    return result


# =====================================================
# ВСІ РАЙОНИ
# =====================================================

def get_raions():

    data = get_locations()

    result = []

    for item in data["raions"]:

        result.append(
            {
                "key": item["key"],
                "name": item["name"],
                "oblast_key": item.get(
                    "oblast_key"
                ),
                "oblast_name": item.get(
                    "oblast_name"
                ),
            }
        )

    return result


# =====================================================
# РАЙОНИ КОНКРЕТНОЇ ОБЛАСТІ
# =====================================================

def get_raions_by_oblast(
    oblast_key
):

    data = get_locations()

    target = (
        str(oblast_key)
        .strip()
        .lower()
    )

    result = []

    for item in data["raions"]:

        item_oblast = (
            item.get(
                "oblast_key"
            )
            or ""
        ).strip().lower()

        if item_oblast != target:
            continue

        result.append(
            {
                "key": item["key"],
                "name": item["name"],
                "oblast_key": item_oblast,
                "oblast_name": item.get(
                    "oblast_name"
                ),
            }
        )

    result.sort(
        key=lambda item:
        item["name"].lower()
    )

    return result


# =====================================================
# ЗНАЙТИ ОБЛАСТЬ
# =====================================================

def find_oblast(
    location_key
):

    data = get_locations()

    target = (
        str(location_key)
        .strip()
        .lower()
    )

    for item in data["oblasts"]:

        if (
            item["key"]
            .strip()
            .lower()
            == target
        ):

            return {
                "key": item["key"],
                "name": item["name"],
            }

    return None


# =====================================================
# ЗНАЙТИ РАЙОН
# =====================================================

def find_raion(
    location_key
):

    data = get_locations()

    target = (
        str(location_key)
        .strip()
        .lower()
    )

    for item in data["raions"]:

        if (
            item["key"]
            .strip()
            .lower()
            == target
        ):

            return {
                "key": item["key"],
                "name": item["name"],
                "oblast_key": item.get(
                    "oblast_key"
                ),
                "oblast_name": item.get(
                    "oblast_name"
                ),
            }

    return None


# =====================================================
# ПОШУК ОБЛАСТІ ЗА НАЗВОЮ
# =====================================================

def find_oblast_by_name(
    name
):

    if not name:
        return None

    target = (
        str(name)
        .strip()
        .lower()
    )

    for item in get_oblasts():

        if (
            item["name"]
            .strip()
            .lower()
            == target
        ):

            return item

    return None


# =====================================================
# ПОШУК РАЙОНУ ЗА НАЗВОЮ
# =====================================================

def find_raion_by_name(
    name
):

    if not name:
        return None

    target = (
        str(name)
        .strip()
        .lower()
    )

    for item in get_raions():

        if (
            item["name"]
            .strip()
            .lower()
            == target
        ):

            return item

    return None


# =====================================================
# НАСЕЛЕНІ ПУНКТИ ДЛЯ МОНІТОРИНГУ
# =====================================================

def find_raion_by_coordinates(latitude, longitude):
    """
    Знаходить район NEPTUN за координатами.
    Координати: latitude, longitude.
    """

    point = (float(longitude), float(latitude))

    for raion in get_locations()["raions"]:
        if _point_in_geometry(point, raion.get("geometry")):
            return {
                "key": raion["key"],
                "name": raion["name"],
                "oblast_key": raion.get("oblast_key"),
                "oblast_name": raion.get("oblast_name"),
            }

    return None


@lru_cache(maxsize=1)
def get_city_locations():
    """
    Формує список міст для моніторингу з CITY_API.

    Район та область визначаються автоматично
    за геометрією NEPTUN.

    Київ обробляється окремо як місто зі спеціальним
    адміністративним статусом.
    """

    from app.data.cities import CITY_API

    data = get_locations()

    oblast_by_key = {
        item["key"]: item
        for item in data["oblasts"]
    }

    result = []

    for city, coordinates in CITY_API.items():

        try:
            latitude, longitude = (
                float(value.strip())
                for value in coordinates.split(",")
            )
        except (ValueError, AttributeError):
            print(
                f"⚠️ NEPTUN | Некоректні координати: {city}"
            )
            continue

        # Київ — окрема адміністративна одиниця.
        if city == "Київ":
            result.append({
                "key": "kyiv-city",
                "name": "Київ",
                "type": "city",
                "oblast_key": "kyiv-city",
                "oblast_name": "Київ",
                "raion_key": None,
                "raion_name": None,
                "latitude": latitude,
                "longitude": longitude,
            })
            continue

        raion = find_raion_by_coordinates(
            latitude,
            longitude,
        )

        if raion is None:
            print(
                f"⚠️ NEPTUN | "
                f"Не вдалося визначити район для: {city}"
            )
            continue

        oblast_key = raion.get("oblast_key")
        oblast_name = raion.get("oblast_name")

        if oblast_key in oblast_by_key:
            oblast_name = oblast_by_key[oblast_key]["name"]

        result.append({
            "key": city.lower(),
            "name": city,
            "type": "city",
            "oblast_key": oblast_key,
            "oblast_name": oblast_name,
            "raion_key": raion["key"],
            "raion_name": raion["name"],
            "latitude": latitude,
            "longitude": longitude,
        })

    result.sort(
        key=lambda item: item["name"].lower()
    )

    return result


def get_city_location_names():
    """
    Повертає міста у форматі для клавіатури.
    """

    return [
        {
            "key": item["key"],
            "name": item["name"],
        }
        for item in get_city_locations()
    ]


def find_city_location(city_name):
    """
    Знаходить місто за назвою.
    """

    if not city_name:
        return None

    target = str(city_name).strip().lower()

    for city in get_city_locations():
        if city["name"].strip().lower() == target:
            return city

    return None
