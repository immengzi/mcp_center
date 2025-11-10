from __future__ import annotations
import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from anteater.core.ts import TimeSeries

logger = logging.getLogger("container_disruption_data")


def divide(x, y):
    try:
        return x / y if y != 0 else 0
    except Exception:
        return 0


def dt_last(*, minutes: int):
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    return start, end


class RootCauseModel(BaseModel):
    metric: str
    labels: Dict[str, Union[str, int, float]] = Field(default_factory=dict)
    score: float


class AnomalyModel(BaseModel):
    machine_id: str
    metric: str
    labels: Dict[str, Union[str, int, float]] = Field(default_factory=dict)
    score: float
    entity_name: Optional[str] = ""
    details: Dict[str, Union[str, int, float, dict]] = Field(default_factory=dict)
    root_causes: List[RootCauseModel] = Field(default_factory=list)


class KPIParam(BaseModel):
    metric: str
    entity_name: Optional[str] = ""
    params: Dict[str, Union[str, int, float]] = Field(default_factory=dict)


class WindowParam(BaseModel):
    look_back: int = 20
    obs_size: int = 6


class ExtraConfig(BaseModel):
    extra_metrics: str = ""


class TSPoint(BaseModel):
    metric: str
    labels: Dict[str, Union[str, int, float]] = Field(default_factory=dict)
    time_stamps: List[int]
    values: List[float]


class TSPayload(BaseModel):
    items: List[TSPoint]


class RCARequest(BaseModel):
    victim: TSPoint
    context: TSPayload


class ReportType(str, Enum):
    normal = "normal"
    anomaly = "anomaly"


def build_metric_loader(config_json=None, metricinfo_json=None):
    """构建 MetricLoader 实例"""
    from anteater.config import AnteaterConf
    from anteater.core.info import MetricInfo
    from anteater.source.metric_loader import MetricLoader

    cfg = AnteaterConf(**config_json) if config_json else AnteaterConf()
    minfo = MetricInfo(**metricinfo_json) if metricinfo_json else MetricInfo()
    return MetricLoader(metricinfo=minfo, config=cfg)
