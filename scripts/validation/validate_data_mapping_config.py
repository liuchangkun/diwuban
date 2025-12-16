#!/usr/bin/env python3
"""
配置文件验证脚本
用途：验证 configs/data_mapping.v2.json 的完整性、唯一性和一致性
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


# 允许的设备类型
ALLOWED_DEVICE_TYPES = {"pump", "main_pipeline", "other", "clear_water_pool"}
# 允许的泵类型
ALLOWED_PUMP_TYPES = {"variable_frequency", "soft_start"}


class ValidationError:
    """验证错误记录"""
    def __init__(self, error_type: str, location: str, detail: str):
        self.error_type = error_type
        self.location = location
        self.detail = detail
    
    def __str__(self):
        return f"[配置验证错误] [{self.error_type}] {self.location}: {self.detail}"


class ConfigValidator:
    """配置文件验证器"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
        self.station_count = 0
        self.device_count = 0
        self.station_ids: Set[int] = set()
        self.device_ids: Set[int] = set()
    
    def validate(self) -> bool:
        """执行完整验证流程"""
        print("=" * 80)
        print("配置文件验证开始")
        print("=" * 80)
        print(f"配置文件路径: {self.config_path}")
        print()
        
        # 步骤1: JSON格式验证
        if not self._validate_json_format():
            self._print_results()
            return False
        
        # 步骤2: 结构验证
        if not self._validate_structure():
            self._print_results()
            return False
        
        # 步骤3: 字段完整性验证
        if not self._validate_fields():
            self._print_results()
            return False
        
        # 步骤4: ID唯一性验证
        if not self._validate_id_uniqueness():
            self._print_results()
            return False
        
        # 步骤5: 数据一致性验证
        if not self._validate_data_consistency():
            self._print_results()
            return False
        
        # 所有验证通过
        self._print_results()
        return True
    
    def _validate_json_format(self) -> bool:
        """验证JSON格式"""
        print("[步骤1] JSON格式验证...")
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print("  ✅ JSON格式正确")
            return True
        except json.JSONDecodeError as e:
            self.errors.append(ValidationError(
                "JSON格式错误",
                f"行 {e.lineno}, 列 {e.colno}",
                f"{e.msg}"
            ))
            print(f"  ❌ JSON格式错误: {e}")
            return False
        except Exception as e:
            self.errors.append(ValidationError(
                "文件读取错误",
                str(self.config_path),
                str(e)
            ))
            print(f"  ❌ 文件读取错误: {e}")
            return False
    
    def _validate_structure(self) -> bool:
        """验证基本结构"""
        print("[步骤2] 基本结构验证...")
        
        if not isinstance(self.data, dict):
            self.errors.append(ValidationError(
                "结构错误",
                "根节点",
                "配置文件根节点必须是对象(dict)"
            ))
            print("  ❌ 根节点不是对象")
            return False
        
        if "stations" not in self.data:
            self.errors.append(ValidationError(
                "结构错误",
                "根节点",
                "缺少必需字段 'stations'"
            ))
            print("  ❌ 缺少 'stations' 字段")
            return False
        
        if not isinstance(self.data["stations"], list):
            self.errors.append(ValidationError(
                "结构错误",
                "stations",
                "'stations' 必须是数组(list)"
            ))
            print("  ❌ 'stations' 不是数组")
            return False
        
        print("  ✅ 基本结构正确")
        return True
    
    def _validate_fields(self) -> bool:
        """验证字段完整性"""
        print("[步骤3] 字段完整性验证...")
        has_error = False
        
        for station_idx, station in enumerate(self.data["stations"]):
            station_num = station_idx + 1
            
            # 验证泵站必需字段
            if not isinstance(station, dict):
                self.errors.append(ValidationError(
                    "字段类型错误",
                    f"泵站#{station_num}",
                    "泵站必须是对象(dict)"
                ))
                has_error = True
                continue
            
            # 验证泵站name字段
            if "name" not in station:
                self.errors.append(ValidationError(
                    "缺少必需字段",
                    f"泵站#{station_num}",
                    "缺少必需字段 'name'"
                ))
                has_error = True
            elif not isinstance(station["name"], str) or not station["name"].strip():
                self.errors.append(ValidationError(
                    "字段值错误",
                    f"泵站#{station_num}",
                    "'name' 必须是非空字符串"
                ))
                has_error = True
            
            # 验证泵站id字段
            if "id" not in station:
                self.errors.append(ValidationError(
                    "缺少必需字段",
                    f"泵站 '{station.get('name', '未命名')}'",
                    "缺少必需字段 'id'"
                ))
                has_error = True
            elif not isinstance(station["id"], int) or station["id"] <= 0:
                self.errors.append(ValidationError(
                    "字段值错误",
                    f"泵站 '{station.get('name', '未命名')}'",
                    f"'id' 必须是正整数，当前值: {station.get('id')}"
                ))
                has_error = True
            
            # 验证devices字段
            if "devices" not in station:
                self.errors.append(ValidationError(
                    "缺少必需字段",
                    f"泵站 '{station.get('name', '未命名')}'",
                    "缺少必需字段 'devices'"
                ))
                has_error = True
                continue
            
            if not isinstance(station["devices"], list):
                self.errors.append(ValidationError(
                    "字段类型错误",
                    f"泵站 '{station.get('name', '未命名')}'",
                    "'devices' 必须是数组(list)"
                ))
                has_error = True
                continue
            
            # 验证每个设备
            station_name = station.get("name", "未命名")
            for device_idx, device in enumerate(station["devices"]):
                device_num = device_idx + 1
                
                if not isinstance(device, dict):
                    self.errors.append(ValidationError(
                        "字段类型错误",
                        f"泵站 '{station_name}' 的设备#{device_num}",
                        "设备必须是对象(dict)"
                    ))
                    has_error = True
                    continue
                
                # 验证设备name字段
                if "name" not in device:
                    self.errors.append(ValidationError(
                        "缺少必需字段",
                        f"泵站 '{station_name}' 的设备#{device_num}",
                        "缺少必需字段 'name'"
                    ))
                    has_error = True
                elif not isinstance(device["name"], str) or not device["name"].strip():
                    self.errors.append(ValidationError(
                        "字段值错误",
                        f"泵站 '{station_name}' 的设备#{device_num}",
                        "'name' 必须是非空字符串"
                    ))
                    has_error = True
                
                # 验证设备id字段
                device_name = device.get("name", "未命名")
                if "id" not in device:
                    self.errors.append(ValidationError(
                        "缺少必需字段",
                        f"泵站 '{station_name}' 的设备 '{device_name}'",
                        "缺少必需字段 'id'"
                    ))
                    has_error = True
                elif not isinstance(device["id"], int) or device["id"] <= 0:
                    self.errors.append(ValidationError(
                        "字段值错误",
                        f"泵站 '{station_name}' 的设备 '{device_name}'",
                        f"'id' 必须是正整数，当前值: {device.get('id')}"
                    ))
                    has_error = True
                
                # 验证设备type字段
                if "type" not in device:
                    self.errors.append(ValidationError(
                        "缺少必需字段",
                        f"泵站 '{station_name}' 的设备 '{device_name}'",
                        "缺少必需字段 'type'"
                    ))
                    has_error = True
                elif not isinstance(device["type"], str) or not device["type"].strip():
                    self.errors.append(ValidationError(
                        "字段值错误",
                        f"泵站 '{station_name}' 的设备 '{device_name}'",
                        "'type' 必须是非空字符串"
                    ))
                    has_error = True
        
        if has_error:
            print(f"  ❌ 发现 {len([e for e in self.errors if '字段' in e.error_type])} 个字段错误")
            return False
        else:
            print("  ✅ 所有必需字段完整且类型正确")
            return True

    def _validate_id_uniqueness(self) -> bool:
        """验证ID唯一性"""
        print("[步骤4] ID唯一性验证...")
        has_error = False

        station_id_map: Dict[int, str] = {}  # id -> station_name
        device_id_map: Dict[int, Tuple[str, str]] = {}  # id -> (station_name, device_name)

        for station in self.data["stations"]:
            station_name = station.get("name", "未命名")
            station_id = station.get("id")

            if station_id is not None and isinstance(station_id, int) and station_id > 0:
                # 检查泵站ID重复
                if station_id in station_id_map:
                    self.errors.append(ValidationError(
                        "ID重复",
                        f"泵站 '{station_name}'",
                        f"泵站ID {station_id} 与泵站 '{station_id_map[station_id]}' 重复"
                    ))
                    has_error = True
                else:
                    station_id_map[station_id] = station_name
                    self.station_ids.add(station_id)
                    self.station_count += 1

            # 检查设备ID
            for device in station.get("devices", []):
                device_name = device.get("name", "未命名")
                device_id = device.get("id")

                if device_id is not None and isinstance(device_id, int) and device_id > 0:
                    # 检查设备ID重复
                    if device_id in device_id_map:
                        prev_station, prev_device = device_id_map[device_id]
                        self.errors.append(ValidationError(
                            "ID重复",
                            f"泵站 '{station_name}' 的设备 '{device_name}'",
                            f"设备ID {device_id} 与泵站 '{prev_station}' 的设备 '{prev_device}' 重复"
                        ))
                        has_error = True
                    else:
                        device_id_map[device_id] = (station_name, device_name)
                        self.device_ids.add(device_id)
                        self.device_count += 1

        if has_error:
            print(f"  ❌ 发现 {len([e for e in self.errors if e.error_type == 'ID重复'])} 个ID重复错误")
            return False
        else:
            print(f"  ✅ 所有ID唯一")
            print(f"     - 泵站ID: {sorted(self.station_ids)}")
            print(f"     - 设备ID: {sorted(self.device_ids)}")
            return True

    def _validate_data_consistency(self) -> bool:
        """验证数据一致性"""
        print("[步骤5] 数据一致性验证...")
        has_error = False

        for station in self.data["stations"]:
            station_name = station.get("name", "未命名")

            for device in station.get("devices", []):
                device_name = device.get("name", "未命名")
                device_type = device.get("type", "").strip().lower().replace("-", "_")
                pump_type = device.get("pump_type")

                # 验证设备类型
                if device_type and device_type not in ALLOWED_DEVICE_TYPES:
                    self.errors.append(ValidationError(
                        "数据一致性错误",
                        f"泵站 '{station_name}' 的设备 '{device_name}'",
                        f"设备类型 '{device.get('type')}' 不在允许范围内。允许的类型: {ALLOWED_DEVICE_TYPES}"
                    ))
                    has_error = True

                # 验证泵类型（仅pump类型设备需要）
                if device_type == "pump":
                    if pump_type:
                        pump_type_norm = str(pump_type).strip().lower().replace("-", "_")
                        if pump_type_norm not in ALLOWED_PUMP_TYPES:
                            self.errors.append(ValidationError(
                                "数据一致性错误",
                                f"泵站 '{station_name}' 的设备 '{device_name}'",
                                f"泵类型 '{pump_type}' 不在允许范围内。允许的类型: {ALLOWED_PUMP_TYPES}"
                            ))
                            has_error = True
                    else:
                        self.warnings.append(
                            f"[警告] 泵站 '{station_name}' 的设备 '{device_name}' 是pump类型但未指定pump_type"
                        )

                # 验证metrics配置
                metrics = device.get("metrics", [])
                if not metrics or not isinstance(metrics, list) or len(metrics) == 0:
                    self.warnings.append(
                        f"[警告] 泵站 '{station_name}' 的设备 '{device_name}' 没有配置任何metrics"
                    )

        if has_error:
            print(f"  ❌ 发现 {len([e for e in self.errors if e.error_type == '数据一致性错误'])} 个数据一致性错误")
            return False
        else:
            if self.warnings:
                print(f"  ⚠️  发现 {len(self.warnings)} 个警告（不影响验证通过）")
            print("  ✅ 数据一致性验证通过")
            return True

    def _print_results(self):
        """打印验证结果"""
        print()
        print("=" * 80)
        print("验证结果")
        print("=" * 80)

        if self.errors:
            print(f"\n❌ 验证失败！发现 {len(self.errors)} 个错误：\n")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print(f"\n⚠️  发现 {len(self.warnings)} 个警告：\n")
            for warning in self.warnings:
                print(f"  {warning}")

        if not self.errors:
            print("\n✅ 验证通过！\n")
            print("配置摘要：")
            print(f"  - 泵站数量: {self.station_count}")
            print(f"  - 设备数量: {self.device_count}")
            print(f"  - 泵站ID范围: {min(self.station_ids) if self.station_ids else 'N/A'} - {max(self.station_ids) if self.station_ids else 'N/A'}")
            print(f"  - 设备ID范围: {min(self.device_ids) if self.device_ids else 'N/A'} - {max(self.device_ids) if self.device_ids else 'N/A'}")

        print("=" * 80)


def main():
    """主函数"""
    # 获取配置文件路径
    root_dir = Path(__file__).resolve().parents[2]
    config_path = root_dir / "configs" / "data_mapping.v2.json"

    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return 1

    # 执行验证
    validator = ConfigValidator(config_path)
    success = validator.validate()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

