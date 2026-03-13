"""
SPC Chart data endpoints
========================
All chart endpoints follow the **30-sample window rule**:
  - If total samples for a characteristic  < 30  → use ALL available  (preliminary limits)
  - If total samples for a characteristic >= 30  → use LAST 30 only

Control limits (UCL / CL / LCL) are ALWAYS computed dynamically from the window.
They are intentionally NOT stored on the Characteristic row so they stay current.

Supported chart types (matches Characteristic.chart_type):
  - I-MR   → I-Chart + MR-Chart (individual measurements, sample_size = 1)
  - Xbar-R → Xbar-Chart + R-Chart (subgroup means/ranges, sample_size > 1)
  - P-Chart → Proportion defective chart (attribute data, measurement_value = defect count)

All three tabs visible in the mobile app always call their endpoint; non-applicable
types return {"applicable": false} so the frontend can show "N/A" state.
Cpk Histogram is always applicable for any characteristic with spec limits.
"""

import math
import statistics
import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.database import get_tenant_db
from app.models.admin import Admin
from app.models.tenant.characteristic import Characteristic, ChartType
from app.models.tenant.department import Department
from app.models.tenant.measurement import Measurement
from app.models.tenant.product_model import ProductModel
from app.models.tenant.production_line import ProductionLine
from app.models.tenant.sample import Sample
from app.models.tenant.station import Station
from app.routes.auth import get_current_admin
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/charts", tags=["SPC Charts"])

# ── SPC control-chart constants ──────────────────────────────────────────────

# d2: expected moving-range bias-correction constant for subgroup size n
_D2 = {
    2: 1.128,
    3: 1.693,
    4: 2.059,
    5: 2.326,
    6: 2.534,
    7: 2.704,
    8: 2.847,
    9: 2.970,
    10: 3.078,
}

# D3, D4: LCL / UCL factors for the MR-chart by subgroup size
_D3 = {
    2: 0.000,
    3: 0.000,
    4: 0.000,
    5: 0.000,
    6: 0.000,
    7: 0.076,
    8: 0.136,
    9: 0.184,
    10: 0.223,
}
_D4 = {
    2: 3.267,
    3: 2.574,
    4: 2.282,
    5: 2.115,
    6: 2.004,
    7: 1.924,
    8: 1.864,
    9: 1.816,
    10: 1.777,
}

# A2: Xbar-R UCL/LCL multiplier by subgroup size
_A2 = {
    2: 1.880,
    3: 1.023,
    4: 0.729,
    5: 0.577,
    6: 0.483,
    7: 0.419,
    8: 0.373,
    9: 0.337,
    10: 0.308,
}

WINDOW_SIZE = 30


# ── Helpers ─────────────────────────────────────────────────────────────────


def _tenant_db(admin: Admin) -> Session:
    gen = get_tenant_db(admin.company_id)
    return next(gen)


def _norm_cdf(x: float, mean: float, std: float) -> float:
    """Cumulative normal distribution — uses math.erf, no scipy needed."""
    if std <= 0:
        return 0.0 if x < mean else 1.0
    return 0.5 * (1.0 + math.erf((x - mean) / (std * math.sqrt(2.0))))


def _norm_pdf(x: float, mean: float, std: float) -> float:
    if std <= 0:
        return 0.0
    return (1.0 / (std * math.sqrt(2.0 * math.pi))) * math.exp(
        -0.5 * ((x - mean) / std) ** 2
    )


def _get_window(
    tenant_db: Session, characteristic_id: str, target_date: Optional[str] = None
) -> Tuple[List[Sample], bool, int]:
    """
    Returns (window_samples_oldest_first, is_preliminary, total_count).
    If target_date is provided (YYYY-MM-DD), returns all samples for that date.
    Else window = last WINDOW_SIZE if total >= WINDOW_SIZE, else all.
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

    if target_date:
        # Filter strictly by the requested date
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
            q = q.filter(
                Sample.sample_datetime >= target_dt,
                Sample.sample_datetime < target_dt + datetime.timedelta(days=1)
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Expected YYYY-MM-DD."
            )
        rows = q.all()
        is_preliminary = False # When showing history, we just show all points for that day
    elif total >= WINDOW_SIZE:
        rows = q.limit(WINDOW_SIZE).all()
        is_preliminary = False
    else:
        rows = q.all()
        is_preliminary = True

    rows.reverse()  # oldest → newest
    return rows, is_preliminary, total


def _measurements_by_sample(
    tenant_db: Session, sample_ids: List[str]
) -> Dict[str, List[float]]:
    if not sample_ids:
        return {}
    rows = (
        tenant_db.query(Measurement)
        .filter(Measurement.sample_id.in_(sample_ids))
        .order_by(Measurement.sample_id, Measurement.measurement_order)
        .all()
    )
    result: Dict[str, List[float]] = {sid: [] for sid in sample_ids}
    for m in rows:
        result[m.sample_id].append(float(m.measurement_value))
    return result


def _rule1_violated(value: float, ucl: float, lcl: float) -> bool:
    """Western Electric Rule 1: point beyond ±3σ limits."""
    return value > ucl or value < lcl


def _fmt_datetime(dt: datetime) -> dict:
    return {
        "date_label": dt.strftime("%-m/%-d/%y") if hasattr(dt, "strftime") else str(dt),
        "time_label": dt.strftime("%-I:%M %p") if hasattr(dt, "strftime") else str(dt),
        "iso": dt.isoformat(),
    }


def _verify_station_ownership(
    tenant_db: Session, station_id: str, characteristic_id: str
):
    """Raise 404 if station or characteristic don't exist / aren't related."""
    char = (
        tenant_db.query(Characteristic)
        .filter(
            Characteristic.characteristic_id == characteristic_id,
            Characteristic.station_id == station_id,
            Characteristic.is_active == True,
        )
        .first()
    )
    if not char:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Characteristic not found for this station.",
        )
    return char


# ── I-Chart endpoint ─────────────────────────────────────────────────────────


@router.get("/station/{station_id}/characteristic/{characteristic_id}/ichart")
async def get_ichart(
    station_id: str,
    characteristic_id: str,
    date: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    I-Chart (Individuals Chart) for I-MR characteristics.
    Also works for Xbar-R: plots subgroup means instead of individual values.

    Window: last 30 samples if ≥30 total, else all (preliminary).

    UCL / CL / LCL are computed from data:
      - I-MR:   CL = X̄,  MR̄ = mean(|Xᵢ - Xᵢ₋₁|),  UCL = X̄ + 3·(MR̄/d₂)
      - Xbar-R: CL = X̄̄,  R̄  = mean(ranges),          UCL = X̄̄ + A₂·R̄
    """
    db = _tenant_db(current_admin)
    try:
        char = _verify_station_ownership(db, station_id, characteristic_id)

        samples, is_preliminary, total = _get_window(db, characteristic_id, target_date=date)
        if not samples:
            return _empty_chart_response(char, "ichart")

        sample_ids = [s.sample_id for s in samples]
        meas_map = _measurements_by_sample(db, sample_ids)

        # Build per-sample values (individual or subgroup mean)
        values: List[float] = []
        for s in samples:
            vals = meas_map.get(s.sample_id, [])
            if not vals:
                continue
            values.append(statistics.mean(vals) if len(vals) > 1 else vals[0])

        if not values:
            return _empty_chart_response(char, "ichart")

        # Compute control limits
        cl = statistics.mean(values)
        n = char.sample_size or 1
        limits: Optional[dict] = None

        if char.chart_type == ChartType.XBAR_R and n > 1:
            # Xbar-R: use ranges
            ranges = []
            for s in samples:
                vals = meas_map.get(s.sample_id, [])
                if len(vals) > 1:
                    ranges.append(max(vals) - min(vals))
            if ranges:
                r_bar = statistics.mean(ranges)
                a2 = _A2.get(min(n, 10), _A2[10])
                ucl = cl + a2 * r_bar
                lcl = cl - a2 * r_bar
                limits = {"ucl": ucl, "cl": cl, "lcl": lcl, "r_bar": r_bar}
        else:
            # I-MR: use moving ranges
            if len(values) >= 2:
                mr = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
                mr_bar = statistics.mean(mr)
                d2 = _D2[2]  # MR uses pairs (n=2)
                sigma_hat = mr_bar / d2
                ucl = cl + 3 * sigma_hat
                lcl = cl - 3 * sigma_hat
                limits = {
                    "ucl": ucl,
                    "cl": cl,
                    "lcl": lcl,
                    "sigma_hat": sigma_hat,
                    "mr_bar": mr_bar,
                }

        # Build data points
        points = []
        for i, (s, value) in enumerate(zip(samples, values), start=1):
            in_ctrl = True
            rules = []
            if limits:
                if _rule1_violated(value, limits["ucl"], limits["lcl"]):
                    in_ctrl = False
                    rules.append("Rule 1: Beyond 3\u03c3 limits")
            dt_info = _fmt_datetime(s.sample_datetime)
            points.append(
                {
                    "x": i,
                    "y": round(value, 6),
                    "sample_id": s.sample_id,
                    "sample_datetime": dt_info["iso"],
                    "date_label": dt_info["date_label"],
                    "time_label": dt_info["time_label"],
                    "is_in_control": in_ctrl,
                    "rules_violated": rules,
                }
            )

        # Latest point info for the summary panel
        latest_pt = points[-1]
        latest_summary = {
            "date_label": latest_pt["date_label"],
            "time_label": latest_pt["time_label"],
            "actual": latest_pt["y"],
            "avg": round(cl, 6) if limits else None,
            "usl": float(char.usl) if char.usl is not None else None,
            "lsl": float(char.lsl) if char.lsl is not None else None,
            "ucl": round(limits["ucl"], 6) if limits else None,
            "lcl": round(limits["lcl"], 6) if limits else None,
        }

        overall_status = (
            "not_in_control"
            if any(not p["is_in_control"] for p in points[-5:])
            else "in_control"
        )

        return {
            "applicable": True,
            "characteristic": _char_info(char),
            "chart_data": {
                "points": points,
                **(
                    {
                        "ucl": round(limits["ucl"], 6),
                        "cl": round(limits["cl"], 6),
                        "lcl": round(limits["lcl"], 6),
                    }
                    if limits
                    else {"ucl": None, "cl": None, "lcl": None}
                ),
                "usl": float(char.usl) if char.usl is not None else None,
                "lsl": float(char.lsl) if char.lsl is not None else None,
            },
            "window": {
                "size": len(values),
                "is_preliminary": is_preliminary,
                "total_samples": total,
            },
            "latest_sample": latest_summary,
            "status": overall_status,
        }
    finally:
        db.close()


# ── MR-Chart endpoint ────────────────────────────────────────────────────────


@router.get("/station/{station_id}/characteristic/{characteristic_id}/mr-chart")
async def get_mr_chart(
    station_id: str,
    characteristic_id: str,
    date: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Moving-Range Chart (companion to I-Chart for I-MR characteristics).
    For Xbar-R, this returns the R-Chart (subgroup range chart).

    UCL_MR = D₄ · MR̄  (D₄ = 3.267 for n=2)
    CL_MR  = MR̄
    LCL_MR = 0         (D₃ = 0 for n ≤ 6)
    """
    db = _tenant_db(current_admin)
    try:
        char = _verify_station_ownership(db, station_id, characteristic_id)

        samples, is_preliminary, total = _get_window(db, characteristic_id, target_date=date)
        if len(samples) < 2:
            return _empty_chart_response(char, "mr-chart")

        sample_ids = [s.sample_id for s in samples]
        meas_map = _measurements_by_sample(db, sample_ids)

        values = []
        for s in samples:
            vals = meas_map.get(s.sample_id, [])
            if vals:
                values.append(statistics.mean(vals) if len(vals) > 1 else vals[0])

        is_xbar_r = char.chart_type == ChartType.XBAR_R and (char.sample_size or 1) > 1

        if is_xbar_r:
            # R-Chart: ranges per subgroup
            range_values = []
            range_samples = []
            for s in samples:
                vals = meas_map.get(s.sample_id, [])
                if len(vals) > 1:
                    range_values.append(max(vals) - min(vals))
                    range_samples.append(s)
            if not range_values:
                return _empty_chart_response(char, "mr-chart")
            r_bar = statistics.mean(range_values)
            n = min(char.sample_size or 2, 10)
            ucl_mr = _D4.get(n, _D4[10]) * r_bar
            lcl_mr = max(0.0, _D3.get(n, 0.0) * r_bar)
            mr_series = range_values
            mr_samples = range_samples
            label = "R (Range)"
        else:
            # MR-Chart: consecutive moving ranges
            if len(values) < 2:
                return _empty_chart_response(char, "mr-chart")
            mr_series = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
            mr_samples = samples[1:]
            mr_bar = statistics.mean(mr_series)
            ucl_mr = _D4[2] * mr_bar
            lcl_mr = 0.0
            r_bar = mr_bar
            label = "MR (Moving Range)"

        points = []
        for i, (s, mr_val) in enumerate(zip(mr_samples, mr_series), start=2):
            in_ctrl = mr_val <= ucl_mr
            dt_info = _fmt_datetime(s.sample_datetime)
            points.append(
                {
                    "x": i,
                    "y": round(mr_val, 6),
                    "sample_id": s.sample_id,
                    "date_label": dt_info["date_label"],
                    "time_label": dt_info["time_label"],
                    "is_in_control": in_ctrl,
                }
            )

        return {
            "applicable": True,
            "chart_label": label,
            "characteristic": _char_info(char),
            "chart_data": {
                "points": points,
                "ucl": round(ucl_mr, 6),
                "cl": round(r_bar, 6),
                "lcl": round(lcl_mr, 6),
            },
            "window": {
                "size": len(mr_series),
                "is_preliminary": is_preliminary,
                "total_samples": total,
            },
        }
    finally:
        db.close()


# ── P-Chart endpoint ─────────────────────────────────────────────────────────


@router.get("/station/{station_id}/characteristic/{characteristic_id}/pchart")
async def get_pchart(
    station_id: str,
    characteristic_id: str,
    date: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    P-Chart (proportion defective) for P-Chart characteristics.

    Each Sample must have exactly ONE Measurement where
      measurement_value = count of defectives in that subgroup.
    The subgroup size (n) comes from Characteristic.sample_size.

      p̄  = Σ(defectives) / (n_subgroups × n)
      UCL = p̄ + 3 · √(p̄(1−p̄)/n)
      LCL = max(0, p̄ − 3 · √(p̄(1−p̄)/n))
    """
    db = _tenant_db(current_admin)
    try:
        char = _verify_station_ownership(db, station_id, characteristic_id)

        samples, is_preliminary, total = _get_window(db, characteristic_id, target_date=date)
        if not samples:
            return _empty_chart_response(char, "pchart")

        sample_ids = [s.sample_id for s in samples]
        meas_map = _measurements_by_sample(db, sample_ids)

        n = char.sample_size or 1  # subgroup size
        p_values: List[float] = []
        defect_counts: List[float] = []
        valid_samples: List[Sample] = []

        for s in samples:
            vals = meas_map.get(s.sample_id, [])
            if not vals:
                continue
            defects = vals[0]  # Measurement = defect count
            p_i = min(max(defects / n, 0.0), 1.0)
            p_values.append(p_i)
            defect_counts.append(defects)
            valid_samples.append(s)

        if not p_values:
            return _empty_chart_response(char, "pchart")

        p_bar = statistics.mean(p_values)
        if p_bar > 0 and (1 - p_bar) > 0:
            sigma_p = math.sqrt(p_bar * (1 - p_bar) / n)
        else:
            sigma_p = 0.0
        ucl = min(p_bar + 3 * sigma_p, 1.0)
        lcl = max(p_bar - 3 * sigma_p, 0.0)

        points = []
        for i, (s, p_i, defects) in enumerate(
            zip(valid_samples, p_values, defect_counts), start=1
        ):
            in_ctrl = lcl <= p_i <= ucl
            dt_info = _fmt_datetime(s.sample_datetime)
            points.append(
                {
                    "x": i,
                    "y": round(p_i * 100, 2),  # % for display
                    "y_raw": round(p_i, 6),  # proportion 0–1
                    "defect_count": int(defects),
                    "subgroup_size": n,
                    "sample_id": s.sample_id,
                    "date_label": dt_info["date_label"],
                    "time_label": dt_info["time_label"],
                    "is_in_control": in_ctrl,
                }
            )

        latest_pt = points[-1]
        latest_summary = {
            "date_label": latest_pt["date_label"],
            "time_label": latest_pt["time_label"],
            "reports_pct": latest_pt["y"],
            "subgroup_size": n,
            "ucl_pct": round(ucl * 100, 2),
            "lcl_pct": round(lcl * 100, 2),
        }
        overall_status = (
            "not_in_control"
            if any(not p["is_in_control"] for p in points[-5:])
            else "in_control"
        )

        return {
            "applicable": True,
            "characteristic": _char_info(char),
            "chart_data": {
                "points": points,
                "ucl_pct": round(ucl * 100, 2),
                "cl_pct": round(p_bar * 100, 2),
                "lcl_pct": round(lcl * 100, 2),
                "ucl": round(ucl, 6),
                "cl": round(p_bar, 6),
                "lcl": round(lcl, 6),
            },
            "window": {
                "size": len(valid_samples),
                "is_preliminary": is_preliminary,
                "total_samples": total,
            },
            "latest_sample": latest_summary,
            "status": overall_status,
        }
    finally:
        db.close()


# ── Cpk Histogram endpoint ───────────────────────────────────────────────────


@router.get("/station/{station_id}/characteristic/{characteristic_id}/cpk-histogram")
async def get_cpk_histogram(
    station_id: str,
    characteristic_id: str,
    bins: int = 20,
    date: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Cpk capability histogram for any characteristic with USL / LSL defined.

    Returns:
      - Histogram bins (count per bucket)
      - Normal-curve overlay points (PDF evaluated at each x)
      - Cpk, Cp, sigma, mean, predicted defect %
      - Capability status: "capable" (Cpk ≥ 1.33) / "marginal" (1.0–1.33) / "not_capable"

    Sigma estimated from MR-chart (consistent with I-chart limits):
      σ̂ = MR̄ / d₂
    """
    db = _tenant_db(current_admin)
    try:
        char = _verify_station_ownership(db, station_id, characteristic_id)

        if char.usl is None or char.lsl is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cpk histogram requires both USL and LSL to be set on the characteristic.",
            )

        usl = float(char.usl)
        lsl = float(char.lsl)

        samples, is_preliminary, total = _get_window(db, characteristic_id, target_date=date)
        if not samples:
            return _empty_chart_response(char, "cpk-histogram")

        sample_ids = [s.sample_id for s in samples]
        meas_map = _measurements_by_sample(db, sample_ids)

        # Collect individual measurements (all readings, not subgroup means)
        all_values: List[float] = []
        for s in samples:
            vals = meas_map.get(s.sample_id, [])
            all_values.extend(vals)

        if len(all_values) < 2:
            return _empty_chart_response(char, "cpk-histogram")

        mean_val = statistics.mean(all_values)
        # Estimate sigma via moving ranges (same estimator as I-chart)
        # Use sorted order of measurement collection for MR
        sample_means = []
        for s in samples:
            vals = meas_map.get(s.sample_id, [])
            if vals:
                sample_means.append(statistics.mean(vals) if len(vals) > 1 else vals[0])

        if len(sample_means) >= 2:
            mr = [
                abs(sample_means[i] - sample_means[i - 1])
                for i in range(1, len(sample_means))
            ]
            mr_bar = statistics.mean(mr)
            sigma = mr_bar / _D2[2]
        else:
            # Fallback: sample std dev
            sigma = statistics.stdev(all_values) if len(all_values) >= 2 else 0.0

        # Cp and Cpk
        spec_width = usl - lsl
        cp = spec_width / (6 * sigma) if sigma > 0 else None
        cpu = (usl - mean_val) / (3 * sigma) if sigma > 0 else None
        cpl = (mean_val - lsl) / (3 * sigma) if sigma > 0 else None
        cpk = min(cpu, cpl) if (cpu is not None and cpl is not None) else None

        # Predicted defect rate
        if sigma > 0:
            p_above = 1.0 - _norm_cdf(usl, mean_val, sigma)
            p_below = _norm_cdf(lsl, mean_val, sigma)
            predicted_defects_pct = (p_above + p_below) * 100.0
        else:
            predicted_defects_pct = 0.0

        # Capability status
        if cpk is None:
            capability_status = "no_data"
        elif cpk >= 1.33:
            capability_status = "capable"
        elif cpk >= 1.0:
            capability_status = "marginal"
        else:
            capability_status = "not_capable"

        # Histogram bins
        min_val = min(all_values)
        max_val = max(all_values)
        # Extend range slightly so spec limits are visible
        plot_min = min(min_val, lsl) - abs(spec_width) * 0.1
        plot_max = max(max_val, usl) + abs(spec_width) * 0.1
        bin_width = (plot_max - plot_min) / bins if bins > 0 else (plot_max - plot_min)

        bin_edges = [plot_min + i * bin_width for i in range(bins + 1)]
        bin_counts = [0] * bins
        for v in all_values:
            idx = int((v - plot_min) / bin_width)
            idx = max(0, min(idx, bins - 1))
            bin_counts[idx] += 1

        histogram = [
            {
                "lower": round(bin_edges[i], 8),
                "upper": round(bin_edges[i + 1], 8),
                "mid": round((bin_edges[i] + bin_edges[i + 1]) / 2, 8),
                "count": bin_counts[i],
            }
            for i in range(bins)
        ]

        # Normal curve overlay — 60 points across plot range
        curve_n = 60
        curve_step = (plot_max - plot_min) / curve_n
        normal_curve = []
        for i in range(curve_n + 1):
            x = plot_min + i * curve_step
            # Scale PDF to histogram counts (area = total measurements × bin_width)
            y_pdf = _norm_pdf(x, mean_val, sigma) * len(all_values) * bin_width
            normal_curve.append({"x": round(x, 8), "y": round(y_pdf, 4)})

        return {
            "applicable": True,
            "characteristic": _char_info(char),
            "stats": {
                "cpk": round(cpk, 4) if cpk is not None else None,
                "cp": round(cp, 4) if cp is not None else None,
                "cpu": round(cpu, 4) if cpu is not None else None,
                "cpl": round(cpl, 4) if cpl is not None else None,
                "mean": round(mean_val, 6),
                "std_dev": round(sigma, 6),
                "predicted_defects_pct": round(predicted_defects_pct, 4),
                "samples_used": len(samples),
                "measurements_used": len(all_values),
                "capability_status": capability_status,
            },
            "histogram": histogram,
            "normal_curve": normal_curve,
            "spec_limits": {"usl": usl, "lsl": lsl},
            "window": {
                "size": len(samples),
                "is_preliminary": is_preliminary,
                "total_samples": total,
            },
        }
    finally:
        db.close()


# ── Summary endpoint ─────────────────────────────────────────────────────────


@router.get("/station/{station_id}/characteristic/{characteristic_id}/summary")
async def get_chart_summary(
    station_id: str,
    characteristic_id: str,
    date: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Lightweight summary for the station card header:
    latest sample status, Cpk, and sample count.
    Avoids loading full chart payload when only the badge/status is needed.
    """
    db = _tenant_db(current_admin)
    try:
        char = _verify_station_ownership(db, station_id, characteristic_id)

        samples, is_preliminary, total = _get_window(db, characteristic_id, target_date=date)
        if not samples:
            return {
                "characteristic": _char_info(char),
                "status": "no_data",
                "cpk": None,
                "total_samples": 0,
                "is_preliminary": True,
            }

        sample_ids = [s.sample_id for s in samples]
        meas_map = _measurements_by_sample(db, sample_ids)

        values = []
        for s in samples:
            vals = meas_map.get(s.sample_id, [])
            if vals:
                values.append(statistics.mean(vals) if len(vals) > 1 else vals[0])

        if len(values) < 2:
            return {
                "characteristic": _char_info(char),
                "status": "insufficient_data",
                "cpk": None,
                "total_samples": total,
                "is_preliminary": True,
            }

        cl = statistics.mean(values)
        mr = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
        mr_bar = statistics.mean(mr)
        sigma_hat = mr_bar / _D2[2]
        ucl = cl + 3 * sigma_hat
        lcl = cl - 3 * sigma_hat

        latest_val = values[-1]
        latest_in_ctrl = lcl <= latest_val <= ucl

        cpk = None
        capability_status = None
        if char.usl is not None and char.lsl is not None and sigma_hat > 0:
            cpu = (float(char.usl) - cl) / (3 * sigma_hat)
            cpl = (cl - float(char.lsl)) / (3 * sigma_hat)
            cpk = round(min(cpu, cpl), 4)
            capability_status = (
                "capable"
                if cpk >= 1.33
                else "marginal" if cpk >= 1.0 else "not_capable"
            )

        return {
            "characteristic": _char_info(char),
            "latest_value": round(latest_val, 6),
            "latest_datetime": samples[-1].sample_datetime.isoformat(),
            "status": "in_control" if latest_in_ctrl else "not_in_control",
            "cpk": cpk,
            "capability_status": capability_status,
            "total_samples": total,
            "window_size": len(values),
            "is_preliminary": is_preliminary,
        }
    finally:
        db.close()


# ── Station dropdown endpoints ───────────────────────────────────────────────

@router.get("/station/{station_id}/characteristic/{characteristic_id}/archived-dates")
async def get_archived_dates(
    station_id: str,
    characteristic_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Returns an array of dates (YYYY-MM-DD) for which this characteristic has sample data.
    Used by the mobile app's Date Picker for the "View archived dates" feature.
    Dates are sorted descending (newest first).
    """
    db = _tenant_db(current_admin)
    try:
        _verify_station_ownership(db, station_id, characteristic_id)

        # Select distinct dates from the samples table
        # Since SQLite/Postgres implementations can vary, doing it simply via ORM:
        from sqlalchemy import cast, Date
        dates_query = (
            db.query(cast(Sample.sample_datetime, Date))
            .filter(Sample.characteristic_id == characteristic_id)
            .distinct()
            .order_by(desc(cast(Sample.sample_datetime, Date)))
            .all()
        )

        dates = [str(date[0]) for date in dates_query if date[0]]
        return {
            "applicable": True,
            "archived_dates": dates
        }
    finally:
        db.close()


@router.get("/station/{station_id}/characteristics")
async def get_station_characteristics(
    station_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    List all active characteristics for a station.
    Used to populate the **Characteristic dropdown** in the mobile chart-detail screen.

    Also returns each characteristic's current SPC status
    (in_control / not_in_control / no_data) so the app can show a colored dot
    next to each item in the dropdown.

    The header info (station_name, department_name, line_name) is included so
    the front-end can render the chart screen header without a separate call.
    """
    db = _tenant_db(current_admin)
    try:
        station = (
            db.query(Station)
            .filter(
                Station.station_id == station_id,
                Station.operational_status == "active",
            )
            .first()
        )
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Station not found.",
            )

        # Resolve dept / line names
        dept = (
            db.query(Department)
            .filter(Department.department_id == station.department_id)
            .first()
        )
        line = (
            db.query(ProductionLine)
            .filter(ProductionLine.line_id == station.line_id)
            .first()
        )

        chars = (
            db.query(Characteristic)
            .filter(
                Characteristic.station_id == station_id,
                Characteristic.is_active == True,
            )
            .order_by(asc(Characteristic.characteristic_name))
            .all()
        )

        char_list = []
        for char in chars:
            # Quick status: look at the last sample only
            latest_sample = (
                db.query(Sample)
                .filter(Sample.characteristic_id == char.characteristic_id)
                .order_by(desc(Sample.sample_datetime))
                .first()
            )
            current_status = "no_data"
            if latest_sample:
                # Check if it has a stored UCL/LCL; use them for a fast check
                # (full recompute is done by ichart/pchart endpoints)
                meas = (
                    db.query(Measurement)
                    .filter(Measurement.sample_id == latest_sample.sample_id)
                    .first()
                )
                if meas and char.ucl is not None and char.lcl is not None:
                    v = float(meas.measurement_value)
                    ucl = float(char.ucl)
                    lcl = float(char.lcl)
                    current_status = (
                        "not_in_control" if (v > ucl or v < lcl) else "in_control"
                    )
                else:
                    current_status = "in_control"  # safe default when no stored limits

            char_list.append(
                {
                    "characteristic_id": char.characteristic_id,
                    "characteristic_name": char.characteristic_name,
                    "chart_type": char.chart_type.value,
                    "unit_of_measure": char.unit_of_measure,
                    "usl": float(char.usl) if char.usl is not None else None,
                    "lsl": float(char.lsl) if char.lsl is not None else None,
                    "sample_size": char.sample_size,
                    "check_frequency_minutes": char.check_frequency_minutes,
                    "current_status": current_status,
                }
            )

        return {
            "station_id": station_id,
            "station_name": station.station_name,
            "department_name": dept.department_name if dept else None,
            "line_name": line.line_name if line else None,
            "characteristics": char_list,
        }
    finally:
        db.close()


@router.get("/station/{station_id}/models")
async def get_station_models(
    station_id: str,
    current_admin: Admin = Depends(get_current_admin),
):
    """
    List all product models associated with a station.
    Used to populate the **Model dropdown** in the mobile chart-detail screen.

    The station stores model UUIDs in a JSONB array (`model_ids` field).
    This endpoint resolves those IDs to full model objects (name + code)
    so the front end can display human-readable model names.
    """
    db = _tenant_db(current_admin)
    try:
        station = (
            db.query(Station)
            .filter(
                Station.station_id == station_id,
                Station.operational_status == "active",
            )
            .first()
        )
        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Station not found.",
            )

        model_ids: list = station.model_ids or []
        if not model_ids:
            return {"station_id": station_id, "models": []}

        models = (
            db.query(ProductModel)
            .filter(
                ProductModel.model_id.in_(model_ids),
                ProductModel.is_active == True,
            )
            .order_by(asc(ProductModel.model_name))
            .all()
        )

        return {
            "station_id": station_id,
            "models": [
                {
                    "model_id": m.model_id,
                    "model_name": m.model_name,
                    "model_code": m.model_code,
                }
                for m in models
            ],
        }
    finally:
        db.close()


# ── Shared helpers ───────────────────────────────────────────────────────────


def _char_info(char: Characteristic) -> dict:
    return {
        "characteristic_id": char.characteristic_id,
        "characteristic_name": char.characteristic_name,
        "unit_of_measure": char.unit_of_measure,
        "chart_type": char.chart_type.value,
        "usl": float(char.usl) if char.usl is not None else None,
        "lsl": float(char.lsl) if char.lsl is not None else None,
        "target_value": (
            float(char.target_value) if char.target_value is not None else None
        ),
        "sample_size": char.sample_size,
        "check_frequency_minutes": char.check_frequency_minutes,
    }


def _empty_chart_response(char: Characteristic, chart_type: str) -> dict:
    return {
        "applicable": True,
        "characteristic": _char_info(char),
        "chart_data": {
            "points": [],
            "ucl": None,
            "cl": None,
            "lcl": None,
        },
        "window": {"size": 0, "is_preliminary": True, "total_samples": 0},
        "status": "no_data",
        "message": "No sample data yet. Charts will build once data entry begins.",
    }
