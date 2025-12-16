\encoding UTF8
SET client_encoding = 'UTF8';

/*
脚本名称: 001_create_completion_gaps.sql
脚本用途: 创建缺口明细持久化表 completion_gaps，用于持久化记录“发现的全部缺口”（包含未处理/跳过的缺口），以支撑审计、可视化与复盘；该表与 completion_steps 解耦。
依赖组件: 需要先存在 completion_runs（run_id 外键）。
适用环境: 建议先在测试/开发库执行；生产执行需走评审与变更审批流程。
设计背景:
  - 现有 completion_steps 仅记录“已处理的缺口步骤”，无法覆盖“全部发现的缺口”。
  - 已有缺口识别函数 fn_detect_gaps_1s 与视图模板 v_coverage_gaps_1s 用于检测/查询，但缺少“持久化全集”的落库表。
  - 因此新增 completion_gaps，以流水线识别步骤统一落库并具备幂等，形成可追溯的缺口全集数据源。
使用建议:
  - 在 Pipeline 的“缺口识别”阶段（非 dry-run），批量 upsert 到 completion_gaps（按 UNIQUE 约束）。
  - 与 completion_steps 的关系：steps 处理的缺口应在 completion_gaps 中可找到；未处理/跳过的缺口仅存在 completion_gaps。
*/

BEGIN;

CREATE TABLE IF NOT EXISTS public.completion_gaps (
  gap_id              bigserial PRIMARY KEY,
  run_id              bigint NOT NULL REFERENCES public.completion_runs(run_id) ON DELETE CASCADE,
  station_id          bigint NOT NULL,
  device_id           bigint NOT NULL,
  metric_id           bigint NOT NULL,
  gap_start_ts        timestamptz NOT NULL,

-- 字段说明：
--   gap_id:       主键，流水号。
--   run_id:       运行批次ID（关联 completion_runs.run_id），用于区分不同窗口与参数下的识别结果。
--   station_id:   站点ID。
--   device_id:    设备ID。
--   metric_id:    指标ID（dim_metric_config.id）。

-- 列注释（用于
--   \d+ public.completion_gaps 或元数据查询 pg_catalog.pg_description）
COMMENT ON COLUMN public.completion_gaps.gap_id               IS '主键，流水号';
COMMENT ON COLUMN public.completion_gaps.run_id               IS '运行批次ID，关联 completion_runs.run_id（区分窗口与参数）';
COMMENT ON COLUMN public.completion_gaps.station_id           IS '站点ID';
COMMENT ON COLUMN public.completion_gaps.device_id            IS '设备ID';
COMMENT ON COLUMN public.completion_gaps.metric_id            IS '指标ID（dim_metric_config.id）';
COMMENT ON COLUMN public.completion_gaps.gap_start_ts         IS '缺口开始秒（UTC，含）';
COMMENT ON COLUMN public.completion_gaps.gap_end_ts           IS '缺口结束秒（UTC，含）';
COMMENT ON COLUMN public.completion_gaps.gap_len_sec          IS '缺口长度（秒）：gap_end_ts - gap_start_ts + 1';
COMMENT ON COLUMN public.completion_gaps.gap_class            IS '缺口分类：short|mid|long（来自系统阈值）';
COMMENT ON COLUMN public.completion_gaps.in_startstop_window  IS '是否处于启停窗口（true 表示可能是启停过程导致的缺口）';
COMMENT ON COLUMN public.completion_gaps.flags                IS '标志数组：如 cumulative_metric/out_of_window 等';
COMMENT ON COLUMN public.completion_gaps.detected_at          IS '识别写入时间戳';

-- 索引注释
COMMENT ON INDEX idx_completion_gaps_run  IS '按 run_id 检索缺口明细，加速单次运行的审计/统计';
COMMENT ON INDEX idx_completion_gaps_time IS '按 device_id + gap_start_ts 检索缺口，适配按设备窗口查询';

--   gap_start_ts: 缺口开始秒（UTC，含）。
--   gap_end_ts:   缺口结束秒（UTC，含）。
--   gap_len_sec:  缺口长度（秒）。
--   gap_class:    缺口分类（short|mid|long），依据系统配置阈值（如 short<300, 300<=mid<1800, long>=1800）。
--   in_startstop_window: 是否处于启停窗口（true 表示可能是启停过程导致的缺口）。
--   flags:        标志数组（如 'cumulative_metric', 'out_of_window' 等）。
--   detected_at:  识别写入时间戳。
-- 唯一约束：
--   (run_id, device_id, metric_id, gap_start_ts, gap_end_ts) 作为幂等键，避免重复落库。
-- 索引建议：
--   idx_completion_gaps_run 便于按 run 检索；idx_completion_gaps_time 便于按设备与时间范围检索。

-- 查询与验收示例：
--   统计各类别缺口数：
--     SELECT gap_class, count(*) FROM public.completion_gaps WHERE run_id=:rid GROUP BY gap_class;
--   抽查最长缺口：
--     SELECT * FROM public.completion_gaps WHERE run_id=:rid ORDER BY gap_len_sec DESC LIMIT 20;
--   关联步骤验证（若需要）：
--     SELECT s.* FROM public.completion_steps s
--     JOIN public.completion_gaps g ON g.run_id=s.run_id AND g.device_id=s.device_id AND g.metric_id=s.metric_id
--                                  AND g.gap_start_ts=s.gap_start_ts AND g.gap_end_ts=s.gap_end_ts
--     WHERE s.run_id=:rid;

  gap_end_ts          timestamptz NOT NULL,
  gap_len_sec         integer NOT NULL,
  gap_class           text NOT NULL,            -- short|mid|long
  in_startstop_window boolean NOT NULL DEFAULT false,
  flags               text[],
  detected_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, device_id, metric_id, gap_start_ts, gap_end_ts)
);

CREATE INDEX IF NOT EXISTS idx_completion_gaps_run   ON public.completion_gaps(run_id);
CREATE INDEX IF NOT EXISTS idx_completion_gaps_time  ON public.completion_gaps(device_id, gap_start_ts);

COMMENT ON TABLE public.completion_gaps IS '缺口明细持久化表：记录发现的全部缺口（含未处理/跳过），用于审计与可视化。';

COMMIT;

