sql = """
[已归档示例SQL]
原示例引用了 v_fully_adaptive_data/device_data/pipeline_data，已与当前数据库不符。
请参考 app/api/v1/endpoints/data.py 中的基于 fact_measurements 的透视 SQL。
"""
print('占位符数量:', sql.count('%s'))

