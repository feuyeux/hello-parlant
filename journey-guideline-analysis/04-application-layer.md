# 应用层模块分析

## GuidelineModule

### 职责
- 封装 Guideline 的业务逻辑
- 管理 Guideline 与其他实体的关系
- 提供高层次的 API

### 依赖注入
```python
def __init__(
    self,
    logger: Logger,
    guideline_store: GuidelineStore,
    tag_store: TagStore,
    agent_store: AgentStore,
    journey_store: JourneyStore,
    relationship_store: RelationshipStore,
    guideline_tool_association_store: GuidelineToolAssociationStore,
    service_registry: ServiceRegistry,
)
```

### 核心方法

#### 创建 Guideline
```python
async def create(
    self,
    condition: str,
    action: str | None,
    metadata: Mapping[str, JSONSerializable] | None,
    enabled: bool | None,
    tags: Sequence[TagId] | None,
) -> Guideline
```

**额外逻辑**:
- 验证标签存在性（Agent、Journey 或普通 Tag）
- 去重标签

#### 更新 Guideline
```python
async def update(
    self,
    guideline_id: GuidelineId,
    condition: str | None,
    action: str | None,
    tool_associations: GuidelineToolAssociationUpdateParams | None,
    enabled: bool | None,
    tags: GuidelineTagsUpdateParams | None,
    metadata: GuidelineMetadataUpdateParams | None,
) -> Guideline
```

**支持的更新**:
- 基本属性（condition, action, enabled）
- 元数据（增量更新）
- 工具关联（添加/删除）
- 标签（添加/删除）

#### 删除 Guideline
```python
async def delete(self, guideline_id: GuidelineId) -> None
```

**级联操作**:
1. 删除相关的关系（Relationships）
2. 删除工具关联
3. 从 Journey 的条件中移除
4. 删除 Guideline 本身

#### 查找关系
```python
async def find_relationships(
    self,
    guideline_id: GuidelineId,
    include_indirect: bool = True,
) -> Sequence[tuple[GuidelineRelationship, bool]]
```

**关系类型**:
- ENTAILMENT: 蕴含关系
- PRIORITY: 优先级关系
- DEPENDENCY: 依赖关系
- DISAMBIGUATION: 消歧关系
- REEVALUATION: 重新评估关系

## JourneyModule

### 职责
- 封装 Journey 的业务逻辑
- 管理 Journey 与 Guideline 的关联
- 提供 Journey 图结构的访问

### 依赖注入
```python
def __init__(
    self,
    logger: Logger,
    journey_store: JourneyStore,
    guideline_store: GuidelineStore,
)
```

### 核心方法

#### 创建 Journey
```python
async def create(
    self,
    title: str,
    description: str,
    conditions: Sequence[str],  # 条件文本列表
    tags: Sequence[TagId] | None,
) -> tuple[Journey, Sequence[Guideline]]
```

**流程**:
1. 为每个条件文本创建 Guideline
2. 创建 Journey，关联这些 Guideline
3. 为每个 Guideline 添加 Journey 专属标签
4. 返回 Journey 和创建的 Guideline 列表

**Journey 标签**: `Tag.for_journey_id(journey_id)` 生成特殊标签

#### 读取 Journey 图
```python
async def read(self, journey_id: JourneyId) -> JourneyGraph
```

返回 `JourneyGraph`:
```python
@dataclass(frozen=True)
class JourneyGraph:
    journey: Journey
    nodes: Sequence[JourneyNode]
    edges: Sequence[JourneyEdge]
```

#### 更新 Journey
```python
async def update(
    self,
    journey_id: JourneyId,
    title: str | None,
    description: str | None,
    conditions: JourneyConditionUpdateParams | None,
    tags: JourneyTagUpdateParams | None,
) -> Journey
```

**条件更新逻辑**:
- **添加条件**: 
  1. 添加到 Journey
  2. 为 Guideline 添加 Journey 标签
- **删除条件**:
  1. 从 Journey 移除
  2. 如果 Guideline 只有该 Journey 标签，删除 Guideline
  3. 否则只移除标签

#### 删除 Journey
```python
async def delete(self, journey_id: JourneyId) -> None
```

**级联操作**:
1. 删除 Journey 本身
2. 对每个条件 Guideline:
   - 如果没有其他 Journey 使用，删除 Guideline
   - 如果只有该 Journey 标签，删除 Guideline
   - 否则只移除 Journey 标签
