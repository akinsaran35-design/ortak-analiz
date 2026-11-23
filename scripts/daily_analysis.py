"""Conservative, free-data football goal market screen. No paid API."""
import csv, io, json, math, urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=3))
now = datetime.now(TZ)
today = now.date()
# football-data.co.uk CSV coverage is limited, not worldwide.
LEAGUES = ["E0", "E1", "D1", "I1", "SP1", "F1", "N1", "B1", "P1", "SC0"]
SEASON = f"{today.year % 100:02d}{(today.year + 1) % 100:02d}" if today.month >= 7 else f"{(today.year - 1) % 100:02d}{today.year % 100:02d}"
OUTPUT = Path("daily.json")
report = {"date": today.isoformat(), "decision": "PAS", "picks": [],
          "reason": "Yeterli doğrulanabilir güncel maç/oran verisi bulunamadı.",
          "updatedAt": now.isoformat(timespec="seconds"),
          "source": "https://www.football-data.co.uk/data.php",
          "method": "Basit Poisson taraması; bağımsız doğrulama veya Dixon-Coles değildir."}

def number(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

def load(league):
    url = f"https://www.football-data.co.uk/mmz4281/{SEASON}/{league}.csv"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 OrtakAnaliz/1.0"})
    with urllib.request.urlopen(req, timeout=9) as response:
        data = response.read(2_000_000).decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(data))), url

def match_date(value):
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None

def poisson_over(lam, threshold):
    return 1 - sum(math.exp(-lam) * lam**k / math.factorial(k) for k in range(threshold+1))

candidates = []
checked = 0
for league in LEAGUES:
    try:
        rows, url = load(league)
    except Exception:
        continue
    history = defaultdict(list)
    for row in rows:
        date = match_date(row.get("Date", ""))
        hg, ag = number(row.get("FTHG")), number(row.get("FTAG"))
        if date and date < today and hg is not None and ag is not None:
            home, away = row.get("HomeTeam"), row.get("AwayTeam")
            if home and away:
                history[home].append((date, "home", hg, ag))
                history[away].append((date, "away", ag, hg))
    for row in rows:
        if match_date(row.get("Date", "")) != today or number(row.get("FTHG")) is not None:
            continue
        checked += 1
        home, away = row.get("HomeTeam"), row.get("AwayTeam")
        if not home or not away:
            continue
        # CSV dates often have no verified kick-off time; avoid potentially started games.
        kickoff = (row.get("Time") or "").strip()
        if not kickoff or ":" not in kickoff:
            continue
        try:
            hour, minute = [int(v) for v in kickoff.split(":")[:2]]
            # Data source times are not guaranteed to be in Turkey local time.
            # Conservative: exclude games less than 4 hours away, without assuming timezone.
            if hour < 12:
                continue
        except ValueError:
            continue
        hs = sorted(history[home], reverse=True)[:12]
        as_ = sorted(history[away], reverse=True)[:12]
        if len(hs) < 10 or len(as_) < 10:
            continue
        h_for = sum(x[2] for x in hs)/len(hs)
        h_against = sum(x[3] for x in hs)/len(hs)
        a_for = sum(x[2] for x in as_)/len(as_)
        a_against = sum(x[3] for x in as_)/len(as_)
        lam_h = max(.25, min(3.2, (h_for+a_against)/2))
        lam_a = max(.25, min(3.2, (a_for+h_against)/2))
        total = lam_h+lam_a
        # Only use named foreign bookmaker prices present on fixture row.
        for market, col, prob in [
            ("1.5 Üst", "B365>1.5", poisson_over(total, 1)),
            ("2.5 Üst", "B365>2.5", poisson_over(total, 2))
        ]:
            odds = number(row.get(col))
            if odds is None or not (1.1 <= odds <= 8):
                continue
            edge = prob * odds - 1
            # Strict screen, not a guarantee of winning.
            if prob >= .72 and edge >= .08:
                candidates.append({"match": f"{home} – {away}", "market": market,
                    "odds": round(odds, 2), "probability": round(prob*100, 1),
                    "edge": round(edge*100, 1), "source": url,
                    "note": "Basit Poisson ön elemesi; oran güncelliği teyit edilmedi.",
                    "kickoffSourceTime": kickoff})
# Do not present stale historical or unverified prices as today's live betting odds.
# This unattended screen intentionally remains PAS until a reliable timestamped
# pre-match odds feed and kickoff timezone verification are configured.
report["reason"] = (
    f"{checked} bugünkü fikstür satırı tarandı; {len(candidates)} istatistiksel aday bulundu. "
    "Ancak oranların güncel zaman damgası ve başlama saati doğrulanamadığı için "
    "otomatik bahis seçimi yapılmadı. Ücretsiz kaynak kapsamı sınırlıdır."
)
OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(report["reason"])
