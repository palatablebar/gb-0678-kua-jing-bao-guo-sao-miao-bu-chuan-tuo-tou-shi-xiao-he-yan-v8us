import pytest
from app.pipeline import calculate,load_sample
@pytest.fixture(scope="module")
def lastmile(): return calculate(load_sample("lastmile.csv"))
def rows_by_parcel(rows): return {r["parcel"]:r for r in rows}
def test_friday_locker_monday_pickup(lastmile):
    "周五入柜、周一取件：正式妥投按取件时刻，按入柜会达标"
    r=rows_by_parcel(lastmile["stages"][3]["rows"])["L001"]
    assert r["delivery_state"]=="已妥投" and r["delivered_at"]=="2026-11-09T01:00:00+00:00" and r["point_arrived_at"]=="2026-11-06T06:00:00+00:00"
    timed=rows_by_parcel(lastmile["stages"][4]["rows"])["L001"]
    assert timed["sla"]=="超时" and timed["expected"]=="17.00"
def test_proxy_sign_on_time(lastmile):
    r=rows_by_parcel(lastmile["stages"][4]["rows"])["L002"]
    assert r["delivery_state"]=="已妥投" and r["sla"]=="达标"
def test_returned_not_on_time_scans_kept(lastmile):
    r=rows_by_parcel(lastmile["stages"][3]["rows"])["L003"]
    assert r["delivery_state"]=="退回" and r["delivered_at"] is None and r["path"]=="ACCEPT → POINT → RETURNED" and r["scan_count"]==3
    timed=rows_by_parcel(lastmile["stages"][4]["rows"])["L003"]
    assert timed["sla"]=="退回" and timed["expected"]=="0.00"
def test_metrics_and_balance(lastmile):
    m4=lastmile["stages"][3]["metrics"];assert (m4["parcels"],m4["delivered"],m4["returned"])==(5,3,1)
    m5=lastmile["stages"][4]["metrics"];assert (m5["late_parcels"],m5["returned_parcels"],m5["compensation"])==(2,1,"37.00")
    assert lastmile["stages"][5]["metrics"]["balanced"] is True and lastmile["stages"][6]["metrics"]["ready"] is True
def test_compensation_and_archive_read_conclusion(lastmile):
    "赔付与归档只读唯一妥投结论"
    timed=rows_by_parcel(lastmile["stages"][4]["rows"])
    books=rows_by_parcel(lastmile["stages"][5]["rows"]);sealed=rows_by_parcel(lastmile["stages"][6]["rows"])
    for parcel in ("L001","L002","L003","L004","L005"):
        assert books[parcel]["sla"]==timed[parcel]["sla"]==sealed[parcel]["sla"]
        assert books[parcel]["expected"]==timed[parcel]["expected"]==sealed[parcel]["expected"]
        assert sealed[parcel]["delivery_state"]==timed[parcel]["delivery_state"]
def test_basis_recorded(lastmile):
    for r in lastmile["stages"][3]["rows"]:
        assert r["delivery_event"] and r["delivery_basis"]
