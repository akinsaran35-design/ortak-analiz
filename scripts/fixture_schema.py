"""Normalize documented OpenFootball collection shapes without hiding invalid data."""
def matches_in(data):
    if isinstance(data,list):
        rows=data
    elif isinstance(data,dict) and isinstance(data.get("matches"),list):
        rows=data["matches"]
    elif isinstance(data,dict) and isinstance(data.get("rounds"),list):
        rows=[]
        for rnd in data["rounds"]:
            if not isinstance(rnd,dict) or not isinstance(rnd.get("matches"),list):
                raise ValueError("invalid round")
            rows.extend(rnd["matches"])
    else:
        raise ValueError("unsupported fixture collection")
    if any(not isinstance(row,dict) for row in rows):
        raise ValueError("invalid fixture row")
    return rows


def final_score(row):
    """Return only a validated explicit full-time score; unknown shapes stay unresolved."""
    score=row.get("score")
    if not isinstance(score,dict):
        return None
    ft=score.get("ft")
    if isinstance(ft,list) and len(ft)==2 and all(type(x) is int and x>=0 for x in ft):
        return ft
    return None
