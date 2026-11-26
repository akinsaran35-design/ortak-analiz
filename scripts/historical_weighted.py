"""Experimental venue and recency weighted goal rates."""
import math

def weighted_average(history, venue, index):
    recent=history[-20:]
    if not recent:
        raise ValueError("empty history")
    weights=[2**(-age/10)*(2 if row[2]==venue else 1)
             for age,row in enumerate(reversed(recent))]
    return sum(w*row[index] for w,row in zip(weights,reversed(recent)))/sum(weights)

def rates(home,away):
    if min(len(home),len(away))<5:
        return None
    clip=lambda x:max(.15,min(4,x))
    return (clip((weighted_average(home,"home",0)+weighted_average(away,"away",1))/2),
            clip((weighted_average(away,"away",0)+weighted_average(home,"home",1))/2))
