from record_deduplicator import RecordDeduplicator

def evaluate():
    dedup = RecordDeduplicator()
    recs = [
        {"id": "A", "email": None, "score": 10},
        {"id": "A", "email": "a@ex.com", "score": 20},
        {"id": "B", "email": "b@ex.com", "score": 30}
    ]
    res = dedup.deduplicate(recs, "id")
    assert len(res) == 2
    assert res[0]["id"] == "A"
    assert res[0]["email"] == "a@ex.com", "Merged record should adopt non-null email from 2nd record"
    assert res[0]["score"] == 10, "Existing non-null score should preserve 1st record value"
    return True
