from __future__ import annotations
import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from anteater.core.ts import TimeSeries

logger = logging.getLogger("container_disruption_data")

# ================= 工具函数 =================
def divide(x, y):
    try:
        return x / y if y != 0 else 0
    except Exception:
        return 0


def dt_last(*, minutes: int):
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    return start, end


# ================== 数据模型 ==================
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


# =============== MetricLoader 工厂 ===============
def build_metric_loader(config_json=None, metricinfo_json=None,
                        config_path=None, metricinfo_path=None):
    """构建 Anteater MetricLoader"""
    from anteater.config import AnteaterConf
    from anteater.core.info import MetricInfo
    from anteater.source.metric_loader import MetricLoader

    def _load_json(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    if config_json is None and config_path:
        config_json = _load_json(config_path)
    if metricinfo_json is None and metricinfo_path:
        metricinfo_json = _load_json(metricinfo_path)

    cfg = AnteaterConf(**config_json) if config_json else AnteaterConf()
    minfo = MetricInfo(**metricinfo_json) if metricinfo_json else MetricInfo()
    return MetricLoader(metricinfo=minfo, config=cfg)
