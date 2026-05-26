import requests

from jibble.jibble_connect import get_jibble_access_token, jibble_member_exists

JIBBLE_TIME_OFF_URL = "https://time-tracking.prod.jibble.io/v1/TimeOffIntervals"
CP_ID = "e7d25280-c89c-462b-809c-ffac81b9dfe1"


def demander_conge(
    start_date: str,
    end_date: str,
    note: str,
    person_id: str,
    access_token: str | None = None,
) -> tuple[int, dict[str, object]]:
    if not access_token:
        token_data = get_jibble_access_token()
        access_token = token_data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Token Jibble invalide.")

    if not jibble_member_exists(person_id, access_token=access_token):
        raise ValueError(f"Le membre avec l'id '{person_id}' n'existe pas.")

    payload = {
        "startDate": start_date,
        "endDate": end_date,
        "note": note,
        "personId": person_id,
        "policyId": CP_ID,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    session = requests.Session()
    session.trust_env = False

    response = session.post(
        JIBBLE_TIME_OFF_URL,
        json=payload,
        headers=headers,
        timeout=30,
    )

    try:
        body = response.json()
    except ValueError:
        body = {"raw_response": response.text}

    return response.status_code, body


if __name__ == "__main__":
    status_code, body = demander_conge(
        start_date="2024-02-11",
        end_date="2024-02-16",
        note="Just a vacation",
        person_id="fbb1572e-e9fc-46bc-9d28-c28828a61400",
    )
    print("Status:", status_code)
    print(body)
