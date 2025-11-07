import sys, types
fake_log = types.ModuleType("anteater.utils.log")
import logging
fake_log.logger = logging.getLogger("anteater")
sys.modules["anteater.utils.log"] = fake_log

from container_disruption_detection.mcp.mcp_server import (
    container_anomaly_detection_tool, container_report_tool,
    TSPayload, TSPoint, ReportType, ContainerDisruptionFacade
)

# mock spot detect，避免空数据报错
ContainerDisruptionFacade._spot_detect = staticmethod(lambda *_: 4)

def test_offline_mcp_tool():
    payload = TSPayload(items=[
        TSPoint(
            metric="gala_gopher_sli_container_cpu_rundelay",
            labels={"container_name": "/container1"},
            time_stamps=list(range(241)),
            values=[1.07e9]*100 + [1.6e5]*100 + list(range(41))
        )
    ])

    anomalies = container_anomaly_detection_tool(
        machine_id="offline",
        kpis=[],
        ts_payload=payload,
    )
    assert isinstance(anomalies, list)
    print("检测结果:", anomalies)

    report = container_report_tool(anomalies, report_type=ReportType.anomaly)
    print(report["markdown"])
