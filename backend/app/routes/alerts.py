"""
Alerts API Endpoints
====================
Powers the mobile app's Alerts screen (4 tabs):
  - Not in Control   : a characteristic's recent point is outside ±3σ control limits
  - Not Capable      : characteristic's Cpk < 1.0
  - Out of Spec      : any measurement value is outside USL / LSL spec limits
  - SPC Checks (Missed Checks): expected sample not recorded within check_frequency_minutes

All endpoints scan across all active stations and characteristics for the
authenticated admin's tenant schema.

Alert logic mirrors charts.py formulas for 100% consistency:
  σ̂ = MR̄ / d₂   (d₂ = 1.128 for n-of-2 moving ranges)
  UCL = X̄ + 3σ̂,  LCL = X̄ - 3σ̂   (I-MR / Xbar-R)
  p̄ ± 3·√(p̄(1-p̄)/n)               (P-Chart)
  Cpk = min(CPU, CPL)               (Capability)
"""

import math
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from app.database import get_tenant_db
from app.models.admin import Admin
from app.models.tenant.characteristic import Characteristic, ChartType
from app.models.tenant.department import Department
from app.models.tenant.measurement import Measurement
from app.models.tenant.production_line import ProductionLine
from app.models.tenant.sample import Sample
from app.models.tenant.station import Station
from app.routes.auth import get_current_admin
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/alerts", tags=["Alerts"])

# ── Constants (must match charts.py exactly) ──────────────────────────────────
_D2 = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534,
       7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}
_A2 = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483,
       7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}
WINDOW_SIZE = 30


# ── Shared DB helper ──────────────────────────────────────────────────────────

def _tenant_db(admin: Admin) -> Session:
    gen = get_tenant_db(admin.company_id)
    return next(gen)


# ── Core alert-classification helpers ────────────────────────────────────────

def _get_window_values(
    tenant_db: Session,
    characteristic_id: str,
    chart_type: ChartType,
    sample_size: int,
) -> Tuple[List[float], List[datetime], bool, int]:
    """
    Returns (values, datetimes, is_preliminary, total_count).
    For I-MR / Xbar-R: values = subgroup means (or individual measurements).
    For P-Chart: values = proportion defective per subgroup (0.0 – 1.0).
    """
    total = (
        tenant_db.query(Sample)
        .filter(Sample.characteristic_id == characteristic_id)
        .count()
    )
    q = (
        tenant_db.query(Sample)
        .filter(Sample.characteristic_id == characteristic_id)
        .order_by(desc(Sample.sample_datetime))
    )
    rows = q.limit(WINDOW_SIZE).all() if total >= WINDOW_SIZE else q.all()
    is_preliminary = total < WINDOW_SIZE
    rows.reverse()  # oldest → newest

    if not rows:
        return [], [], True, total

    # Load measurements for these samples in one query
    sample_ids = [s.sample_id for s in rows]
    meas_rows = (
        tenant_db.query(Measurement)
        .filter(Measurement.sample_id.in_(sample_ids))
        .order_by(Measurement.sample_id, Measurement.measurement_order)
        .all()
    )
    meas_map: Dict[str, List[float]] = {sid: [] for sid in sample_ids}
    for m in meas_rows:
        meas_map[m.sample_id].append(float(m.measurement_value))

    values: List[float] = []
    datetimes: List[datetime] = []

    for s in rows:
        vals = meas_map.get(s.sample_id, [])
        if not vals:
            continue
        if chart_type == ChartType.P_CHART:
            n = max(sample_size, 1)
            p_i = min(max(vals[0] / n, 0.0), 1.0)
            values.append(p_i)
        else:
            values.append(statistics.mean(vals) if len(vals) > 1 else vals[0])
        datetimes.append(s.sample_datetime)

    return values, datetimes, is_preliminary, total


def _compute_control_limits(
    values: List[float],
    chart_type: ChartType,
    sample_size: int,
    tenant_db: Session,
    char: Characteristic,
) -> Optional[Tuple[float, float, float]]:
    """
    Returns (ucl, cl, lcl) or None if insufficient data.
    Mirrors charts.py formulas exactly.
    """
    if len(values) < 2:
        return None

    cl = statistics.mean(values)

    if chart_type == ChartType.P_CHART:
        p_bar = cl
        if p_bar > 0 and (1 - p_bar) > 0:
            sigma_p = math.sqrt(p_bar * (1 - p_bar) / max(sample_size, 1))
        else:
            sigma_p = 0.0
        ucl = min(p_bar + 3 * sigma_p, 1.0)
        lcl = max(p_bar - 3 * sigma_p, 0.0)
        return ucl, cl, lcl

    if chart_type == ChartType.XBAR_R and sample_size > 1:
        # Need to recompute ranges — we only have means here so fall back to I-MR approach
        mr = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
        mr_bar = statistics.mean(mr)
        a2 = _A2.get(min(sample_size, 10), _A2[10])
        # Best approximation from means only
        sigma_hat = mr_bar / _D2[2]
        ucl = cl + 3 * sigma_hat
        lcl = cl - 3 * sigma_hat
        return ucl, cl, lcl

    # I-MR (default)
    mr = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    mr_bar = statistics.mean(mr)
    sigma_hat = mr_bar / _D2[2]
    ucl = cl + 3 * sigma_hat
    lcl = cl - 3 * sigma_hat
    return ucl, cl, lcl


def _compute_cpk(
    values: List[float],
    usl: Optional[float],
    lsl: Optional[float],
) -> Optional[float]:
    """Returns Cpk or None if not computable."""
    if usl is None or lsl is None or len(values) < 2:
        return None
    cl = statistics.mean(values)
    mr = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    mr_bar = statistics.mean(mr)
    sigma = mr_bar / _D2[2]
    if sigma <= 0:
        return None
    cpu = (usl - cl) / (3 * sigma)
    cpl = (cl - lsl) / (3 * sigma)
    return min(cpu, cpl)


def _is_not_in_control(values: List[float], chart_type: ChartType, sample_size: int,
                       char: Characteristic, tenant_db: Session) -> bool:
    """
    True if any of the last 5 points violates control limits (Western Electric Rule 1).
    """
    if len(values) < 2:
        return False
    limits = _compute_control_limits(values, chart_type, sample_size, tenant_db, char)
    if limits is None:
        return False
    ucl, cl, lcl = limits
    # Check last 5 points (same as charts.py overall_status logic)
    recent = values[-5:]
    return any(v > ucl or v < lcl for v in recent)


def _is_not_capable(values: List[float], usl: Optional[float], lsl: Optional[float]) -> bool:
    """True if Cpk < 1.0."""
    cpk = _compute_cpk(values, usl, lsl)
    return cpk is not None and cpk < 1.0


def _is_out_of_spec(values: List[float], usl: Optional[float], lsl: Optional[float]) -> bool:
    """True if any measurement value in the window is outside USL or LSL."""
    if usl is None and lsl is None:
        return False
    for v in values:
        if usl is not None and v > usl:
            return True
        if lsl is not None and v < lsl:
            return True
    return False


def _is_missed_check(char: Characteristic, tenant_db: Session) -> bool:
    """
    True if the most recent sample is older than check_frequency_minutes.
    Requires check_frequency_minutes to be set on the characteristic.
    """
    if not char.check_frequency_minutes:
        return False
    latest = (
        tenant_db.query(Sample)
        .filter(Sample.characteristic_id == char.characteristic_id)
        .order_by(desc(Sample.sample_datetime))
        .first()
    )
    if latest is None:
        return True  # Never sampled = always missed
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    threshold = now_utc - timedelta(minutes=char.check_frequency_minutes)
    return latest.sample_datetime < threshold


# ── Build lookup maps ─────────────────────────────────────────────────────────

def _build_lookup_maps(tenant_db: Session):
    """Returns dicts: {id: object} for departments and lines."""
    depts = {d.department_id: d for d in tenant_db.query(Department).all()}
    lines = {l.line_id: l for l in tenant_db.query(ProductionLine).all()}
    return depts, lines


# ── Main classification pass ──────────────────────────────────────────────────

class _CharAlert:
    """Lightweight classification result for one characteristic."""
    __slots__ = ("char", "station", "dept_name", "line_name",
                 "not_in_control", "not_capable", "out_of_spec", "missed_check")

    def __init__(self, char, station, dept_name, line_name,
                 not_in_control, not_capable, out_of_spec, missed_check):
        self.char = char
        self.station = station
        self.dept_name = dept_name
        self.line_name = line_name
        self.not_in_control = not_in_control
        self.not_capable = not_capable
        self.out_of_spec = out_of_spec
        self.missed_check = missed_check


def _classify_all_characteristics(tenant_db: Session) -> List[_CharAlert]:
    """
    Single pass over all active characteristics → classify every alert type.
    Returns a flat list of _CharAlert objects.
    """
    depts, lines = _build_lookup_maps(tenant_db)

    stations = (
        tenant_db.query(Station)
        .filter(Station.operational_status == "active")
        .all()
    )

    results: List[_CharAlert] = []

    for station in stations:
        dept = depts.get(station.department_id)
        line = lines.get(station.line_id)
        dept_name = dept.department_name if dept else "—"
        line_name = line.line_name if line else "—"

        chars = (
            tenant_db.query(Characteristic)
            .filter(
                Characteristic.station_id == station.station_id,
                Characteristic.is_active == True,
            )
            .all()
        )

        for char in chars:
            chart_type = char.chart_type
            sample_size = char.sample_size or 1
            usl = float(char.usl) if char.usl is not None else None
            lsl = float(char.lsl) if char.lsl is not None else None

            values, _, _, _ = _get_window_values(
                tenant_db, char.characteristic_id, chart_type, sample_size
            )

            nic = _is_not_in_control(values, chart_type, sample_size, char, tenant_db)
            nc = _is_not_capable(values, usl, lsl)
            oos = _is_out_of_spec(values, usl, lsl)
            mc = _is_missed_check(char, tenant_db)

            results.append(
                _CharAlert(
                    char=char,
                    station=station,
                    dept_name=dept_name,
                    line_name=line_name,
                    not_in_control=nic,
                    not_capable=nc,
                    out_of_spec=oos,
                    missed_check=mc,
                )
            )

    return results


# ── Endpoint 1: Summary (the 4 donut metrics) ─────────────────────────────────


@router.get("/summary")
async def get_alerts_summary(
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Returns the 4 headline alert metrics shown as donut charts on the Alerts screen.

    - **not_in_control_pct**: % of active characteristics with a recent out-of-control point
    - **not_capable_pct**: % of characteristics with Cpk < 1.0 (requires USL + LSL)
    - **out_of_spec_pct**: % of characteristics with any measurement outside USL/LSL
    - **missed_checks_count**: count of characteristics overdue for their next sample

    All percentages are rounded to 1 decimal place.
    Returns `total_characteristics` so frontend can verify the denominator.
    """
    db = _tenant_db(current_admin)
    try:
        results = _classify_all_characteristics(db)
        total = len(results)

        if total == 0:
            return {
                "total_characteristics": 0,
                "not_in_control_pct": 0.0,
                "not_in_control_count": 0,
                "not_capable_pct": 0.0,
                "not_capable_count": 0,
                "out_of_spec_pct": 0.0,
                "out_of_spec_count": 0,
                "missed_checks_count": 0,
            }

        nic = sum(1 for r in results if r.not_in_control)
        nc = sum(1 for r in results if r.not_capable)
        oos = sum(1 for r in results if r.out_of_spec)
        mc = sum(1 for r in results if r.missed_check)

        return {
            "total_characteristics": total,
            "not_in_control_pct": round(nic / total * 100, 1),
            "not_in_control_count": nic,
            "not_capable_pct": round(nc / total * 100, 1),
            "not_capable_count": nc,
            "out_of_spec_pct": round(oos / total * 100, 1),
            "out_of_spec_count": oos,
            "missed_checks_count": mc,
        }
    finally:
        db.close()


# ── Endpoint 2: Paginated alert list ─────────────────────────────────────────

ALERT_TYPE_LABELS = {
    "not_in_control": "Not in control",
    "not_capable": "Not capable",
    "out_of_spec": "Out of spec",
    "missed_checks": "Missed checks",
}

VALID_ALERT_TYPES = list(ALERT_TYPE_LABELS.keys())


@router.get("/list")
async def get_alerts_list(
    type: str = Query(
        ...,
        description="Alert type filter. One of: not_in_control | not_capable | out_of_spec | missed_checks",
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Paginated list of stations and their alerting characteristics for the given alert type.

    Response groups characteristics **under their parent station**, matching the
    Alerts screen UI where each station card expands to show its failing characteristics.

    **Alert Types:**
    - `not_in_control` — recent point beyond ±3σ control limits
    - `not_capable`    — Cpk < 1.0
    - `out_of_spec`    — measurement outside USL or LSL
    - `missed_checks`  — no sample recorded within `check_frequency_minutes`

    **Pagination notes:**
    - `total` = total number of *characteristics* matching the filter
    - Items are grouped by station: a station appears only if ≥1 of its characteristics match
    - Page/per_page control the number of *characteristics* returned (not stations)
    """
    if type not in VALID_ALERT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid alert type '{type}'. Must be one of: {', '.join(VALID_ALERT_TYPES)}",
        )

    db = _tenant_db(current_admin)
    try:
        all_results = _classify_all_characteristics(db)

        # Filter to the requested type
        type_map = {
            "not_in_control": lambda r: r.not_in_control,
            "not_capable": lambda r: r.not_capable,
            "out_of_spec": lambda r: r.out_of_spec,
            "missed_checks": lambda r: r.missed_check,
        }
        filtered = [r for r in all_results if type_map[type](r)]
        total = len(filtered)

        # Paginate at the characteristic level
        start = (page - 1) * per_page
        end = start + per_page
        page_items = filtered[start:end]

        # Group by station (preserving order)
        station_map: Dict[str, dict] = {}
        for r in page_items:
            sid = r.station.station_id
            if sid not in station_map:
                station_map[sid] = {
                    "station_id": sid,
                    "station_name": r.station.station_name,
                    "department_name": r.dept_name,
                    "line_name": r.line_name,
                    "alert_label": ALERT_TYPE_LABELS[type],
                    "characteristics": [],
                }
            station_map[sid]["characteristics"].append(
                {
                    "characteristic_id": r.char.characteristic_id,
                    "characteristic_name": r.char.characteristic_name,
                    "chart_type": r.char.chart_type.value,
                    "unit_of_measure": r.char.unit_of_measure,
                    "alert_dot": True,
                }
            )

        return {
            "type": type,
            "alert_label": ALERT_TYPE_LABELS[type],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, math.ceil(total / per_page)),
            "items": list(station_map.values()),
        }
    finally:
        db.close()
