"""
Holt Fußballdaten (Real Madrid, Tottenham, Champions League) von football-data.org
und speichert sie als data/football.json im Repo. Wird von der GitHub Action
(.github/workflows/update-football.yml) regelmäßig automatisch ausgeführt.

Der API-Key kommt aus der Umgebungsvariable FOOTBALL_DATA_KEY (GitHub-Secret) -
steht NICHT im Klartext in diesem Skript oder im Repo.
"""

import json
import os
import urllib.request
from datetime import date, timedelta, datetime, timezone

API_KEY = os.environ["FOOTBALL_DATA_KEY"]
BASE = "https://api.football-data.org/v4"


def fd_get(path):
    req = urllib.request.Request(BASE + path, headers={"X-Auth-Token": API_KEY})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def resolve_team_id(comp_code, name_contains):
    data = fd_get(f"/competitions/{comp_code}/teams")
    for team in data.get("teams", []):
        if name_contains in (team.get("name") or "") or name_contains in (team.get("shortName") or ""):
            return team["id"]
    raise RuntimeError(f"{name_contains} nicht gefunden in Wettbewerb {comp_code}")


def fmt_match(m):
    if not m:
        return None
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
    }


def team_last_next(comp_code, name_contains):
    team_id = resolve_team_id(comp_code, name_contains)
    today = date.today()
    date_from = (today - timedelta(days=14)).isoformat()
    date_to = (today + timedelta(days=21)).isoformat()
    data = fd_get(f"/teams/{team_id}/matches?dateFrom={date_from}&dateTo={date_to}")
    matches = data.get("matches", [])
    finished = sorted(
        [m for m in matches if m["status"] == "FINISHED"],
        key=lambda m: m["utcDate"],
        reverse=True,
    )
    upcoming = sorted(
        [m for m in matches if m["status"] in ("SCHEDULED", "TIMED")],
        key=lambda m: m["utcDate"],
    )
    return {
        "last": fmt_match(finished[0]) if finished else None,
        "next": fmt_match(upcoming[0]) if upcoming else None,
    }


def champions_league():
    today = date.today()
    date_from = (today - timedelta(days=5)).isoformat()
    date_to = (today + timedelta(days=21)).isoformat()
    data = fd_get(f"/competitions/CL/matches?dateFrom={date_from}&dateTo={date_to}")
    matches = sorted(data.get("matches", []), key=lambda m: m["utcDate"])
    return [fmt_match(m) for m in matches[:6]]


def main():
    result = {"updated_at": datetime.now(timezone.utc).isoformat()}

    try:
        result["real_madrid"] = team_last_next("PD", "Real Madrid")
    except Exception as e:
        result["real_madrid"] = {"error": str(e)}

    try:
        result["tottenham"] = team_last_next("PL", "Tottenham")
    except Exception as e:
        result["tottenham"] = {"error": str(e)}

    try:
        result["champions_league"] = champions_league()
    except Exception as e:
        result["champions_league"] = {"error": str(e)}

    os.makedirs("data", exist_ok=True)
    with open("data/football.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Gespeichert:", json.dumps(result, ensure_ascii=False)[:500])


if __name__ == "__main__":
    main()
