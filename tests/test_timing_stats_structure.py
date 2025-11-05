"""测试耗时统计的返回值结构"""


def test_rule_result_structure_extraction():
    """测试从新的返回值结构中提取总数和总耗时"""
    # 模拟新的返回值结构
    rule_result = {
        "baseline_shadow": {"count": 128, "duration_ms": 25000},
        "baseline_prod": {"count": 128, "duration_ms": 15000},
        "quality_rules_shadow": {"count": 0, "duration_ms": 100},
        "running_thresholds_shadow": {"count": 256, "duration_ms": 45000},
        "running_thresholds_prod": {"count": 256, "duration_ms": 32000},
        "quality_rules_prod": {"count": 0, "duration_ms": 500},
    }
    
    # 提取总数（与 prepare_dim 中的逻辑一致）
    total_rules = sum(v["count"] if isinstance(v, dict) else v for v in rule_result.values())
    total_duration_ms = sum(v.get("duration_ms", 0) if isinstance(v, dict) else 0 for v in rule_result.values())
    
    # 验证
    assert total_rules == 768  # 128 + 128 + 0 + 256 + 256 + 0
    assert total_duration_ms == 117600  # 25000 + 15000 + 100 + 45000 + 32000 + 500


def test_rule_result_structure_with_errors():
    """测试包含错误的返回值结构"""
    rule_result = {
        "baseline_shadow": {"count": 0, "duration_ms": 0},  # 跳过
        "baseline_prod": {"count": 128, "duration_ms": 15000},
        "quality_rules_shadow": {"count": 0, "duration_ms": 100, "error": "Some error"},  # 失败
        "running_thresholds_shadow": {"count": 256, "duration_ms": 45000},
        "running_thresholds_prod": {"count": 256, "duration_ms": 32000},
        "quality_rules_prod": {"count": 0, "duration_ms": 500},
    }
    
    # 提取总数
    total_rules = sum(v["count"] if isinstance(v, dict) else v for v in rule_result.values())
    total_duration_ms = sum(v.get("duration_ms", 0) if isinstance(v, dict) else 0 for v in rule_result.values())
    
    # 验证
    assert total_rules == 640  # 0 + 128 + 0 + 256 + 256 + 0
    assert total_duration_ms == 92600  # 0 + 15000 + 100 + 45000 + 32000 + 500


def test_timing_stats_structure():
    """测试 orchestrator 中的耗时统计结构"""
    import time
    
    # 模拟 timing_stats 字典
    timing_stats = {}
    
    # 模拟阶段1
    t0_stage = time.perf_counter()
    time.sleep(0.01)  # 模拟10ms的工作
    duration_s = time.perf_counter() - t0_stage
    timing_stats["prepare_dim_stage1"] = {"duration_s": duration_s}
    
    # 模拟阶段2（包含规则生成详细耗时）
    t0_stage = time.perf_counter()
    time.sleep(0.02)  # 模拟20ms的工作
    duration_s = time.perf_counter() - t0_stage
    rule_timing = {
        "baseline_shadow": 25000,
        "baseline_prod": 15000,
        "quality_rules_shadow": 100,
        "running_thresholds_shadow": 45000,
        "running_thresholds_prod": 32000,
        "quality_rules_prod": 500,
    }
    timing_stats["prepare_dim_stage2"] = {"duration_s": duration_s, "rule_timing_ms": rule_timing}
    
    # 验证结构
    assert "prepare_dim_stage1" in timing_stats
    assert "duration_s" in timing_stats["prepare_dim_stage1"]
    assert timing_stats["prepare_dim_stage1"]["duration_s"] > 0
    
    assert "prepare_dim_stage2" in timing_stats
    assert "duration_s" in timing_stats["prepare_dim_stage2"]
    assert "rule_timing_ms" in timing_stats["prepare_dim_stage2"]
    assert len(timing_stats["prepare_dim_stage2"]["rule_timing_ms"]) == 6
    assert timing_stats["prepare_dim_stage2"]["rule_timing_ms"]["baseline_shadow"] == 25000


def test_timing_report_generation():
    """测试耗时报告生成逻辑"""
    timing_stats = {
        "prepare_dim_stage1": {"duration_s": 5.23},
        "create_staging": {"duration_s": 2.15},
        "ingest_copy": {"duration_s": 8.47},
        "merge_fact": {"duration_s": 12.34},
        "prepare_dim_stage2": {
            "duration_s": 120.50,
            "rule_timing_ms": {
                "baseline_shadow": 25000,
                "baseline_prod": 15000,
                "quality_rules_shadow": 100,
                "running_thresholds_shadow": 45000,
                "running_thresholds_prod": 32000,
                "quality_rules_prod": 500,
            }
        },
        "total": {"duration_s": 148.69}
    }
    
    total_duration_s = timing_stats["total"]["duration_s"]
    
    # 生成报告行
    report_lines = []
    for stage_name, stage_data in timing_stats.items():
        if stage_name == "total":
            continue
        duration_s = stage_data.get("duration_s", 0)
        percentage = (duration_s / total_duration_s * 100) if total_duration_s > 0 else 0
        
        # 详细信息
        details = ""
        if stage_name == "prepare_dim_stage2" and "rule_timing_ms" in stage_data:
            rule_timing = stage_data["rule_timing_ms"]
            if rule_timing:
                details_parts = []
                for rule_name, duration_ms in rule_timing.items():
                    details_parts.append(f"{rule_name}: {duration_ms}ms")
                details = "; ".join(details_parts)
        
        report_lines.append({
            "stage": stage_name,
            "duration_s": duration_s,
            "percentage": percentage,
            "details": details
        })
    
    # 验证
    assert len(report_lines) == 5
    assert report_lines[0]["stage"] == "prepare_dim_stage1"
    assert report_lines[0]["percentage"] > 0
    assert report_lines[4]["stage"] == "prepare_dim_stage2"
    assert "baseline_shadow: 25000ms" in report_lines[4]["details"]
    assert sum(line["percentage"] for line in report_lines) < 100.1  # 允许浮点误差

