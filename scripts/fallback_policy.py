"""Conservative fallback eligibility; never authorizes predictions or settlement."""
def decide(primary_status, secondary_status, primary_count, matched_count, disagreements, independent=False):
    coverage=matched_count/primary_count if primary_count>0 and 0<=matched_count<=primary_count else None
    eligible=(independent is True and coverage is not None and primary_count>=100 and coverage>=0.95 and disagreements==0 and secondary_status=="observed")
    mode="primary" if primary_status=="observed" else ("secondary_fixture_candidate" if eligible else "unavailable")
    return dict(mode=mode,coverage=coverage,eligible=eligible,automaticFallbackEnabled=False,predictionsEnabled=False,settlementEnabled=False)
