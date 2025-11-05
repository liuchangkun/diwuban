"""
DependencyAnalyzer - 依赖分析器

分析指标之间的依赖关系，生成正确的计算顺序。

核心功能:
1. 构建依赖图（DAG）
2. 拓扑排序（Kahn算法）
3. 检测循环依赖（DFS算法）
4. 生成计算顺序

使用示例:
    from app.services.calculation.dependency_analyzer import DependencyAnalyzer

    analyzer = DependencyAnalyzer()
    order = analyzer.get_calculation_order(['pump_efficiency', 'pump_flow_rate', 'pump_head'])
    # 返回: ['pump_flow_rate', 'pump_head', 'pump_efficiency']
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

from app.adapters.db import get_connection

logger = logging.getLogger(__name__)


class CircularDependencyError(Exception):
    """循环依赖错误"""
    pass


class DependencyAnalyzer:
    """
    依赖分析器

    分析指标之间的依赖关系，生成拓扑排序的计算顺序。

    Attributes:
        _method_registry: 计算方法注册表（从数据库加载）
    """

    def __init__(self):
        """初始化依赖分析器"""
        logger.info("[流程-开始] [依赖分析器初始化]")

        self._method_registry: Dict[str, List[Dict]] = {}
        self._calculation_order_cache: Dict[frozenset, List[str]] = {}  # 计算顺序缓存
        self._cache_hits: int = 0  # 缓存命中次数
        self._cache_misses: int = 0  # 缓存未命中次数
        self._context: Dict | None = None  # 附带上下文（station_id/device_id/time/metrics）
        self._load_methods_from_db()
        logger.info("[核心-初始化] DependencyAnalyzer 初始化完成")

    def set_context(self, ctx: Optional[dict]) -> None:
        """设置当前日志上下文（station_id/device_id/start_time/end_time/requested_metrics）。"""
        self._context = ctx or {}


    def _load_methods_from_db(self) -> None:
        """从数据库加载计算方法注册表"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT method_id, metric_key, method_code, priority, dependencies, is_enabled
                        FROM calculation_method_registry
                        WHERE is_enabled = TRUE
                        ORDER BY metric_key, priority DESC
                    """
                    cur.execute(query)
                    rows = cur.fetchall()

                    # 按metric_key分组
                    for row in rows:
                        method_id, metric_key, method_code, priority, dependencies, is_enabled = row
                        if metric_key not in self._method_registry:
                            self._method_registry[metric_key] = []

                        self._method_registry[metric_key].append({
                            'method_id': method_id,
                            'method_code': method_code,
                            'priority': priority,
                            'dependencies': dependencies or []
                        })

                    logger.info(
                        f"DependencyAnalyzer 加载完成：{len(self._method_registry)} 个指标的方法",
                        extra={"metric_count": len(self._method_registry)}
                    )
        except Exception as e:
            logger.error(f"DependencyAnalyzer 加载失败: {e}", exc_info=True)
            raise

    def build_graph(self, metrics: List[str]) -> Dict[str, List[str]]:
        """
        构建依赖图（自动扩展所有间接依赖）

        为每个指标选择优先级最高的方法，构建依赖关系图。
        自动递归扩展所有间接依赖，确保依赖链完整。

        Args:
            metrics: 需要计算的指标列表（用户请求的顶层指标）

        Returns:
            依赖图，格式为 {metric_key: [依赖的指标列表]}

        Example:
            >>> graph = analyzer.build_graph(['pump_efficiency'])
            >>> print(graph)
            {'pump_efficiency': ['pump_flow_rate', 'pump_head', 'pump_active_power'],
             'pump_head': ['pump_outlet_pressure', 'pump_inlet_pressure'],
             'pump_inlet_pressure': ['pool_liquid_level'],
             'pump_flow_rate': ['main_pipeline_flow_rate', 'pump_active_power', 'pump_frequency']}
        """
        graph: Dict[str, List[str]] = {}
        visited: Set[str] = set()  # 防止重复处理
        auto_expanded: Set[str] = set()  # 记录自动扩展的依赖
        user_requested = set(metrics)  # 用户明确请求的指标

        def expand_dependencies(metric: str) -> None:
            """递归扩展依赖"""
            # 如果已经处理过，跳过
            if metric in visited:
                return
            visited.add(metric)

            # 如果指标没有注册的计算方法
            if metric not in self._method_registry:
                ctx = self._context or {}
                logger.warning(
                    f"指标 {metric} 没有注册的计算方法",
                    extra={"extra_data": {
                        "metric": metric,
                        "metrics": list(metrics),
                        "泵站ID": ctx.get("station_id"),
                        "设备ID": ctx.get("device_id"),
                        "开始时间": ctx.get("start_time"),
                        "结束时间": ctx.get("end_time"),
                        "requested_metrics": ctx.get("requested_metrics"),
                    }}
                )
                graph[metric] = []
                return

            # 选择优先级最高的方法（已按priority DESC排序）
            method = self._method_registry[metric][0]
            dependencies = method['dependencies']

            # 将依赖添加到图中
            graph[metric] = dependencies

            # 记录日志
            if metric in user_requested:
                logger.debug(
                    f"指标 {metric} 使用方法 {method['method_code']}, 依赖: {dependencies}"
                )
            else:
                # 这是自动扩展的依赖
                auto_expanded.add(metric)
                logger.debug(
                    f"自动扩展依赖: {metric} 使用方法 {method['method_code']}, 依赖: {dependencies}"
                )

            # 递归扩展所有依赖
            for dep in dependencies:
                expand_dependencies(dep)

        # 从用户请求的指标开始扩展
        for metric in metrics:
            expand_dependencies(metric)

        # 记录自动扩展的依赖
        if auto_expanded:
            ctx = self._context or {}
            logger.info(
                f"自动扩展了 {len(auto_expanded)} 个间接依赖: {', '.join(sorted(auto_expanded))}",
                extra={"extra_data": {
                    "user_requested": list(user_requested),
                    "auto_expanded": list(sorted(auto_expanded)),
                    "total_metrics": len(graph),
                    "泵站ID": ctx.get("station_id"),
                    "设备ID": ctx.get("device_id"),
                    "开始时间": ctx.get("start_time"),
                    "结束时间": ctx.get("end_time"),
                }}
            )

        return graph

    def topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        拓扑排序（Kahn算法）

        将有向无环图（DAG）转换为线性顺序。

        注意：图的格式是 {node: [dependencies]}，表示 node 依赖 dependencies。
        所以我们需要先计算 dependencies，再计算 node。

        Args:
            graph: 依赖图，格式为 {node: [dependencies]}

        Returns:
            拓扑排序后的指标列表（按计算顺序）

        Raises:
            CircularDependencyError: 如果检测到循环依赖

        Example:
            >>> graph = {'A': ['B'], 'B': ['C'], 'C': []}
            >>> order = analyzer.topological_sort(graph)
            >>> print(order)
            ['C', 'B', 'A']
        """
        # 计算入度（有多少节点依赖我）
        in_degree: Dict[str, int] = {node: 0 for node in graph}

        # 构建反向图（谁依赖我）
        reverse_graph: Dict[str, List[str]] = {node: [] for node in graph}
        for node in graph:
            for dep in graph[node]:
                if dep in graph:  # 只考虑在图中的依赖
                    reverse_graph[dep].append(node)
                    in_degree[node] += 1

        # 找到入度为0的节点（没有人依赖的节点，可以最先计算）
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []

        while queue:
            # 取出一个入度为0的节点
            node = queue.pop(0)
            result.append(node)

            # 遍历所有依赖当前节点的节点
            for dependent in reverse_graph[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # 检查是否有循环依赖
        if len(result) != len(graph):
            # 找出未被访问的节点（参与循环依赖的节点）
            unvisited = set(graph.keys()) - set(result)
            cycle = self.detect_circular_dependency(graph)
            if cycle:
                raise CircularDependencyError(
                    f"检测到循环依赖: {' → '.join(cycle)} → {cycle[0]}"
                )
            else:
                raise CircularDependencyError(
                    f"拓扑排序失败，未访问的节点: {unvisited}"
                )

        return result

    def detect_circular_dependency(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        检测循环依赖（DFS算法）

        使用深度优先搜索检测图中的环。

        Args:
            graph: 依赖图

        Returns:
            循环依赖的路径，如果没有循环则返回空列表

        Example:
            >>> graph = {'A': ['B'], 'B': ['C'], 'C': ['A']}
            >>> cycle = analyzer.detect_circular_dependency(graph)
            >>> print(cycle)
            ['A', 'B', 'C']
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            """深度优先搜索"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle = dfs(neighbor, path.copy())
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:]

            rec_stack.remove(node)
            return None

        for node in graph:
            if node not in visited:
                cycle = dfs(node, [])
                if cycle:
                    return cycle

        return []

    def find_strongly_connected_components(
        self,
        graph: Dict[str, List[str]]
    ) -> List[List[str]]:
        """
        使用Tarjan算法查找强连通分量（SCC）

        强连通分量是图中的最大子图，其中任意两个节点都可以相互到达。
        循环依赖组就是大小>1的强连通分量。

        Args:
            graph: 依赖图

        Returns:
            强连通分量列表，每个分量是一个节点列表

        Example:
            >>> graph = {'A': ['B'], 'B': ['C'], 'C': ['A'], 'D': ['E'], 'E': []}
            >>> sccs = analyzer.find_strongly_connected_components(graph)
            >>> print(sccs)
            [['A', 'B', 'C'], ['D'], ['E']]
        """
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = set()
        sccs = []

        def strongconnect(node: str):
            """Tarjan算法的递归函数"""
            # 设置节点的索引和lowlink
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack.add(node)

            # 遍历邻居节点
            for neighbor in graph.get(node, []):
                if neighbor not in index:
                    # 邻居未访问，递归访问
                    strongconnect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif neighbor in on_stack:
                    # 邻居在栈中，说明找到了环
                    lowlinks[node] = min(lowlinks[node], index[neighbor])

            # 如果node是SCC的根节点
            if lowlinks[node] == index[node]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == node:
                        break
                sccs.append(scc)

        # 对所有未访问的节点执行Tarjan算法
        for node in graph:
            if node not in index:
                strongconnect(node)

        return sccs

    def identify_circular_groups(
        self,
        graph: Dict[str, List[str]]
    ) -> Dict[str, Optional[str]]:
        """
        识别循环依赖组

        Args:
            graph: 依赖图

        Returns:
            字典，键为指标名，值为循环依赖组ID（如果不在循环中则为None）

        Example:
            >>> graph = {'A': ['B'], 'B': ['C'], 'C': ['A'], 'D': ['E'], 'E': []}
            >>> groups = analyzer.identify_circular_groups(graph)
            >>> print(groups)
            {'A': 'circular_0', 'B': 'circular_0', 'C': 'circular_0', 'D': None, 'E': None}
        """
        sccs = self.find_strongly_connected_components(graph)

        circular_groups = {}
        group_id = 0

        for scc in sccs:
            if len(scc) > 1:
                # 大小>1的SCC是循环依赖组
                group_name = f"circular_{group_id}"
                for node in scc:
                    circular_groups[node] = group_name
                group_id += 1

                logger.info(
                    f"检测到循环依赖组 {group_name}: {' ↔ '.join(sorted(scc))}",
                    extra={"group": group_name, "members": scc}
                )
            else:
                # 大小=1的SCC不是循环依赖
                circular_groups[scc[0]] = None

        return circular_groups

    def _get_order_with_circular_groups(
        self,
        graph: Dict[str, List[str]],
        circular_groups: Dict[str, Optional[str]]
    ) -> List[str]:
        """
        获取包含循环依赖组的计算顺序

        将循环依赖组视为单个节点，对缩减后的图进行拓扑排序。

        Args:
            graph: 依赖图
            circular_groups: 循环依赖组信息

        Returns:
            计算顺序列表
        """
        # 1. 构建组到成员的映射
        group_members: Dict[str, List[str]] = {}
        for metric, group in circular_groups.items():
            if group is not None:
                if group not in group_members:
                    group_members[group] = []
                group_members[group].append(metric)

        # 2. 构建缩减图（将循环依赖组视为单个节点）
        reduced_graph: Dict[str, List[str]] = {}

        for metric in graph:
            # 确定当前节点（可能是组或单个指标）
            current_group = circular_groups.get(metric)
            current_node = current_group if current_group else metric

            if current_node not in reduced_graph:
                reduced_graph[current_node] = []

            # 添加依赖
            for dep in graph[metric]:
                dep_group = circular_groups.get(dep)
                dep_node = dep_group if dep_group else dep

                # 跳过组内依赖
                if current_node != dep_node and dep_node not in reduced_graph[current_node]:
                    reduced_graph[current_node].append(dep_node)

        # 3. 对缩减图进行拓扑排序
        reduced_order = self.topological_sort(reduced_graph)

        # 4. 展开循环依赖组
        final_order = []
        for node in reduced_order:
            if node in group_members:
                # 这是一个循环依赖组，添加所有成员
                final_order.extend(sorted(group_members[node]))
            else:
                # 这是一个单独的指标
                final_order.append(node)

        return final_order

    def get_circular_group_info(
        self,
        metrics: List[str]
    ) -> Dict[str, List[str]]:
        """
        获取循环依赖组信息

        Args:
            metrics: 指标列表

        Returns:
            字典，键为组ID，值为组成员列表
        """
        graph = self.build_graph(metrics)
        circular_groups = self.identify_circular_groups(graph)

        group_info: Dict[str, List[str]] = {}
        for metric, group in circular_groups.items():
            if group is not None:
                if group not in group_info:
                    group_info[group] = []
                group_info[group].append(metric)

        return group_info

    def get_calculation_order(self, metrics: List[str], use_cache: bool = True) -> List[str]:
        """
        获取计算顺序

        优先从缓存/数据库读取，如果没有则动态计算并保存。

        Args:
            metrics: 需要计算的指标列表
            use_cache: 是否使用缓存（默认True）

        Returns:
            按计算顺序排列的指标列表

        Raises:
            CircularDependencyError: 如果检测到循环依赖

        Example:
            >>> order = analyzer.get_calculation_order(['pump_efficiency', 'pump_flow_rate', 'pump_head'])
            >>> print(order)
            ['pump_flow_rate', 'pump_head', 'pump_efficiency']
        """
        logger.info(
            "[流程-开始] [计算顺序分析]",
            extra={
                "extra_data": {
                    "metric_count": len(metrics),
                    "use_cache": use_cache,
                }
            },
        )

        # 1. 尝试从缓存读取
        if use_cache:
            cache_key = frozenset(metrics)
            if cache_key in self._calculation_order_cache:
                self._cache_hits += 1
                order = self._calculation_order_cache[cache_key]
                logger.debug(
                    f"从缓存读取计算顺序: {' → '.join(order)} "
                    f"(命中率: {self.get_cache_hit_rate():.1%})"
                )
                return order
            else:
                self._cache_misses += 1

        # 2. 尝试从数据库读取
        order = self.load_calculation_order_from_db(metrics)
        if order is not None:
            # 保存到缓存
            if use_cache:
                cache_key = frozenset(metrics)
                self._calculation_order_cache[cache_key] = order
            logger.debug(f"从数据库读取计算顺序: {' → '.join(order)}")
            return order

        # 3. 动态计算
        logger.info("[流程-阶段] [开始动态计算]")

        # 3.1 构建依赖图
        graph = self.build_graph(metrics)

        logger.info(
            "[流程-阶段] [依赖图构建完成]",
            extra={"extra_data": {"graph_nodes": len(graph)}},
        )

        # 3.2 识别循环依赖组
        circular_groups = self.identify_circular_groups(graph)

        # 检查是否有循环依赖
        has_circular = any(group is not None for group in circular_groups.values())

        if has_circular:
            # 有循环依赖，使用特殊处理
            ctx = self._context or {}
            logger.warning(
                f"检测到循环依赖，将使用迭代求解",
                extra={"extra_data": {
                    "circular_groups": circular_groups,
                    "泵站ID": ctx.get("station_id"),
                    "设备ID": ctx.get("device_id"),
                    "开始时间": ctx.get("start_time"),
                    "结束时间": ctx.get("end_time"),
                    "requested_metrics": ctx.get("requested_metrics"),
                }}
            )

            # 获取计算顺序（包含循环依赖组）
            order = self._get_order_with_circular_groups(graph, circular_groups)
        else:
            # 无循环依赖，使用拓扑排序
            order = self.topological_sort(graph)

        # 4. 保存到缓存和数据库
        if use_cache:
            cache_key = frozenset(metrics)
            self._calculation_order_cache[cache_key] = order

        # 自动保存到数据库（包含循环依赖信息）
        self.save_calculation_order(
            metrics, order,
            circular_groups=circular_groups,
            updated_by="auto"
        )

        logger.info(
            f"计算顺序生成完成: {' → '.join(order)}",
            extra={"order": order, "has_circular": has_circular}
        )

        return order

    def load_calculation_order_from_db(self, metrics: List[str]) -> Optional[List[str]]:
        """
        从数据库加载计算顺序（验证完整依赖链）

        Args:
            metrics: 需要计算的指标列表

        Returns:
            计算顺序列表，如果数据库中没有记录或依赖链不完整则返回None
        """
        try:
            # 首先构建完整的依赖图（包含自动扩展的依赖）
            graph = self.build_graph(metrics)
            all_required_metrics = set(graph.keys())  # 所有需要的指标（包括自动扩展的）

            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 查询所有需要的指标的计算顺序
                    query = """
                        SELECT metric_key, order_index, depends_on
                        FROM metric_calculation_order
                        WHERE metric_key = ANY(%s)
                        ORDER BY order_index
                    """
                    cur.execute(query, (list(all_required_metrics),))
                    rows = cur.fetchall()

                    if not rows:
                        logger.debug(f"数据库中没有找到计算顺序记录")
                        return None

                    # 检查是否所有指标都有记录（包括自动扩展的依赖）
                    db_metrics = {row[0] for row in rows}
                    missing_metrics = all_required_metrics - db_metrics
                    if missing_metrics:
                        logger.debug(
                            f"数据库中缺少部分指标的记录（包括自动扩展的依赖）: {missing_metrics}，将重新计算"
                        )
                        return None

                    # 验证依赖关系是否仍然有效
                    for metric_key, order_index, depends_on in rows:
                        current_deps = self.get_dependencies(metric_key)
                        db_deps = set(depends_on or [])
                        current_deps_set = set(current_deps)

                        if db_deps != current_deps_set:
                            ctx = self._context or {}
                            logger.warning(
                                f"指标 {metric_key} 的依赖关系已变化，数据库: {db_deps}, 当前: {current_deps_set}",
                                extra={"extra_data": {
                                    "指标键": metric_key,
                                    "泵站ID": ctx.get("station_id"),
                                    "设备ID": ctx.get("device_id"),
                                    "开始时间": ctx.get("start_time"),
                                    "结束时间": ctx.get("end_time"),
                                    "requested_metrics": ctx.get("requested_metrics"),
                                }}
                            )
                            return None

                    # 提取计算顺序
                    calculation_order = [row[0] for row in rows]

                    logger.info(
                        f"从数据库加载计算顺序（包含 {len(all_required_metrics)} 个指标）: {' → '.join(calculation_order)}",
                        extra={"order": calculation_order, "total_metrics": len(all_required_metrics)}
                    )

                    return calculation_order

        except Exception as e:
            logger.error(f"从数据库加载计算顺序失败: {e}", exc_info=True)
            return None

    def save_calculation_order(
        self,
        metrics: List[str],
        calculation_order: List[str],
        circular_groups: Dict[str, Optional[str]] = None,
        updated_by: str = "system"
    ) -> bool:
        """
        保存计算顺序到数据库

        Args:
            metrics: 需要计算的指标列表
            calculation_order: 计算顺序列表
            circular_groups: 循环依赖组信息（可选）
            updated_by: 更新者标识

        Returns:
            是否保存成功
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 预取有效的 metric_key（FK 约束目标）
                    cur.execute("SELECT metric_key FROM dim_metric_config")
                    valid_keys = {r[0] for r in cur.fetchall()}

                    # 使用UPSERT语法
                    upsert_query = """
                        INSERT INTO metric_calculation_order (
                            metric_key, depends_on, priority, order_index,
                            is_circular, circular_group, updated_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (metric_key)
                        DO UPDATE SET
                            depends_on = EXCLUDED.depends_on,
                            priority = EXCLUDED.priority,
                            order_index = EXCLUDED.order_index,
                            is_circular = EXCLUDED.is_circular,
                            circular_group = EXCLUDED.circular_group,
                            updated_at = CURRENT_TIMESTAMP,
                            updated_by = EXCLUDED.updated_by
                    """

                    # 准备数据（仅保存 dim_metric_config 中存在的指标，避免 FK 违反）
                    rows = []
                    skipped: list[str] = []
                    for idx, metric_key in enumerate(calculation_order):
                        if metric_key not in metrics:
                            continue
                        if metric_key not in valid_keys:
                            skipped.append(metric_key)
                            continue

                        depends_on = self.get_dependencies(metric_key)
                        priority = idx  # 使用索引作为优先级
                        order_index = idx

                        # 确定是否属于循环依赖
                        if circular_groups and metric_key in circular_groups:
                            circular_group = circular_groups[metric_key]
                            is_circular = circular_group is not None
                        else:
                            is_circular = False
                            circular_group = None

                        rows.append((
                            metric_key,
                            depends_on,
                            priority,
                            order_index,
                            is_circular,
                            circular_group,
                            updated_by
                        ))

                    # 批量插入
                    if rows:
                        cur.executemany(upsert_query, rows)
                        conn.commit()

                    if skipped:
                        logger.warning(
                            "部分指标未写入 metric_calculation_order（在 dim_metric_config 中不存在，已跳过）",
                            extra={"extra_data": {"skipped": skipped}}
                        )

                    logger.info(
                        f"保存计算顺序到数据库: {len(rows)} 个指标",
                        extra={"metric_count": len(rows)}
                    )

                    return True

        except Exception as e:
            logger.error(
                f"保存计算顺序到数据库失败: {e}",
                exc_info=True,
                extra={"metrics": metrics, "order": calculation_order}
            )
            return False

    def get_dependencies(self, metric_key: str) -> List[str]:
        """
        获取指定指标的依赖列表

        Args:
            metric_key: 指标键

        Returns:
            依赖的指标列表
        """
        if metric_key not in self._method_registry:
            return []

        # 返回优先级最高的方法的依赖
        method = self._method_registry[metric_key][0]
        return method['dependencies']

    def update_calculation_order(
        self,
        metrics: List[str],
        new_order: List[str],
        updated_by: str = "manual"
    ) -> bool:
        """
        手动更新计算顺序

        验证新顺序是否满足依赖关系，如果满足则保存到数据库和缓存。

        Args:
            metrics: 需要计算的指标列表
            new_order: 新的计算顺序
            updated_by: 更新者标识

        Returns:
            是否更新成功
        """
        # 1. 验证新顺序包含所有指标
        if set(new_order) != set(metrics):
            logger.error(f"新顺序的指标集合与原指标集合不一致")
            return False

        # 2. 验证依赖关系
        for idx, metric_key in enumerate(new_order):
            deps = self.get_dependencies(metric_key)
            for dep in deps:
                if dep not in new_order:
                    continue
                dep_idx = new_order.index(dep)
                if dep_idx >= idx:
                    logger.error(
                        f"依赖关系违反: {metric_key} 依赖 {dep}, "
                        f"但 {dep} 在 {metric_key} 之后"
                    )
                    return False

        # 3. 保存到数据库
        success = self.save_calculation_order(metrics, new_order, updated_by)
        if not success:
            return False

        # 4. 更新缓存
        cache_key = frozenset(metrics)
        self._calculation_order_cache[cache_key] = new_order

        logger.info(
            f"手动更新计算顺序成功: {' → '.join(new_order)}",
            extra={"order": new_order, "updated_by": updated_by}
        )

        return True

    def clear_cache(self) -> None:
        """清空缓存"""
        self._calculation_order_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("计算顺序缓存已清空")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息

        Returns:
            缓存统计字典
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0

        return {
            'cache_size': len(self._calculation_order_cache),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'total_queries': total,
            'hit_rate': hit_rate
        }

    def get_cache_hit_rate(self) -> float:
        """
        获取缓存命中率

        Returns:
            命中率（0.0-1.0）
        """
        total = self._cache_hits + self._cache_misses
        return self._cache_hits / total if total > 0 else 0.0

    def refresh(self) -> None:
        """刷新方法注册表和缓存"""
        logger.info("DependencyAnalyzer 刷新")
        self._method_registry.clear()
        self._calculation_order_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._load_methods_from_db()

