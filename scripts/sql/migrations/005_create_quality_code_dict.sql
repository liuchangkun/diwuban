-- 目的：质量状态码与中文标签字典，便于统一标注与报表分组

BEGIN;

CREATE TABLE IF NOT EXISTS public.quality_code_dict(
  code smallint PRIMARY KEY,
  label_zh text NOT NULL,
  category text NULL,
  severity int NULL,
  description text NULL
);

COMMENT ON TABLE public.quality_code_dict IS '质量码字典表：映射 quality_status（数值）到中文标签与类别、严重度、描述。';
COMMENT ON COLUMN public.quality_code_dict.code IS '质量码（与 fact_measurements.quality_status 一致）。';
COMMENT ON COLUMN public.quality_code_dict.label_zh IS '中文标签（如：越界、异常跳变、平台期、状态矛盾、功率因数异常等）。';
COMMENT ON COLUMN public.quality_code_dict.category IS '类别（如：数值特性、状态矛盾、机理/物理、时间一致性等）。';
COMMENT ON COLUMN public.quality_code_dict.severity IS '严重度等级（1~5，数字越大表示越严重；可选）。';
COMMENT ON COLUMN public.quality_code_dict.description IS '中文描述（规则说明/判定逻辑摘要）。';

-- 预置常用质量码（可按需扩展）
INSERT INTO public.quality_code_dict(code,label_zh,category,severity,description) VALUES
  (101,'越界','数值特性',3,'数值超出合理区间'),
  (111,'异常跳变','数值特性',3,'相邻秒差值超阈'),
  (112,'变化率异常','数值特性',3,'相对或绝对变化率超阈'),
  (121,'平台期','数值特性',2,'短窗标准差与极差均很小，可能传感器卡死'),
  (131,'上饱和','数值特性',3,'接近量程上限持续'),
  (132,'下饱和','数值特性',3,'接近量程下限持续'),
  (201,'高噪声','噪声/完整性',2,'短窗标准差异常偏高'),
  (401,'状态矛盾','跨指标/跨设备',4,'运行=0但功率/流量高或运行=1但输出近零'),
  (501,'时间漂移','时间一致性',2,'ts_raw 与 ts_bucket 偏差过大'),
  (502,'重复秒','时间一致性',2,'同秒重复/冲突'),
  (701,'功率因数异常','机理/物理',3,'功率因数超出合理范围'),
  (711,'液位流量守恒异常','机理/物理',4,'dLevel/dt 与流量不一致'),
  (721,'相似定律异常','机理/物理',3,'与变频相似定律偏差过大'),
  (731,'泵曲线偏差','机理/物理',3,'与泵特性曲线偏差过大'),
  (751,'计数器非单调','机理/物理',3,'累计量出现回退');

COMMIT;

