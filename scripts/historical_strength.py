"""Experimental league-normalized attack and defence rates."""
def rates(home, away, league_home, league_away, prior=5):
    if min(len(home),len(away))<5 or min(league_home,league_away)<=0:
        return None
    def avg(rows,venue,index,mean):
        v=[r[index] for r in rows[-30:] if r[2]==venue]
        return (sum(v)+prior*mean)/(len(v)+prior)
    h=avg(home,"home",0,league_home)*avg(away,"away",1,league_home)/league_home
    a=avg(away,"away",0,league_away)*avg(home,"home",1,league_away)/league_away
    return tuple(max(.15,min(4,x)) for x in (h,a))
