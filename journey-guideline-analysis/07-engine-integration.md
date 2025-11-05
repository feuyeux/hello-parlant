# 引擎层集成分析

## GuidelineMatcher

### 核心职责
- 匹配适用的 Guideline
- 分析响应质量
- 支持多种匹配策略

### 类结构

```python
class GuidelineMatcher:
    def __init__(
        self,
        logger: Logger,
        meter: Meter,
        strategy_resolver: GuidelineMatchingStrategyResolver,
    ) -> None
```

### 关键方法

#### match_guidelines
```python
async def match_guidelines(
    self,
    context: EngineContext,
    active_journeys: Sequence[Journey],
    guidelines: Sequence[Guideline],
) -> GuidelineMatchingResult
```

**输入**:
- `context`: 引擎上下文（Agent、Session、Customer 等）
- `active_journeys`: 当前激活的 Journey 列表
- `guidelines`: 待匹配的 Guideline 列表

**流程**:
1. 根据 Guideline 类型解析匹配策略
2. 为每种策略创建匹配批次
3. 并行处理所有批次
4. 应用策略转换
5. 返回匹配结果

**输出**:
```python
@dataclass(frozen=True)
class GuidelineMatchingResult:
    total_duration: float
    batch_count: int
    batch_generations: Sequence[GenerationInfo]
    batches: Sequence[Sequence[GuidelineMatch]]
    matches: Sequence[GuidelineMatch]
```

### GuidelineMatchingContext

传递给匹配批次的上下文:
```python
@dataclass(frozen=True)
class GuidelineMatchingContext:
    agent: Agent
    session: Session
    customer: Customer
    context_variables: Sequence[tuple[ContextVariable, ContextVariableValue]]
    interaction_history: Sequence[Event]
    terms: Sequence[Term]
    capabilities: Sequence[Capability]
    staged_events: Sequence[EmittedEvent]
    active_journeys: Sequence[Journey]
    journey_paths: dict[JourneyId, list[Optional[GuidelineId]]]
```

**关键字段**:
- `active_journeys`: 当前激活的 Journey
- `journey_paths`: 每个 Journey 的执行路径

## JourneyNodeSelectionBatch

### 核心职责
- 为 Journey 选择下一个要执行的节点
- 跟踪 Journey 执行路径
- 处理节点转换逻辑

### 类结构

```python
class GenericJourneyNodeSelectionBatch(GuidelineMatchingBatch):
    def __init__(
        self,
        logger: Logger,
        meter: Meter,
        guideline_store: GuidelineStore,
        optimization_policy: OptimizationPolicy,
        schematic_generator: SchematicGenerator[JourneyNodeSelectionSchema],
        examined_journey: Journey,
        context: GuidelineMatchingContext,
        node_guidelines: Sequence[Guideline] = [],
        journey_path: Sequence[str | None] = [],
    ) -> None
```

### 节点包装器

#### _JourneyNode
```python
@dataclass
class _JourneyNode:
    id: str
    action: str | None
    incoming_edges: list[_JourneyEdge]
    outgoing_edges: list[_JourneyEdge]
    kind: JourneyNodeKind
    customer_dependent_action: bool
    customer_action_description: Optional[str] = None
    agent_dependent_action: Optional[bool] = None
    agent_action_description: Optional[str] = None
```

#### _JourneyEdge
```python
@dataclass
class _JourneyEdge:
    target_guideline: Guideline | None
    condition: str | None
    source_node_index: str
    target_node_index: str
```

### 节点类型

```python
class JourneyNodeKind(Enum):
    FORK = "fork"      # 分支节点，无动作
    CHAT = "chat"      # 对话节点
    TOOL = "tool"      # 工具调用节点
    NA = "NA"          # 未分类
```

### 步骤完成状态

```python
class StepCompletionStatus(Enum):
    COMPLETED = "completed"
    NEEDS_CUSTOMER_INPUT = "needs_customer_input"
    NEEDS_AGENT_ACTION = "needs_agent_action"
    NEEDS_TOOL_CALL = "needs_tool_call"
```

### 核心处理流程

#### 1. 自动返回匹配
```python
def auto_return_match(self) -> GuidelineMatchingBatchResult | None:
    if self._previous_path and self._previous_path[-1] in self._node_wrappers:
        last_visited_node = self._node_wrappers[self._previous_path[-1]]
        if (
            last_visited_node.kind == JourneyNodeKind.TOOL
            and len(last_visited_node.outgoing_edges) == 1
        ):
            # 自动选择工具节点的唯一后续节点
            return GuidelineMatchingBatchResult(...)
```

**优化**: 如果上一个节点是工具节点且只有一个出边，直接返回，无需 LLM 推理

#### 2. 构建节点包装器
```python
def build_node_wrappers(guidelines: Sequence[Guideline]) -> dict[str, _JourneyNode]:
    # 1. 从 Guideline 元数据提取节点信息
    # 2. 构建节点字典
    # 3. 构建边并关联到节点
    # 4. 处理根节点特殊情况
```

#### 3. 节点剪枝
```python
def get_pruned_nodes(
    nodes: dict[str, _JourneyNode],
    previous_path: Sequence[str | None],
    max_depth: int,
) -> dict[str, _JourneyNode]:
    # 从当前路径开始，BFS 遍历 max_depth 层
    # 工具节点不继续展开
    # 返回剪枝后的节点集
```

**目的**: 减少 LLM 需要处理的节点数量，提高效率

#### 4. 生成转换图文本
```python
def get_journey_transition_map_text(
    nodes: dict[str, _JourneyNode],
    journey_title: str,
    journey_description: str = "",
    journey_conditions: Sequence[Guideline] = [],
    previous_path: Sequence[str | None] = [],
    print_customer_action_description: bool = False,
    to_prune: bool = False,
    max_depth: int = 5,
) -> str
```

**输出示例**:
```
Journey: 客户服务流程
Journey activation condition: "客户需要帮助" OR "客户有问题"

Steps:
STEP 1: 询问客户需求
Step Flags:
- BEGIN HERE: Begin the journey advancement at this step.
- CUSTOMER DEPENDENT: This action requires an action from the customer.
TRANSITIONS:
↳ If "客户说明了需求" → Go to step 2
↳ If "客户不清楚需求" → Go to step 3

STEP 2: 提供解决方案
Step Flags:
- REQUIRES AGENT ACTION: This step may require the agent to say something.
TRANSITIONS:
↳ If "解决方案已提供" → RETURN 'NONE'
```

#### 5. LLM 推理
```python
async def process(self) -> GuidelineMatchingBatchResult:
    # 1. 检查是否可以自动返回
    # 2. 构建 prompt
    # 3. 调用 LLM 生成
    # 4. 验证节点推进路径
    # 5. 返回匹配的 Guideline
```

### 推理 Schema

```python
class JourneyNodeSelectionSchema(DefaultBaseModel):
    rationale: str | None = None
    journey_applies: bool | None = None
    requires_backtracking: bool | None = None
    backtracking_target_step: str | None = None
    step_advancement: Sequence[JourneyNodeAdvancement] | None = None
    next_step: str | None = None
```

**字段说明**:
- `rationale`: 选择理由
- `journey_applies`: Journey 是否适用
- `requires_backtracking`: 是否需要回溯
- `backtracking_target_step`: 回溯目标步骤
- `step_advancement`: 步骤推进序列
- `next_step`: 下一个要执行的步骤

### 路径验证

```python
def _get_verified_node_advancement(
    self, response: JourneyNodeSelectionSchema
) -> list[str | None]:
    # 1. 构建路径
    # 2. 验证回溯合法性
    # 3. 验证转换合法性
    # 4. 修复非法路径
    # 5. 返回验证后的路径
```

**验证规则**:
- 回溯只能到之前访问过的节点
- 转换必须沿着存在的边
- 不能跳过工具节点
- 分支节点不能作为最终步骤

## 集成流程

```
1. 引擎接收用户输入
   ↓
2. 加载激活的 Journey
   ↓
3. 将 Journey 投影为 Guideline
   ↓
4. GuidelineMatcher.match_guidelines()
   ├─ 创建 JourneyNodeSelectionBatch
   ├─ 构建节点包装器
   ├─ 剪枝节点
   ├─ 生成转换图文本
   ├─ LLM 推理选择下一步
   └─ 返回匹配的 Guideline
   ↓
5. 引擎执行 Guideline 的 action
   ↓
6. 更新 Journey 路径
   ↓
7. 返回响应给用户
```
