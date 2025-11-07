import sys, types
fake_log = types.ModuleType("anteater.utils.log")
import logging
fake_log.logger = logging.getLogger("anteater")
sys.modules["anteater.utils.log"] = fake_log

import pytest
import numpy as np
from types import SimpleNamespace
from datetime import datetime, timezone
from anteater.core.ts import TimeSeries
from container_disruption_detection.mcp.mcp_server import ContainerDisruptionFacade, AnomalyModel, ExtraConfig

@pytest.fixture
def mock_facade(monkeypatch):
    """创建一个带假依赖的ContainerDisruptionFacade对象"""
    facade = ContainerDisruptionFacade(data_loader=SimpleNamespace(), config=ExtraConfig())

    # mock TSDBSCAN.detect() → 模拟检测结果（部分异常）
    class MockTSDBSCAN:
        def __init__(self, *_, **__): pass
        def detect(self, values):
            # 返回0/1序列，模拟241点中部分为异常
            return np.array([0]*230 + [1]*11)
    monkeypatch.setattr("container_disruption_detection.mcp.mcp_server.TSDBSCAN", MockTSDBSCAN)

    # mock SPOT算法内部调用，直接返回4个异常
    def mock_spot_detect(train_data, test_data, obs_size):
        return 4  # 模拟4个异常点
    facade._spot_detect = mock_spot_detect

    # mock get_container_extra_info()，避免真实请求
    facade.get_container_extra_info = lambda *a, **kw: {"mock": True}

    return facade


def make_mock_timeseries():
    """构造一条模拟的时间序列"""
    timestamps = list(range(241))
    # 模拟数据变化：前100高值，中间低值，后段波动
    values = (
        [1.07e9]*100 + [1.6e5]*100 + list(np.linspace(4.8e3, 2.6e8, 41))
    )
    labels = {
        "container_id": "102c5c265006",
        "container_name": "/container1",
        "machine_id": "1396ba98-aff3-438a-af15-b558b4e2e339-192.168.64.2"
    }
    return [TimeSeries(metric="gala_gopher_sli_container_cpu_rundelay",
                       labels=labels,
                       time_stamps=timestamps,
                       values=values)]


def test_detect_by_spot_without_rca(mock_facade):
    """测试detect_by_spot_without_rca逻辑"""
    ts_list = make_mock_timeseries()
    mock_facade.start_time = datetime.now(timezone.utc)
    mock_facade.end_time = datetime.now(timezone.utc)

    anomalies = mock_facade.detect_by_spot_without_rca(
        metric="gala_gopher_sli_container_cpu_rundelay",
        machine_id="1396ba98-aff3-438a-af15-b558b4e2e339-192.168.64.2",
        outlier_ratio_th=0.3,
        look_back=20,
        obs_size=10,
        ts_list_override=ts_list,
    )

    assert isinstance(anomalies, list)
    assert len(anomalies) == 1
    anomaly = anomalies[0]
    assert anomaly.details["event_source"] == "spot"
    assert anomaly.details["info"]["mock"] is True

