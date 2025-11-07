# Journey 到 Guideline 的投影机制

## JourneyGuidelineProjection 类

### 核心概念

Journey 是一个图结构，但引擎处理的是 Guideline 列表。`JourneyGuidelineProjection` 负责将 Journey 的图结构"投影"为一组 Guideline，使引擎能够处理 Journey。

### 类定义

```python
class JourneyGuidelineProjection:
    def __init__(
        self,
        journey_store: JourneyStore,
        guideline_store: GuidelineStore,
    ) -> None:
        self._journey_store = journey_store
        self._guideline_store = guideline_store
```

### 核心方法：project_journey_to_guidelines

```python
async def project_journey_to_guidelines(
    self,
    journey_id: JourneyId,
) -> Sequence[Guideline]
```

#### 投影算法

**1. 数据准备**
```python
journey = await self._journey_store.read_journey(journey_id)
edges_objs = await self._journey_store.list_edges(journey_id)
nodes = {n.id: n for n in await self._journey_store.list_nodes(journey_id)}
edges = {e.id: e for e in edges_objs}
node_edges: dict[JourneyNodeId, list[JourneyEdge]] = defaultdict(list)
```

**2. 构建节点索引**
- 为每个节点分配一个索引号
- 用于在 Guideline 元数据中标识节点位置

**3. 创建 Guideline**

对于每个 (edge, node) 对，创建一个 Guideline:

```python
def make_guideline(
    edge: JourneyEdge | None,
    node: JourneyNode,
) -> Guideline:
    # 合并元数据
    merged_journey_node = {
        **base_journey_node,
        **node_journey_node,
        **edge_journey_node,
    }
    
    return Guideline(
        id=format_journey_node_guideline_id(node.id, edge.id if edge else None),
        content=GuidelineContent(
            condition=edge.condition if edge and edge.condition else "",
            action=node.action,
        ),
        creation_utc=datetime.now(timezone.utc),
        enabled=True,
        tags=[],
        metadata=metadata,
    )
```

**4. 广度优先遍历**

```python
queue: deque[tuple[JourneyEdgeId | None, JourneyNodeId]] = deque()
queue.append((None, journey.root_id))

while queue:
    edge_id, node_id = queue.popleft()
    new_guideline = make_guideline(edges[edge_id] if edge_id else None, nodes[node_id])
    guidelines[new_guideline.id] = new_guideline
    
    for edge in node_edges[node_id]:
        queue.append((edge.id, edge.target))
        add_edge_guideline_metadata(new_guideline.id, ...)
```

**5. 构建 follow_ups 关系**

在元数据中记录每个节点的后续节点:
```python
def add_edge_guideline_metadata(
    guideline_id: GuidelineId, 
    edge_guideline_id: GuidelineId
) -> None:
    guidelines[guideline_id].metadata["journey_node"]["follow_ups"].append(edge_guideline_id)
```

### Guideline ID 格式

```python
def format_journey_node_guideline_id(
    node_id: JourneyNodeId,
    edge_id: Optional[JourneyEdgeId] = None,
) -> GuidelineId:
    if edge_id:
        return GuidelineId(f"journey_node:{node_id}:{edge_id}")
    return GuidelineId(f"journey_node:{node_id}")
```

**格式**: `journey_node:<node_id>[:<edge_id>]`

### 元数据结构

投影生成的 Guideline 包含以下元数据:

```python
{
    "journey_node": {
        "follow_ups": ["journey_node:2:edge1", "journey_node:3:edge2"],
        "index": "1",
        "journey_id": "journey_123",
        "kind": "chat",  # 或 "tool", "fork", "NA"
        # ... 其他节点/边的元数据
    },
    # ... 其他顶层元数据
}
```

### 投影示例

**原始 Journey**:
```
Root (index=1)
  ├─[condition: "用户询问价格"]→ Node2 (index=2, action: "查询价格")
  └─[condition: "用户询问库存"]→ Node3 (index=3, action: "查询库存")
```

**投影后的 Guideline**:

1. **Guideline 1** (Root):
   - ID: `journey_node:root_id`
   - Condition: ""
   - Action: "<<JOURNEY ROOT: start the journey...>>"
   - Metadata: `{"journey_node": {"follow_ups": ["journey_node:node2_id:edge1_id", "journey_node:node3_id:edge2_id"], "index": "1", ...}}`

2. **Guideline 2**:
   - ID: `journey_node:node2_id:edge1_id`
   - Condition: "用户询问价格"
   - Action: "查询价格"
   - Metadata: `{"journey_node": {"follow_ups": [], "index": "2", ...}}`

3. **Guideline 3**:
   - ID: `journey_node:node3_id:edge2_id`
   - Condition: "用户询问库存"
   - Action: "查询库存"
   - Metadata: `{"journey_node": {"follow_ups": [], "index": "3", ...}}`

### 辅助函数

#### 从 Guideline ID 提取 Node ID
```python
def extract_node_id_from_journey_node_guideline_id(
    guideline_id: GuidelineId,
) -> JourneyNodeId:
    parts = guideline_id.split(":")
    if len(parts) < 2 or parts[0] != "journey_node":
        raise ValueError(f"Invalid guideline ID format: {guideline_id}")
    return JourneyNodeId(parts[1])
```

## 投影的用途

1. **引擎处理**: 引擎可以像处理普通 Guideline 一样处理 Journey
2. **路径跟踪**: 通过 `follow_ups` 元数据跟踪 Journey 路径
3. **状态管理**: 通过 `index` 和 `journey_id` 管理 Journey 执行状态
4. **类型识别**: 通过 `kind` 区分不同类型的节点


## 相关文档

### 实际运行示例
- [11-weather-agent-startup-flow.md](./11-weather-agent-startup-flow.md) - Journey 创建和投影示例
- [12-weather-agent-request-flow.md](./12-weather-agent-request-flow.md) - 投影后的 Guideline 使用示例
- [14-method-call-chains.md](./14-method-call-chains.md) - 投影方法调用链

### 相关机制
- [07-engine-integration.md](./07-engine-integration.md) - 投影后的节点选择
- [08-complete-flow.md](./08-complete-flow.md) - 投影在完整流程中的位置
- [02-core-models.md](./02-core-models.md) - Journey 和 Guideline 数据模型
