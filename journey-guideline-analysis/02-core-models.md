# 核心数据模型分析

## Guideline 数据模型

### GuidelineContent
```python
@dataclass(frozen=True)
class GuidelineContent:
    condition: str          # 触发条件
    action: Optional[str]   # 执行动作（可选）
```

### Guideline
```python
@dataclass(frozen=True)
class Guideline:
    id: GuidelineId                              # 唯一标识符
    creation_utc: datetime                       # 创建时间
    content: GuidelineContent                    # 内容（条件+动作）
    enabled: bool                                # 是否启用
    tags: Sequence[TagId]                        # 标签列表
    metadata: Mapping[str, JSONSerializable]     # 元数据
```

**关键特性**:
- 不可变数据类 (`frozen=True`)
- 支持标签分类
- 灵活的元数据存储
- 可以只有条件（观察型）或条件+动作（行动型）

## Journey 数据模型

### Journey
```python
@dataclass(frozen=True)
class Journey:
    id: JourneyId                      # 唯一标识符
    creation_utc: datetime             # 创建时间
    description: str                   # 描述
    conditions: Sequence[GuidelineId]  # 激活条件（Guideline IDs）
    title: str                         # 标题
    root_id: JourneyNodeId            # 根节点ID
    tags: Sequence[TagId]             # 标签列表
```

### JourneyNode
```python
@dataclass(frozen=True)
class JourneyNode:
    id: JourneyNodeId                           # 节点ID
    creation_utc: datetime                      # 创建时间
    action: Optional[str]                       # 节点动作
    tools: Sequence[ToolId]                     # 关联的工具
    metadata: Mapping[str, JSONSerializable]    # 元数据
```

**节点类型** (通过 metadata 中的 `kind` 字段):
- `FORK`: 分支节点，无实际动作
- `CHAT`: 对话节点，需要 Agent 响应
- `TOOL`: 工具调用节点
- `NA`: 未分类

### JourneyEdge
```python
@dataclass(frozen=True)
class JourneyEdge:
    id: JourneyEdgeId                           # 边ID
    creation_utc: datetime                      # 创建时间
    source: JourneyNodeId                       # 源节点
    target: JourneyNodeId                       # 目标节点
    condition: Optional[str]                    # 转换条件
    metadata: Mapping[str, JSONSerializable]    # 元数据
```

## 关联关系

### Journey ↔ Guideline
- Journey 通过 `conditions` 字段存储 Guideline ID 列表
- 这些 Guideline 定义了 Journey 的激活条件
- Journey 删除时，如果 Guideline 仅属于该 Journey，则一并删除

### Journey ↔ Tag
- Journey 可以有多个标签
- 通过 `JourneyTagAssociationDocument` 存储关联
- 支持按标签查询 Journey

### Guideline ↔ Tool
- Guideline 可以关联多个工具
- 通过 `GuidelineToolAssociation` 存储关联
- 当 Guideline 匹配时，可以自动调用关联的工具
