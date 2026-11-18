from app.modules.m4_paths.rules import evaluate
from app.pipeline import calculate
def scan(id,node,at):return {"scan_id":str(id),"parcel":"01","node":node,"event_utc":at,"received_utc":"2026-11-09T00:00:00Z","zone":"Asia/Tokyo","destination":"JP","promised_hours":"24","declared_value":"200","reported":"0","_sources":[id]}
def test_real_eight_parcels(result): assert result["stages"][3]["metrics"]["parcels"]==8
def test_real_regression_isolated(result): assert result["stages"][3]["quarantine"][0]["reason"]=="PATH_REGRESSION"
def test_late_upload_event_time_decides():
    "TRAP-13"
    r=evaluate([scan(2,"DELIVERED","2026-11-04T00:00:00Z"),scan(1,"ACCEPT","2026-11-02T00:00:00Z")],{})["rows"][0]
    assert r["delivered_at"]=="2026-11-04T00:00:00Z" and r["scan_count"]==2
def test_missing_accept(): assert evaluate([scan(1,"DELIVERED","2026-11-04T00:00:00Z")],{})["quarantine"][0]["reason"]=="MISSING_ACCEPT"
def test_order_independent():
    rows=[scan(1,"ACCEPT","2026-11-02T00:00:00Z"),scan(2,"DELIVERED","2026-11-04T00:00:00Z")];assert evaluate(rows,{})==evaluate(list(reversed(rows)),{})
def test_simultaneous_conflict():
    r=evaluate([scan(1,"ACCEPT","2026-11-02T00:00:00Z"),scan(2,"DEPART","2026-11-02T00:00:00Z")],{});assert r["quarantine"][0]["reason"]=="SIMULTANEOUS_CONFLICT"
def test_real_group_lineage(result): assert all(len(r["_sources"])==4 for r in result["stages"][3]["rows"])
def test_locker_does_not_stop_clock():
    "TRAP-27 周五入柜周一取件，正式妥投按取件时刻"
    rows=[scan(1,"ACCEPT","2026-11-06T00:00:00Z"),scan(2,"POINT","2026-11-06T06:00:00Z"),scan(3,"DELIVERED","2026-11-09T01:00:00Z")]
    r=evaluate(rows,{})["rows"][0]
    assert r["delivered_at"]=="2026-11-09T01:00:00Z" and r["point_arrived_at"]=="2026-11-06T06:00:00Z"
    assert r["delivery_state"]=="已妥投" and "实际取得" in r["delivery_basis"] and "3" in r["delivery_event"]
def test_point_only_stays_in_transit():
    rows=[scan(1,"ACCEPT","2026-11-06T00:00:00Z"),scan(2,"POINT","2026-11-06T06:00:00Z")]
    r=evaluate(rows,{})["rows"][0]
    assert r["delivered_at"] is None and r["delivery_state"]=="在途" and r["point_arrived_at"]=="2026-11-06T06:00:00Z"
def test_returned_not_delivered_and_scans_kept():
    rows=[scan(1,"ACCEPT","2026-11-09T00:00:00Z"),scan(2,"POINT","2026-11-09T04:00:00Z"),scan(3,"RETURNED","2026-11-12T00:00:00Z")]
    r=evaluate(rows,{})["rows"][0]
    assert r["delivery_state"]=="退回" and r["delivered_at"] is None and r["returned_at"]=="2026-11-12T00:00:00Z"
    assert r["scan_count"]==3 and r["path"]=="ACCEPT → POINT → RETURNED" and len(r["_sources"])==3
def test_signed_then_returned_stays_delivered():
    rows=[scan(1,"ACCEPT","2026-11-09T00:00:00Z"),scan(2,"DELIVERED","2026-11-09T08:00:00Z"),scan(3,"RETURNED","2026-11-10T00:00:00Z")]
    r=evaluate(rows,{})["rows"][0]
    assert r["delivery_state"]=="已妥投" and r["delivered_at"]=="2026-11-09T08:00:00Z"
def test_event_after_return_regresses():
    rows=[scan(1,"ACCEPT","2026-11-09T00:00:00Z"),scan(2,"RETURNED","2026-11-10T00:00:00Z"),scan(3,"DELIVERED","2026-11-11T00:00:00Z")]
    r=evaluate(rows,{})
    assert r["quarantine"][0]["reason"]=="PATH_REGRESSION" and r["rows"][0]["delivery_state"]=="退回"
def test_single_conclusion_fields_present(result):
    row=result["stages"][3]["rows"][0]
    assert row["delivery_state"]=="已妥投" and row["delivery_event"] and row["delivery_basis"]
