"""Conservative merge of same-source historical snapshots."""
def merge(previous, current, conflicts, start, end):
    rows={}
    blocked=set(conflicts)
    for row in previous+current:
        k=str(row["matchID"])
        if not start <= row["date"] < end: continue
        if k in rows and rows[k]!=row: blocked.add(k)
        rows[k]=row
    return [v for k,v in rows.items() if k not in blocked], sorted(blocked)
