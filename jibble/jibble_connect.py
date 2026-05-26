import requests

JIBBLE_TOKEN_URL = "https://identity.prod.jibble.io/connect/token"
JIBBLE_PEOPLE_URL = "https://workspace.prod.jibble.io/v1/People"
JIBBLE_CLIENT_ID = "3248789b-fb95-4120-a16b-2f4967276a34"
JIBBLE_CLIENT_SECRET = "6nNt2qc8bxBvICPBdd0kgHBDpHp4CexELBAZYvXKseoZBK4u"


def get_jibble_access_token() -> dict[str, object]:
    payload = {
        "grant_type": "client_credentials",
        "client_id": JIBBLE_CLIENT_ID,
        "client_secret": JIBBLE_CLIENT_SECRET,
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    session = requests.Session()
    session.trust_env = False

    response = session.post(JIBBLE_TOKEN_URL, data=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def jibble_member_exists(user_id: str, access_token: str | None = None) -> bool:
    if not access_token:
        token_data = get_jibble_access_token()
        access_token = token_data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Token Jibble invalide.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    session = requests.Session()
    session.trust_env = False

    response = session.get(f"{JIBBLE_PEOPLE_URL}({user_id})", headers=headers, timeout=30)
    if response.status_code == 404:
        return False
    response.raise_for_status()

    return True


if __name__ == "__main__":
    print(get_jibble_access_token())
