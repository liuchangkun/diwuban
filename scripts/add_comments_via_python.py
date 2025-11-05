#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""通过Python直接添加数据库注释（使用参数化查询避免引号问题）"""

import psycopg2
import sys
import re

def parse_comment_statements(sql_content):
    """解析SQL文件中的COMMENT语句"""
    # 使用正则表达式匹配COMMENT ON语句
    # 匹配格式：COMMENT ON TABLE/COLUMN/VIEW/MATERIALIZED VIEW/PROCEDURE/FUNCTION xxx IS '...';
    pattern = r"COMMENT\s+ON\s+(MATERIALIZED\s+VIEW|TABLE|COLUMN|VIEW|PROCEDURE|FUNCTION)\s+([^\s]+(?:\([^)]*\))?)\s+IS\s+'((?:[^']|'')*)';"

    statements = []
    for match in re.finditer(pattern, sql_content, re.DOTALL | re.IGNORECASE):
        obj_type = match.group(1).upper()
        obj_name = match.group(2)
        comment = match.group(3)

        # 替换SQL中的双单引号为单引号
        comment = comment.replace("''", "'")

        statements.append({
            'type': obj_type,
            'name': obj_name,
            'comment': comment
        })

    return statements

def add_comment(cursor, obj_type, obj_name, comment):
    """添加注释（使用参数化查询）"""
    try:
        if obj_type == 'TABLE':
            cursor.execute(
                f"COMMENT ON TABLE {obj_name} IS %s;",
                (comment,)
            )
        elif obj_type == 'COLUMN':
            cursor.execute(
                f"COMMENT ON COLUMN {obj_name} IS %s;",
                (comment,)
            )
        elif obj_type == 'VIEW':
            cursor.execute(
                f"COMMENT ON VIEW {obj_name} IS %s;",
                (comment,)
            )
        elif obj_type == 'MATERIALIZED VIEW':
            cursor.execute(
                f"COMMENT ON MATERIALIZED VIEW {obj_name} IS %s;",
                (comment,)
            )
        elif obj_type == 'PROCEDURE':
            cursor.execute(
                f"COMMENT ON PROCEDURE {obj_name} IS %s;",
                (comment,)
            )
        elif obj_type == 'FUNCTION':
            cursor.execute(
                f"COMMENT ON FUNCTION {obj_name} IS %s;",
                (comment,)
            )
        return True
    except Exception as e:
        # 忽略字段不存在的错误
        if "does not exist" in str(e):
            return None  # 返回None表示字段不存在（预期错误）
        else:
            raise e

def main():
    """主函数"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        database="pump_station_optimization"
    )

    cursor = conn.cursor()

    print("=" * 80)
    print("开始添加数据库注释（使用Python参数化查询）")
    print("=" * 80)

    # 读取SQL文件
    sql_file = "scripts/sql/migrations/058_add_remaining_comments.sql"

    print(f"\n读取SQL文件: {sql_file}")

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    print(f"SQL文件大小: {len(sql_content)} 字符")

    # 解析COMMENT语句
    statements = parse_comment_statements(sql_content)

    print(f"找到 {len(statements)} 条COMMENT语句\n")

    # 执行每条语句（每个语句独立事务）
    success_count = 0
    skip_count = 0
    error_count = 0

    for i, stmt in enumerate(statements, 1):
        try:
            result = add_comment(cursor, stmt['type'], stmt['name'], stmt['comment'])
            if result is True:
                success_count += 1
                if stmt['type'] in ('TABLE', 'VIEW', 'MATERIALIZED VIEW', 'PROCEDURE', 'FUNCTION'):
                    obj_type_zh = {'TABLE': '表', 'VIEW': '视图', 'MATERIALIZED VIEW': '物化视图', 'PROCEDURE': '存储过程', 'FUNCTION': '函数'}
                    print(f"✅ [{i}/{len(statements)}] {obj_type_zh.get(stmt['type'], stmt['type'])}注释已添加: {stmt['name']}")
                # 每个成功的语句立即提交
                conn.commit()
            elif result is None:
                skip_count += 1
                # 回滚失败的事务
                conn.rollback()
                # 不显示跳过的字段（太多了）
        except Exception as e:
            error_count += 1
            print(f"❌ [{i}/{len(statements)}] 失败 {stmt['type']} {stmt['name']}: {e}")
            # 回滚失败的事务
            conn.rollback()

    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print(f"注释添加完成！")
    print(f"  ✅ 成功: {success_count} 条")
    print(f"  ⏭️  跳过: {skip_count} 条（字段不存在）")
    print(f"  ❌ 失败: {error_count} 条")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

