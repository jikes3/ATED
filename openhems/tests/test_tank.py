from openhems_core.tank import horizontal_tank_volume, refill_decision


def test_horizontal_tank_empty_half_full():
    assert horizontal_tank_volume(0, 6000, 3, 1.6) == 0
    assert round(horizontal_tank_volume(0.8, 6000, 3, 1.6)) == 3000
    assert horizontal_tank_volume(1.6, 6000, 3, 1.6) == 6000


def test_refill_decision():
    assert refill_decision(5, 20, 50, 10) == "NOUZOVĚ DOPLNIT"
    assert refill_decision(15, 20, 50, 10) == "DOPLNĚNÍ DOPORUČENO"
    assert refill_decision(30, 20, 50, 10) == "SLEDOVAT"
    assert refill_decision(55, 20, 50, 10) == "NEDOPLŇOVAT"
