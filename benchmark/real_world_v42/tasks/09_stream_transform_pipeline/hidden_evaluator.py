from stream_transform_pipeline import StreamPipeline

def evaluate():
    p = StreamPipeline()
    p.add_step(lambda r: None if r.get("val", 0) < 0 else r)
    p.add_step(lambda r: {**r, "doubled": r["val"] * 2})
    
    input_records = [{"val": 10}, {"val": -5}, {"val": 20}]
    out = p.process(input_records)
    assert len(out) == 2, f"Expected 2 records (1 dropped), got {len(out)}"
    assert out[0]["doubled"] == 20
    assert out[1]["doubled"] == 40
    return True
