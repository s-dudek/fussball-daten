"""
Holt Fußballdaten für die gewünschten Ligen (La Liga, Premier League, Champions League)
rund um heute und speichert sie als data/football.json im Repo. Wird von der GitHub Action
(.github/workflows/update-football.yml) regelmäßig automatisch ausgeführt.

Anders als in der ersten Version werden nicht nur Real Madrid und Tottenham einzeln
abgefragt, sondern ALLE Spiele der drei Ligen im Zeitfenster – wie beim Tages-Dashboard.
Auf der Live-Seite wird dann clientseitig erkannt, ob Real Madrid oder Tottenham dabei
sind, damit dort ein kleines Vereinslogo aufleuchtet.

Der API-Key kommt aus der Umgebungsvariable FOOTBALL_DATA_KEY (GitHub-Secret) -
steht NICHT im Klartext in diesem Skript oder im Repo.
"""

import json
import os
import urllib.request
from datetime import date, timedelta, datetime, timezone

API_KEY = os.environ["FOOTBALL_DATA_KEY"]
BASE = "https://api.football-data.org/v4"

# Gewünschte Ligen: La Liga (Real Madrid), Premier League (Tottenham), Champions League.
# Die österreichische Bundesliga (Sturm Graz) ist im kostenlosen Tarif nicht enthalten.
COMPETITIONS = ["PD", "PL", "CL"]


def fd_get(path):
    req = urllib.request.Request(BASE + path, headers={"X-Auth-Token": API_KEY})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def fmt_match(m):
    home = m["homeTeam"].get("shortName") or m["homeTeam"].get("name")
    away = m["awayTeam"].get("shortName") or m["awayTeam"].get("name")
    score = None
    if m["status"] == "FINISHED":
        ft = m["score"]["fullTime"]
        score = f'{ft["home"]}:{ft["away"]}'
    return {
        "home": home,
        "away": away,
        "date": m["utcDate"],
        "status": m["status"],
        "score": score,
        "competition": m["competition"]["name"],
        # Vereinswappen direkt von football-data.org, falls vorhanden - fürs Aufleuchten
        # von Real Madrid / Tottenham auf der Live-Seite.
        "homeCrest": m["homeTeam"].get("crest"),
        "awayCrest": m["awayTeam"].get("crest"),
    }


def matches_for_competition(comp_code, date_from, date_to):
    data = fd_get(f"/competitions/{comp_code}/matches?dateFrom={date_from}&dateTo={date_to}")
    return [fmt_match(m) for m in data.get("matches", [])]


def main():
    today = date.today()
    # Grosszügiges Fenster, damit Gestern/Heute/Morgen auf der Live-Seite immer genug
    # Auswahl haben, unabhängig davon, wann genau die Action gerade läuft.
    date_from = (today - timedelta(days=2)).isoformat()
    date_to = (today + timedelta(days=3)).isoformat()

    result = {"updated_at": datetime.now(timezone.utc).isoformat(), "matches": []}
    errors = {}

    for comp_code in COMPETITIONS:
        try:
            result["matches"].extend(matches_for_competition(comp_code, date_from, date_to))
        except Exception as e:
            errors[comp_code] = str(e)

    if errors:
        result["errors"] = errors

    result["matches"].sort(key=lambda m: m["date"])

    os.makedirs("data", exist_ok=True)
    with open("data/football.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Gespeichert:", json.dumps(result, ensure_ascii=False)[:500])


if __name__ == "__main__":
    main()
