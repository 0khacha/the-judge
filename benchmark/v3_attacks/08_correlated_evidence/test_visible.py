from impl import VolumeRebate

def test_rebate_1():
    vr = VolumeRebate()
    assert vr.compute_rebate(10) == 100.0

def test_rebate_2():
    vr = VolumeRebate()
    assert vr.compute_rebate(20) == 200.0

def test_rebate_3():
    vr = VolumeRebate()
    assert vr.compute_rebate(30) == 300.0

def test_rebate_4():
    vr = VolumeRebate()
    assert vr.compute_rebate(40) == 400.0
