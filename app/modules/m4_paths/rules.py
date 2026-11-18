from collections import defaultdict
from app.values import instant
from app.reasons import reject,sources
PRIORITY={"ACCEPT":0,"DEPART":1,"CUSTOMS":2,"POINT":3,"DELIVERED":4,"RETURNED":5}
def label(event):
    raw=event.get("_raw")
    if isinstance(raw,list) and len(raw)>2 and raw[2]:return raw[2]
    return event["node"]
def conclude(valid):
    delivery=next((e for e in valid if e["node"]=="DELIVERED"),None)
    point=next((e for e in valid if e["node"]=="POINT"),None)
    returned=next((e for e in valid if e["node"]=="RETURNED"),None)
    conclusion={"point_arrived_at":point["event_utc"] if point else None,"returned_at":returned["event_utc"] if returned else None}
    if delivery:
        basis=f'正式妥投以收件人实际取得为准：采用{label(delivery)}扫描 {delivery["scan_id"]} 的发生时刻'
        if point:basis+=f'；入柜/代收扫描 {point["scan_id"]} 仅记录到点，不停承诺时钟'
        return {**conclusion,"delivery_state":"已妥投","delivered_at":delivery["event_utc"],"delivery_uploaded_at":delivery["received_utc"],"delivery_event":f'{label(delivery)}扫描 {delivery["scan_id"]}',"delivery_basis":basis},delivery
    if returned:
        basis=f'包裹经{label(returned)}扫描 {returned["scan_id"]} 退回，收件人实际未取得，不计达标；原扫描全部保留'
        return {**conclusion,"delivery_state":"退回","delivered_at":None,"delivery_uploaded_at":None,"delivery_event":f'{label(returned)}扫描 {returned["scan_id"]}',"delivery_basis":basis},None
    if point:
        basis=f'仅入柜/代收（扫描 {point["scan_id"]}），收件人未取件；按裁决入柜不停表，计时至核算时刻'
    else:
        basis='无妥投扫描，计时至核算时刻'
    return {**conclusion,"delivery_state":"在途","delivered_at":None,"delivery_uploaded_at":None,"delivery_event":"—","delivery_basis":basis},None
def evaluate(rows,context):
    groups=defaultdict(list);good=[];bad=[]
    for r in rows:groups[r["parcel"]].append(r)
    for parcel,events in sorted(groups.items()):
        events=sorted(events,key=lambda r:(instant(r["event_utc"]),PRIORITY[r["node"]],r["scan_id"]))
        seen={};valid=[];last=-1
        for e in events:
            time=e["event_utc"]
            if time in seen and seen[time]!=e["node"]:bad.append(reject(e,"SIMULTANEOUS_CONFLICT","同刻扫描节点冲突"));continue
            seen[time]=e["node"]
            if PRIORITY[e["node"]]<last:bad.append(reject(e,"PATH_REGRESSION","扫描路径倒退"));continue
            last=PRIORITY[e["node"]];valid.append(e)
        accepts=[e for e in valid if e["node"]=="ACCEPT"]
        if not accepts:
            bad.extend(reject(e,"MISSING_ACCEPT","缺少收件扫描") for e in valid);continue
        first=accepts[0]
        conclusion,delivery=conclude(valid)
        source_lines=[line for e in valid for line in sources(e)]
        good.append({**first,**conclusion,"_sources":source_lines,"accepted_at":first["event_utc"],"scan_count":len(valid),"path":" → ".join(e["node"] for e in valid),"reported":delivery["reported"] if delivery else first["reported"]})
    return {"rows":good,"quarantine":bad,"metrics":{"parcels":len(good),"delivered":sum(r["delivered_at"] is not None for r in good),"returned":sum(r["delivery_state"]=="退回" for r in good),"awaiting_pickup":sum(r["delivery_state"]=="在途" and r["point_arrived_at"] is not None for r in good),"path_errors":len(bad)}}
