#!/usr/bin/env python3
"""
验证 merge.yaml 配置文件的语法正确性
"""

import sys
from pathlib import Path
import yaml

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_yaml_syntax():
    """测试 YAML 语法正确性"""
    print("验证 merge.yaml 配置文件语法...")
    
    yaml_file = project_root / "configs" / "merge.yaml"
    print(f"文件路径: {yaml_file}")
    
    try:
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        print("\n✅ YAML 语法正确")
        
        # 验证 quality_mark_chunked 配置节点
        if "run_all" in data and "quality_mark_chunked" in data["run_all"]:
            chunked_config = data["run_all"]["quality_mark_chunked"]
            print("\n✅ 找到 quality_mark_chunked 配置节点")
            print(f"\n配置内容:")
            print(f"  enabled: {chunked_config.get('enabled')}")
            print(f"  chunk_size_minutes: {chunked_config.get('chunk_size_minutes')}")
            print(f"  overlap_minutes: {chunked_config.get('overlap_minutes')}")
            print(f"  on_error: {chunked_config.get('on_error')}")
            
            # 验证配置值
            errors = []
            
            if not isinstance(chunked_config.get('enabled'), bool):
                errors.append("enabled 必须是布尔值")
            
            if not isinstance(chunked_config.get('chunk_size_minutes'), int):
                errors.append("chunk_size_minutes 必须是整数")
            elif chunked_config.get('chunk_size_minutes') <= 0:
                errors.append("chunk_size_minutes 必须 > 0")
            
            if not isinstance(chunked_config.get('overlap_minutes'), int):
                errors.append("overlap_minutes 必须是整数")
            elif chunked_config.get('overlap_minutes') < 1:
                errors.append("overlap_minutes 必须 >= 1")
            
            if chunked_config.get('on_error') not in ('abort', 'continue'):
                errors.append("on_error 必须是 'abort' 或 'continue'")
            
            if chunked_config.get('chunk_size_minutes', 0) <= chunked_config.get('overlap_minutes', 0):
                errors.append("chunk_size_minutes 必须 > overlap_minutes")
            
            if errors:
                print("\n❌ 配置值验证失败:")
                for error in errors:
                    print(f"  - {error}")
                return False
            else:
                print("\n✅ 配置值验证通过")
                return True
        else:
            print("\n❌ 未找到 quality_mark_chunked 配置节点")
            return False
            
    except yaml.YAMLError as e:
        print(f"\n❌ YAML 语法错误: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        return False


if __name__ == "__main__":
    success = test_yaml_syntax()
    sys.exit(0 if success else 1)

