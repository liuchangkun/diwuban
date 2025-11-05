import unittest

from app.services.calculation.stats_collector import StatsCollector


class TestStatsCollectorBasic(unittest.TestCase):
    def test_group_and_metric_idempotency(self):
        sc = StatsCollector()
        run_id = "r1"
        station_id = 1
        device_id = 2
        bucket = ("2025-10-07T00:00:00Z", "2025-10-07T01:00:00Z")

        # 组级事件不应报错，可重复调用
        sc.on_group_start("g-1", run_id, station_id, device_id)
        sc.on_group_start("g-1", run_id, station_id, device_id)

        # 指标开始/写入/结束一次
        sc.on_metric_start(run_id, station_id, device_id, "m1", bucket, path_type="acyclic", method_id="mid", total_points=10)
        sc.on_write(run_id, station_id, device_id, "m1", bucket, written_points=7, write_duration_ms=12)
        sc.on_metric_end(run_id, station_id, device_id, "m1", bucket, valid_points=8, calc_duration_ms=20, validate_duration_ms=5, method_id="mid")

        # 重复调用应被忽略（finished=True）
        sc.on_metric_start(run_id, station_id, device_id, "m1", bucket, path_type="acyclic", method_id="mid", total_points=100)
        sc.on_write(run_id, station_id, device_id, "m1", bucket, written_points=100, write_duration_ms=999)
        sc.on_metric_end(run_id, station_id, device_id, "m1", bucket, valid_points=100, calc_duration_ms=999, validate_duration_ms=999, method_id="mid")

        result = sc.flush()
        self.assertEqual(len(result), 1)
        key = next(iter(result.keys()))
        stats = result[key]
        self.assertEqual(stats["total_points"], 10)
        self.assertEqual(stats["written_points"], 7)
        self.assertEqual(stats["valid_points"], 8)
        self.assertTrue(stats["finished"])  # 幂等标记


if __name__ == "__main__":
    unittest.main()

