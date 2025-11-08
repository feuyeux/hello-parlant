# Journey 和 Guideline 运行机制
## 基于天气查询代理的完整示例

本指南通过 `weather_agent.py` 这个具体示例，展示如何使用 Journey 和 Guideline 构建一个实用的对话代理。

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念实战](#核心概念实战)
3. [数据模型详解](#数据模型详解)
4. [创建 Journey 流程](#创建-journey-流程)
5. [执行 Journey 流程](#执行-journey-流程)
6. [投影机制详解](#投影机制详解)
7. [最佳实践](#最佳实践)
8. [常见问题](#常见问题)

---

## 快速开始

### 天气代理示例概览

天气代理是一个简单但完整的示例，展示了如何：
- 定义工具函数（查询天气）
- 创建多步骤 Journey（询问城市 → 查询天气 → 展示结果）
- 设置全局和局部 Guideline
- 处理成功和失败场景

### 运行示例

```bash
python journey-guideline-analysis/weather_agent.py
```


---

## 核心概念实战

### 1. Guideline（指南）

**定义**: 条件-动作规则，告诉 Agent 在特定情况下该做什么。

#### 示例：全局 Guideline

```python
# 来自 weather_agent.py
await agent.create_guideline(
    condition="用户问候",
    action="友好回应，简单介绍自己可以查询天气，支持的城市包括：北京、上海、广州、成都、深圳、杭州等"
)
```

**对应的数据模型**:
```python
Guideline(
    id="guideline_abc123",
    content=GuidelineContent(
        condition="用户问候",
        action="友好回应，简单介绍自己可以查询天气..."
    ),
    enabled=True,
    tags=[],
    metadata={}
)
```

**工作原理**:
1. 用户发送消息："你好"
2. 引擎匹配到这个 Guideline（条件匹配）
3. Agent 执行 action 中的指令
4. 返回友好的问候和介绍


#### 示例：Journey 内的 Guideline

```python
# 来自 weather_agent.py
await journey.create_guideline(
    condition="用户输入的城市名称不清晰或有歧义",
    action="礼貌地请用户确认具体是哪个城市"
)
```

**特点**:
- 只在 Journey 激活时生效
- 用于处理 Journey 特定的场景
- 通过标签与 Journey 关联

---

### 2. Journey（旅程）

**定义**: 多步骤的对话流程，用有向图表示。

#### 天气查询 Journey 结构

```
初始状态 (INITIAL)
    ├─[用户消息中包含城市名称]→ 查询天气 (TOOL)
    │                                  ├─[查询成功]→ 展示结果 (CHAT)
    │                                  │                ↓
    │                                  │           询问继续 (CHAT)
    │                                  │          ├─[想继续]→ 查询天气
    │                                  │          └─[不想继续]→ END
    │                                  └─[查询失败]→ 提示可用城市 (CHAT)
    │                                                   ↓
    │                                              查询天气 (TOOL)
    └─[用户没有提到具体城市]→ 询问城市 (CHAT)
                                    ↓
                               查询天气 (TOOL)
```


#### 对应的代码

```python
# 来自 weather_agent.py
async def create_weather_journey(agent: p.Agent) -> p.Journey:
    # 1. 创建 Journey
    journey = await agent.create_journey(
        title="查询天气",
        description="帮助用户查询城市天气",
        conditions=["用户想查询天气", "用户提到城市名称"]
    )
    
    # 2. 定义转换：初始状态 → 查询天气（如果用户已提到城市）
    t1 = await journey.initial_state.transition_to(
        tool_state=get_weather,
        condition="用户消息中包含城市名称"
    )
    
    # 3. 定义转换：初始状态 → 询问城市（如果用户没提到城市）
    t2 = await journey.initial_state.transition_to(
        chat_state="友好地询问用户想查询哪个城市的天气",
        condition="用户没有提到具体城市"
    )
    
    # 4. 定义转换：询问城市 → 查询天气
    t3 = await t2.target.transition_to(tool_state=get_weather)
    
    # ... 更多转换定义
    
    return journey
```


---

## 数据模型详解

### Journey 数据模型（以天气查询为例）

#### Journey 对象

```python
Journey(
    id="journey_weather_001",
    creation_utc=datetime(2025, 11, 5, 10, 0, 0),
    title="查询天气",
    description="帮助用户查询城市天气",
    conditions=[
        "guideline_condition_001",  # "用户想查询天气"
        "guideline_condition_002"   # "用户提到城市名称"
    ],
    root_id="node_initial",
    tags=["weather", "query"]
)
```

**字段说明**:
- `id`: Journey 的唯一标识符
- `conditions`: 激活条件（Guideline ID 列表）
- `root_id`: 根节点 ID（初始状态）
- `tags`: 标签，用于分类和查询


#### JourneyNode 对象（节点）

**示例 1: 初始节点**
```python
JourneyNode(
    id="node_initial",
    creation_utc=datetime(2025, 11, 5, 10, 0, 0),
    action="<<JOURNEY ROOT: start the journey...>>",
    tools=[],
    metadata={
        "kind": "FORK"  # 分支节点
    }
)
```

**示例 2: 对话节点**
```python
JourneyNode(
    id="node_ask_city",
    creation_utc=datetime(2025, 11, 5, 10, 0, 1),
    action="友好地询问用户想查询哪个城市的天气",
    tools=[],
    metadata={
        "kind": "CHAT"  # 对话节点
    }
)
```

**示例 3: 工具节点**
```python
JourneyNode(
    id="node_get_weather",
    creation_utc=datetime(2025, 11, 5, 10, 0, 2),
    action=None,  # 工具节点通常没有 action
    tools=["get_weather"],  # 关联的工具
    metadata={
        "kind": "TOOL"  # 工具节点
    }
)
```

**节点类型**:
- `FORK`: 分支节点，无实际动作，用于路由
- `CHAT`: 对话节点，Agent 需要生成回复
- `TOOL`: 工具调用节点，执行特定工具
- `NA`: 未分类节点


#### JourneyEdge 对象（边）

**示例 1: 条件转换**
```python
JourneyEdge(
    id="edge_001",
    creation_utc=datetime(2025, 11, 5, 10, 0, 3),
    source="node_initial",
    target="node_get_weather",
    condition="用户消息中包含城市名称",
    metadata={}
)
```

**示例 2: 无条件转换**
```python
JourneyEdge(
    id="edge_002",
    creation_utc=datetime(2025, 11, 5, 10, 0, 4),
    source="node_ask_city",
    target="node_get_weather",
    condition=None,  # 无条件，自动转换
    metadata={}
)
```

**字段说明**:
- `source`: 源节点 ID
- `target`: 目标节点 ID
- `condition`: 转换条件（可选）
- 如果 `condition` 为 None，表示无条件转换


---

## 创建 Journey 流程

### 完整流程图

```
用户代码
    ↓
agent.create_journey()
    ↓
JourneyModule.create()
    ↓
├─ 为每个 condition 创建 Guideline
│  └─ GuidelineStore.create_guideline()
│      └─ 插入到 DocumentDatabase
│
├─ 创建 Journey
│  └─ JourneyStore.create_journey()
│      ├─ 生成 Journey ID
│      ├─ 创建根节点
│      ├─ 插入到 DocumentDatabase
│      └─ 向量化并插入到 VectorDatabase
│
└─ 为 Guideline 添加 Journey 标签
   └─ GuidelineStore.upsert_tag()
```


### 步骤详解

#### 步骤 1: 用户代码创建 Journey

```python
# 来自 weather_agent.py
journey = await agent.create_journey(
    title="查询天气",
    description="帮助用户查询城市天气",
    conditions=["用户想查询天气", "用户提到城市名称"]
)
```

#### 步骤 2: 应用层处理

```python
# src/parlant/core/app_modules/journeys.py
async def create(
    self,
    title: str,
    description: str,
    conditions: Sequence[str],
    tags: Sequence[TagId] | None,
) -> tuple[Journey, Sequence[Guideline]]:
    # 2.1 为每个条件创建 Guideline
    guidelines = []
    for condition in conditions:
        guideline = await self._guideline_store.create_guideline(
            condition=condition,
            action=None,  # 条件型 Guideline，没有 action
            tags=[],
        )
        guidelines.append(guideline)
    
    # 2.2 创建 Journey
    journey = await self._journey_store.create_journey(
        title=title,
        description=description,
        conditions=[g.id for g in guidelines],
        tags=tags,
    )
    
    # 2.3 为 Guideline 添加 Journey 标签
    for guideline in guidelines:
        await self._guideline_store.upsert_tag(
            guideline_id=guideline.id,
            tag_id=Tag.for_journey_id(journey.id),
        )
    
    return journey, guidelines
```

**关键点**:
- 每个 condition 字符串被转换为一个 Guideline
- 这些 Guideline 的 ID 存储在 Journey 的 `conditions` 字段
- 通过标签建立 Guideline 和 Journey 的关联


#### 步骤 3: 存储层处理

```python
# src/parlant/core/journeys.py
async def create_journey(
    self,
    title: str,
    description: str,
    conditions: Sequence[GuidelineId],
    creation_utc: Optional[datetime] = None,
    tags: Optional[Sequence[TagId]] = None,
) -> Journey:
    async with self._lock.writer_lock:
        # 3.1 生成 Journey ID（基于内容的哈希）
        journey_checksum = md5_checksum(f"{title}{description}{conditions}")
        journey_id = JourneyId(self._id_generator.generate(journey_checksum))
        
        # 3.2 生成根节点 ID
        journey_root_id = JourneyNodeId(
            self._id_generator.generate(f"{journey_id}root")
        )
        
        # 3.3 创建根节点
        root = JourneyNode(
            id=journey_root_id,
            creation_utc=creation_utc or datetime.now(timezone.utc),
            action="<<JOURNEY ROOT: start the journey...>>",
            tools=[],
            metadata={"kind": "FORK"},
        )
        
        # 3.4 插入根节点到数据库
        await self._node_association_collection.insert_one(
            document=self._serialize_node(root, journey_id)
        )
        
        # 3.5 创建 Journey 对象
        journey = Journey(
            id=journey_id,
            creation_utc=creation_utc or datetime.now(timezone.utc),
            title=title,
            description=description,
            conditions=conditions,
            root_id=journey_root_id,
            tags=tags or [],
        )
        
        # 3.6 组装内容用于向量化
        content = self.assemble_content(
            title=title,
            description=description,
            nodes=[root],
            edges=[],
        )
        
        # 3.7 插入到文档数据库
        await self._collection.insert_one(
            document=self._serialize(journey)
        )
        
        # 3.8 向量化并插入到向量数据库
        embedding = await self._embedder.embed(content)
        await self._vector_collection.insert_one(
            document={
                "id": journey_id,
                "content": content,
                "embedding": embedding,
            }
        )
        
        # 3.9 创建标签关联
        for tag_id in tags or []:
            await self._tag_association_collection.insert_one({
                "journey_id": journey_id,
                "tag_id": tag_id,
            })
        
        # 3.10 创建条件关联
        for condition in conditions:
            await self._condition_association_collection.insert_one({
                "journey_id": journey_id,
                "condition": condition,
            })
    
    return journey
```

**关键点**:
- 使用读写锁保证并发安全
- 同时写入文档数据库和向量数据库（双存储架构）
- 使用关联表管理标签和条件


#### 步骤 4: 添加节点和边

```python
# 来自 weather_agent.py
# 添加转换（自动创建节点和边）
t1 = await journey.initial_state.transition_to(
    tool_state=get_weather,
    condition="用户消息中包含城市名称"
)
```

**内部实现**:
```python
# SDK 内部
async def transition_to(
    self,
    tool_state=None,
    chat_state=None,
    condition=None,
):
    # 1. 创建目标节点
    if tool_state:
        node = await journey_store.create_node(
            journey_id=self.journey_id,
            action=None,
            tools=[tool_state.__name__],
            metadata={"kind": "TOOL"},
        )
    elif chat_state:
        node = await journey_store.create_node(
            journey_id=self.journey_id,
            action=chat_state,
            tools=[],
            metadata={"kind": "CHAT"},
        )
    
    # 2. 创建边
    edge = await journey_store.create_edge(
        journey_id=self.journey_id,
        source=self.node_id,
        target=node.id,
        condition=condition,
    )
    
    # 3. 返回转换对象
    return Transition(target=State(node.id), edge=edge)
```


---

## 执行 Journey 流程

`.venv/Lib/site-packages/parlant/core/application.py`

```python
    async def _process_session(self, session: Session) -> None:
        event_emitter = await self._event_emitter_factory.create_event_emitter(
            emitting_agent_id=session.agent_id,
            session_id=session.id,
        )

        await self._engine.process(
```

`.venv/Lib/site-packages/parlant/core/engines/alpha/engine.py`
```python
    async def process(
        self,
        context: Context,
        event_emitter: EventEmitter,
    ) -> bool:
        """Processes a context and emits new events as needed"""

        # Load the full relevant information from storage.
        loaded_context = await self._load_context(context, event_emitter)

    async def _do_process(
        self,
        context: LoadedContext,
    ) -> None:
    
    async def _run_preparation_iteration(
        self,
        context: LoadedContext,
        preamble_task: asyncio.Task[bool],
    ) -> _PreparationIterationResult:
        
    async def _run_initial_preparation_iteration(
        self,
        context: LoadedContext,
        preamble_task: asyncio.Task[bool],
    ) -> _PreparationIterationResult:
        
    async def _load_matched_guidelines_and_journeys(
        self,
        context: LoadedContext,
    ) -> _GuidelineAndJourneyMatchingResult:
        # Step 1: Retrieve the journeys likely to be activated for this agent
        # Step 2 : Retrieve all the guidelines for the context.
        # Step 3: Exclude guidelines whose prerequisite journeys are less likely to be activated
        # (everything beyond the first `top_k` journeys), and also remove all journey graph guidelines.
        # Removing these guidelines
        # matching pass fast and focused on the most likely flows.
        # Step 4: Filter the best matches out of those.
        
    async def _prune_low_prob_guidelines_and_all_graph(
        self,
        context: LoadedContext,
        relevant_journeys: Sequence[Journey],
        all_stored_guidelines: dict[GuidelineId, Guideline],
        top_k: int,
    ) -> tuple[list[Guideline], list[Journey]]:
```

`.venv/Lib/site-packages/parlant/core/entity_cq.py`

```python
    async def finds_journeys_for_context(
        self,
        agent_id: AgentId,
    ) -> Sequence[Journey]:
        
    async def sort_journeys_by_contextual_relevance(
        self,
        available_journeys: Sequence[Journey],
        query: str,
    ) -> Sequence[Journey]:
        
    async def find_guidelines_for_context(
        self,
        agent_id: AgentId,
        journeys: Sequence[Journey],
    ) -> Sequence[Guideline]:
```

`.venv/Lib/site-packages/parlant/core/journeys.py`

```python
    async def list_journeys(
        self,
        tags: Optional[Sequence[TagId]] = None,
        condition: Optional[GuidelineId] = None,
    ) -> Sequence[Journey]:
```

`.venv/Lib/site-packages/parlant/core/journey_guideline_projection.py`

```
    async def project_journey_to_guidelines(
        self,
        journey_id: JourneyId,
    ) -> Sequence[Guideline]:
```

`.venv/Lib/site-packages/parlant/core/engines/alpha/guideline_matching/guideline_matcher.py`

```
    async def match_guidelines(
        self,
        context: LoadedContext,
        active_journeys: Sequence[Journey],
        guidelines: Sequence[Guideline],
    ) -> GuidelineMatchingResult:
```



### 完整流程图

```
用户发送消息: "北京天气怎么样？"
    ↓
引擎接收消息
    ↓
查找激活的 Journey
    ├─ 向量搜索相关 Journey
    └─ 检查 conditions 是否匹配
    ↓
投影 Journey 为 Guideline
    ├─ 读取节点和边
    ├─ 广度优先遍历
    └─ 生成 Guideline 列表
    ↓
匹配 Guideline
    ├─ 创建 JourneyNodeSelectionBatch
    ├─ 构建节点包装器
    ├─ 剪枝节点
    ├─ 生成转换图文本
    └─ LLM 推理选择下一步
    ↓
执行选中的 Guideline
    ├─ 调用工具（如果是 TOOL 节点）
    └─ 生成回复（如果是 CHAT 节点）
    ↓
更新 Journey 路径
    └─ 记录当前位置
    ↓
返回响应给用户
```


### 步骤详解

#### 步骤 1: 查找激活的 Journey

```python
# 伪代码
async def find_active_journeys(
    query: str,
    available_journeys: list[Journey],
) -> list[Journey]:
    # 1.1 向量搜索
    embedding = await embedder.embed(query)
    similar_journeys = await vector_db.search(
        embedding=embedding,
        top_k=10,
    )
    
    # 1.2 检查条件
    active_journeys = []
    for journey in similar_journeys:
        # 读取 Journey 的 conditions（Guideline IDs）
        condition_guidelines = await guideline_store.read_many(
            journey.conditions
        )
        
        # 检查是否有条件匹配
        for guideline in condition_guidelines:
            if await match_condition(guideline.content.condition, query):
                active_journeys.append(journey)
                break
    
    return active_journeys
```

**示例**:
- 用户消息: "北京天气怎么样？"
- 向量搜索找到 "查询天气" Journey
- 检查条件: "用户想查询天气" ✓, "用户提到城市名称" ✓
- Journey 被激活


#### 步骤 2: 投影 Journey 为 Guideline

这是最关键的步骤，将图结构转换为 Guideline 列表。

```python
# src/parlant/core/journey_guideline_projection.py
async def project_journey_to_guidelines(
    self,
    journey_id: JourneyId,
) -> Sequence[Guideline]:
    # 2.1 读取 Journey 数据
    journey = await self._journey_store.read_journey(journey_id)
    nodes = await self._journey_store.list_nodes(journey_id)
    edges = await self._journey_store.list_edges(journey_id)
    
    # 2.2 构建索引
    nodes_dict = {n.id: n for n in nodes}
    edges_dict = {e.id: e for e in edges}
    node_edges = defaultdict(list)
    for edge in edges:
        node_edges[edge.source].append(edge)
    
    # 2.3 广度优先遍历
    guidelines = {}
    queue = deque([(None, journey.root_id)])
    node_index = 0
    
    while queue:
        edge_id, node_id = queue.popleft()
        node = nodes_dict[node_id]
        edge = edges_dict[edge_id] if edge_id else None
        
        # 2.4 创建 Guideline
        guideline = self._make_guideline(
            journey=journey,
            node=node,
            edge=edge,
            index=node_index,
        )
        guidelines[guideline.id] = guideline
        node_index += 1
        
        # 2.5 添加后续节点到队列
        for next_edge in node_edges[node_id]:
            queue.append((next_edge.id, next_edge.target))
            
            # 记录 follow_ups 关系
            follow_up_id = format_journey_node_guideline_id(
                next_edge.target, next_edge.id
            )
            guideline.metadata["journey_node"]["follow_ups"].append(
                follow_up_id
            )
    
    return list(guidelines.values())
```


**投影示例**（天气查询 Journey）:

原始图结构:
```
初始状态 (node_initial)
    ├─[edge_001: "用户消息中包含城市名称"]→ 查询天气 (node_get_weather)
    └─[edge_002: "用户没有提到具体城市"]→ 询问城市 (node_ask_city)
                                                ↓
                                           [edge_003: 无条件]
                                                ↓
                                           查询天气 (node_get_weather)
```

投影后的 Guideline 列表:

**Guideline 1** (根节点):
```python
Guideline(
    id="journey_node:node_initial",
    content=GuidelineContent(
        condition="",
        action="<<JOURNEY ROOT: start the journey...>>"
    ),
    metadata={
        "journey_node": {
            "journey_id": "journey_weather_001",
            "index": "0",
            "kind": "FORK",
            "follow_ups": [
                "journey_node:node_get_weather:edge_001",
                "journey_node:node_ask_city:edge_002"
            ]
        }
    }
)
```

**Guideline 2** (直接查询):
```python
Guideline(
    id="journey_node:node_get_weather:edge_001",
    content=GuidelineContent(
        condition="用户消息中包含城市名称",
        action=None  # TOOL 节点没有 action
    ),
    metadata={
        "journey_node": {
            "journey_id": "journey_weather_001",
            "index": "1",
            "kind": "TOOL",
            "tools": ["get_weather"],
            "follow_ups": []
        }
    }
)
```

**Guideline 3** (询问城市):
```python
Guideline(
    id="journey_node:node_ask_city:edge_002",
    content=GuidelineContent(
        condition="用户没有提到具体城市",
        action="友好地询问用户想查询哪个城市的天气"
    ),
    metadata={
        "journey_node": {
            "journey_id": "journey_weather_001",
            "index": "2",
            "kind": "CHAT",
            "follow_ups": ["journey_node:node_get_weather:edge_003"]
        }
    }
)
```

**Guideline 4** (询问后查询):
```python
Guideline(
    id="journey_node:node_get_weather:edge_003",
    content=GuidelineContent(
        condition=None,  # 无条件转换
        action=None
    ),
    metadata={
        "journey_node": {
            "journey_id": "journey_weather_001",
            "index": "3",
            "kind": "TOOL",
            "tools": ["get_weather"],
            "follow_ups": []
        }
    }
)
```


#### 步骤 3: 匹配 Guideline

```python
# src/parlant/core/engines/alpha/guideline_matching/guideline_matcher.py
async def match_guidelines(
    self,
    context: EngineContext,
    active_journeys: list[Journey],
    guidelines: list[Guideline],
) -> GuidelineMatchingResult:
    # 3.1 按类型分组
    journey_guidelines = [
        g for g in guidelines 
        if "journey_node" in g.metadata
    ]
    regular_guidelines = [
        g for g in guidelines 
        if "journey_node" not in g.metadata
    ]
    
    # 3.2 为每个 Journey 创建节点选择批次
    batches = []
    for journey in active_journeys:
        journey_path = context.state.journey_paths.get(journey.id, [])
        
        batch = JourneyNodeSelectionBatch(
            journey_id=journey.id,
            journey_path=journey_path,
            guidelines=[
                g for g in journey_guidelines 
                if g.metadata["journey_node"]["journey_id"] == journey.id
            ],
        )
        batches.append(batch)
    
    # 3.3 并行处理所有批次
    results = await asyncio.gather(*[
        batch.process(context) for batch in batches
    ])
    
    # 3.4 合并结果
    all_matches = []
    for result in results:
        all_matches.extend(result.matches)
    
    return GuidelineMatchingResult(matches=all_matches)
```


#### 步骤 4: 节点选择（JourneyNodeSelectionBatch）

这是最复杂的部分，使用 LLM 推理选择下一个节点。

```python
# src/parlant/core/engines/alpha/guideline_matching/generic/journey_node_selection_batch.py
class JourneyNodeSelectionBatch:
    async def process(
        self, 
        context: EngineContext
    ) -> GuidelineMatchingResult:
        # 4.1 构建节点包装器
        node_wrappers = self._build_node_wrappers()
        
        # 4.2 剪枝节点（只保留相关节点）
        pruned_nodes = self._get_pruned_nodes(
            node_wrappers=node_wrappers,
            journey_path=self.journey_path,
        )
        
        # 4.3 检查自动返回（如果只有一个后续节点）
        if len(pruned_nodes) == 1 and self._can_auto_return(pruned_nodes[0]):
            return self._auto_return_match(pruned_nodes[0])
        
        # 4.4 生成转换图文本
        transition_map_text = self._get_journey_transition_map_text(
            pruned_nodes
        )
        
        # 4.5 LLM 推理
        prompt = f"""
        当前对话上下文: {context.messages}
        
        可用的转换:
        {transition_map_text}
        
        请选择最合适的下一步。
        """
        
        response = await llm.generate(prompt)
        
        # 4.6 解析响应并验证路径
        selected_node = self._parse_llm_response(response)
        
        if self._is_valid_path(selected_node, self.journey_path):
            return GuidelineMatchingResult(
                matches=[GuidelineMatch(
                    guideline=selected_node.guideline,
                    metadata={
                        "journey_path": self.journey_path + [selected_node.id],
                        "step_selection_journey_id": self.journey_id,
                    }
                )]
            )
        
        return GuidelineMatchingResult(matches=[])
```


**节点剪枝示例**:

假设当前路径: `["node_initial"]`

所有节点:
```
1. journey_node:node_initial (当前位置)
2. journey_node:node_get_weather:edge_001 (follow_up)
3. journey_node:node_ask_city:edge_002 (follow_up)
4. journey_node:node_get_weather:edge_003 (不相关)
5. journey_node:node_show_result:edge_004 (不相关)
```

剪枝后的节点（只保留当前节点的 follow_ups）:
```
1. journey_node:node_get_weather:edge_001
2. journey_node:node_ask_city:edge_002
```

**转换图文本**:
```
可用的转换:
1. [条件: 用户消息中包含城市名称] → 查询天气 (TOOL: get_weather)
2. [条件: 用户没有提到具体城市] → 询问城市 (CHAT: 友好地询问用户想查询哪个城市的天气)
```

**LLM 推理**:
- 输入: 用户消息 "北京天气怎么样？"
- 分析: 消息中包含城市名称 "北京"
- 选择: 转换 1（查询天气）


#### 步骤 5: 执行 Guideline

```python
# 伪代码
async def execute_guideline(
    guideline: Guideline,
    context: EngineContext,
) -> str:
    # 5.1 获取节点类型
    kind = guideline.metadata.get("journey_node", {}).get("kind", "NA")
    
    if kind == "TOOL":
        # 5.2 执行工具
        tool_name = guideline.metadata["journey_node"]["tools"][0]
        tool = context.tools[tool_name]
        
        # 从用户消息中提取参数
        params = await extract_tool_params(
            tool=tool,
            message=context.current_message,
        )
        
        # 调用工具
        result = await tool(**params)
        
        # 示例: get_weather(location="北京")
        # 返回: {"success": True, "temperature": 15, "condition": "晴朗", ...}
        
        return result
    
    elif kind == "CHAT":
        # 5.3 生成对话回复
        action = guideline.content.action
        
        # 使用 LLM 生成回复
        prompt = f"""
        指令: {action}
        上下文: {context.messages}
        
        请生成合适的回复。
        """
        
        response = await llm.generate(prompt)
        
        # 示例: "您想查询哪个城市的天气呢？我可以查询北京、上海、广州等城市。"
        
        return response
    
    return ""
```


#### 步骤 6: 更新 Journey 路径

```python
# 更新路径以跟踪用户在 Journey 中的位置
context.state.journey_paths[journey_id] = [
    "node_initial",
    "node_get_weather"  # 新增
]
```

**路径的作用**:
- 跟踪用户在 Journey 中的当前位置
- 用于节点剪枝（只显示相关的下一步）
- 支持跨会话恢复（如果持久化）

---

## 投影机制详解

### 为什么需要投影？

**问题**: 引擎只能处理 Guideline 列表，但 Journey 是图结构。

**解决方案**: 将 Journey 图"投影"为 Guideline 列表。

### 投影的核心思想

```
Journey 图                    Guideline 列表
┌─────────┐                  ┌──────────────────┐
│  Node A │                  │ Guideline 1      │
│    ↓    │    投影          │ (Node A)         │
│  Node B │  ────────→       │ Guideline 2      │
│    ↓    │                  │ (Node B)         │
│  Node C │                  │ Guideline 3      │
└─────────┘                  │ (Node C)         │
                             └──────────────────┘
```


### 投影算法详解

#### 1. 广度优先遍历

```python
# 初始化队列
queue = deque()
queue.append((None, journey.root_id))  # (edge_id, node_id)

# 遍历
while queue:
    edge_id, node_id = queue.popleft()
    
    # 处理当前节点
    process_node(edge_id, node_id)
    
    # 添加后续节点
    for edge in node_edges[node_id]:
        queue.append((edge.id, edge.target))
```

**为什么用广度优先？**
- 保证按层级顺序处理节点
- 便于构建 follow_ups 关系
- 符合用户的思维模式（先看近的选项）

#### 2. Guideline ID 格式

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

**示例**:
- 根节点: `journey_node:node_initial`
- 带边的节点: `journey_node:node_get_weather:edge_001`

**为什么包含 edge_id？**
- 同一个节点可能有多条入边
- 每条边代表不同的转换条件
- 需要区分不同的路径


#### 3. 元数据结构

```python
{
    "journey_node": {
        # 基本信息
        "journey_id": "journey_weather_001",
        "index": "1",
        "kind": "TOOL",
        
        # 后续节点
        "follow_ups": [
            "journey_node:node_show_result:edge_004",
            "journey_node:node_show_error:edge_005"
        ],
        
        # 工具信息（如果是 TOOL 节点）
        "tools": ["get_weather"],
        
        # 原始节点元数据
        "original_node_metadata": {...},
        
        # 原始边元数据
        "original_edge_metadata": {...}
    }
}
```

**字段说明**:
- `journey_id`: 所属 Journey 的 ID
- `index`: 节点在遍历中的序号
- `kind`: 节点类型（FORK/CHAT/TOOL/NA）
- `follow_ups`: 后续节点的 Guideline ID 列表
- `tools`: 关联的工具列表（仅 TOOL 节点）


#### 4. 完整投影示例

**原始 Journey**（天气查询的简化版本）:

```
节点:
- node_initial (FORK): 初始状态
- node_ask_city (CHAT): 询问城市
- node_get_weather (TOOL): 查询天气
- node_show_result (CHAT): 展示结果

边:
- edge_001: node_initial → node_ask_city (无条件)
- edge_002: node_ask_city → node_get_weather (无条件)
- edge_003: node_get_weather → node_show_result (条件: "查询成功")
```

**投影后的 Guideline**:

```python
[
    # Guideline 1: 根节点
    Guideline(
        id="journey_node:node_initial",
        content=GuidelineContent(
            condition="",
            action="<<JOURNEY ROOT: start the journey...>>"
        ),
        metadata={
            "journey_node": {
                "journey_id": "journey_weather_001",
                "index": "0",
                "kind": "FORK",
                "follow_ups": ["journey_node:node_ask_city:edge_001"]
            }
        }
    ),
    
    # Guideline 2: 询问城市
    Guideline(
        id="journey_node:node_ask_city:edge_001",
        content=GuidelineContent(
            condition=None,  # 无条件转换
            action="友好地询问用户想查询哪个城市的天气"
        ),
        metadata={
            "journey_node": {
                "journey_id": "journey_weather_001",
                "index": "1",
                "kind": "CHAT",
                "follow_ups": ["journey_node:node_get_weather:edge_002"]
            }
        }
    ),
    
    # Guideline 3: 查询天气
    Guideline(
        id="journey_node:node_get_weather:edge_002",
        content=GuidelineContent(
            condition=None,
            action=None
        ),
        metadata={
            "journey_node": {
                "journey_id": "journey_weather_001",
                "index": "2",
                "kind": "TOOL",
                "tools": ["get_weather"],
                "follow_ups": ["journey_node:node_show_result:edge_003"]
            }
        }
    ),
    
    # Guideline 4: 展示结果
    Guideline(
        id="journey_node:node_show_result:edge_003",
        content=GuidelineContent(
            condition="查询成功",
            action="简洁友好地告诉用户天气情况：温度、天气状况、湿度"
        ),
        metadata={
            "journey_node": {
                "journey_id": "journey_weather_001",
                "index": "3",
                "kind": "CHAT",
                "follow_ups": []
            }
        }
    )
]
```


---

## 最佳实践

### 1. 设计 Journey 结构

#### ✅ 好的设计

```python
# 清晰的线性流程
初始状态 → 收集信息 → 执行操作 → 展示结果 → 结束

# 合理的分支
初始状态
    ├─[条件A]→ 流程A
    └─[条件B]→ 流程B
```

#### ❌ 避免的设计

```python
# 过于复杂的分支（难以维护）
初始状态
    ├─[条件1]→ 节点1
    │           ├─[条件1.1]→ 节点1.1
    │           ├─[条件1.2]→ 节点1.2
    │           └─[条件1.3]→ 节点1.3
    ├─[条件2]→ 节点2
    │           ├─[条件2.1]→ 节点2.1
    │           └─[条件2.2]→ 节点2.2
    └─[条件3]→ 节点3
                ├─[条件3.1]→ 节点3.1
                └─[条件3.2]→ 节点3.2

# 循环引用（可能导致无限循环）
节点A → 节点B → 节点C → 节点A
```


### 2. 编写清晰的条件

#### ✅ 好的条件

```python
# 具体明确
condition="用户消息中包含城市名称"
condition="查询成功"
condition="用户想继续查询"

# 可以被 LLM 理解
condition="用户询问价格"
condition="用户表示满意"
```

#### ❌ 避免的条件

```python
# 过于模糊
condition="用户说了什么"
condition="情况A"

# 过于复杂
condition="用户消息中包含城市名称且不是北京且天气晴朗且温度高于20度"

# 技术性太强
condition="regex_match(message, r'^[0-9]+$')"
```

### 3. 编写有效的 Action

#### ✅ 好的 Action

```python
# 清晰的指令
action="友好地询问用户想查询哪个城市的天气"
action="简洁友好地告诉用户天气情况：温度、天气状况、湿度"

# 包含必要的上下文
action="告知暂不支持该城市，列出可查询的城市列表"
```

#### ❌ 避免的 Action

```python
# 过于简单
action="回复"
action="说话"

# 过于详细（限制了 LLM 的创造性）
action="说：'您好，请问您想查询哪个城市的天气？我们支持北京、上海...'"

# 包含代码逻辑
action="if temperature > 30: say('很热') else: say('不热')"
```


### 4. 合理使用节点类型

#### FORK 节点
- **用途**: 纯粹的路由，没有实际动作
- **示例**: 初始状态、决策点
- **特点**: 通常有多个出边

```python
# 初始状态（FORK）
初始状态
    ├─[用户已提供信息]→ 直接处理
    └─[用户未提供信息]→ 收集信息
```

#### CHAT 节点
- **用途**: Agent 需要生成回复
- **示例**: 询问、确认、解释
- **特点**: 有 action，没有 tools

```python
# 询问节点（CHAT）
action="询问用户想查询哪个城市的天气"
```

#### TOOL 节点
- **用途**: 调用工具函数
- **示例**: 查询数据库、调用 API
- **特点**: 有 tools，通常没有 action

```python
# 工具节点（TOOL）
tools=["get_weather"]
action=None
```


### 5. 处理错误和边界情况

#### 示例：天气查询的错误处理

```python
# 查询天气后的分支
await tool_node.transition_to(
    chat_state="简洁友好地告诉用户天气情况",
    condition="查询成功"
)

await tool_node.transition_to(
    chat_state="告知暂不支持该城市，列出可查询的城市列表",
    condition="查询失败"
)
```

#### 关键点
- 为每个可能的结果创建转换
- 提供清晰的错误提示
- 允许用户重试或选择其他路径

### 6. 使用 Journey 内的 Guideline

```python
# 来自 weather_agent.py
await journey.create_guideline(
    condition="用户输入的城市名称不清晰或有歧义",
    action="礼貌地请用户确认具体是哪个城市"
)

await journey.create_guideline(
    condition="用户一次提到多个城市",
    action="逐个查询并对比展示各城市天气"
)
```

**用途**:
- 处理 Journey 特定的边界情况
- 增强用户体验
- 不影响 Journey 的主流程


### 7. 全局 vs 局部 Guideline

#### 全局 Guideline
```python
# 在 Agent 级别创建
await agent.create_guideline(
    condition="用户问候",
    action="友好回应，简单介绍自己"
)

await agent.create_guideline(
    condition="对话中的任何时候",
    action="保持简洁友好，像朋友聊天一样自然"
)
```

**特点**:
- 在所有对话中生效
- 用于通用行为规范
- 优先级通常低于 Journey 内的 Guideline

#### Journey 内的 Guideline
```python
# 在 Journey 级别创建
await journey.create_guideline(
    condition="用户输入的城市名称不清晰",
    action="礼貌地请用户确认具体是哪个城市"
)
```

**特点**:
- 只在 Journey 激活时生效
- 用于 Journey 特定的场景
- 优先级通常高于全局 Guideline


---

## 常见问题

### Q1: Journey 和 Guideline 有什么区别？

**Guideline**:
- 简单的条件-动作规则
- 适合单步骤的行为
- 独立存在

**Journey**:
- 多步骤的流程
- 适合复杂的交互
- 由多个节点和边组成

**示例对比**:

```python
# Guideline: 简单的问候
await agent.create_guideline(
    condition="用户问候",
    action="友好回应"
)

# Journey: 完整的查询流程
journey = await agent.create_journey(...)
await journey.initial_state.transition_to(...)
await ...
```

### Q2: 什么时候用 Journey，什么时候用 Guideline？

**使用 Guideline**:
- 单步骤的响应
- 通用的行为规范
- 简单的条件判断

**使用 Journey**:
- 多步骤的流程
- 需要收集信息
- 有明确的开始和结束
- 需要处理多种分支


### Q3: Journey 如何被激活？

Journey 通过 `conditions` 字段定义的 Guideline 来激活：

```python
journey = await agent.create_journey(
    title="查询天气",
    conditions=["用户想查询天气", "用户提到城市名称"]
)
```

**激活流程**:
1. 用户发送消息
2. 引擎使用向量搜索找到相关 Journey
3. 检查 Journey 的 conditions 是否匹配
4. 如果匹配，Journey 被激活
5. 投影 Journey 为 Guideline 并执行

### Q4: 如何跟踪用户在 Journey 中的位置？

通过 `journey_path` 跟踪：

```python
# 初始状态
context.state.journey_paths[journey_id] = ["node_initial"]

# 用户选择了某个转换
context.state.journey_paths[journey_id] = [
    "node_initial",
    "node_ask_city"
]

# 继续前进
context.state.journey_paths[journey_id] = [
    "node_initial",
    "node_ask_city",
    "node_get_weather"
]
```

**用途**:
- 节点剪枝（只显示相关的下一步）
- 防止回退到已访问的节点
- 支持跨会话恢复


### Q5: 投影是什么时候发生的？

投影在 **每次 Journey 被激活时** 发生：

```python
# 用户发送消息
"北京天气怎么样？"
    ↓
# 查找激活的 Journey
active_journeys = find_active_journeys(...)
    ↓
# 为每个激活的 Journey 进行投影
for journey in active_journeys:
    guidelines = await projection.project_journey_to_guidelines(journey.id)
    ↓
# 匹配和执行
```

**注意**: 投影是实时的，不会缓存。如果 Journey 结构改变，下次激活时会使用新的结构。

### Q6: 如何处理 Journey 中的循环？

**有限循环**（推荐）:
```python
# 询问 → 查询 → 展示 → 询问是否继续
await result_node.transition_to(
    chat_state="询问用户是否还想查询其他城市"
)

await ask_continue_node.transition_to(
    tool_state=get_weather,
    condition="用户想继续"
)

await ask_continue_node.transition_to(
    state=p.END_JOURNEY,
    condition="用户不想继续"
)
```

**避免无限循环**:
```python
# ❌ 不要这样做
节点A → 节点B → 节点A → 节点B → ...
```


### Q7: 如何调试 Journey？

#### 1. 查看投影结果

```python
# 手动投影 Journey
projection = JourneyGuidelineProjection(journey_store, guideline_store)
guidelines = await projection.project_journey_to_guidelines(journey_id)

# 打印 Guideline
for g in guidelines:
    print(f"ID: {g.id}")
    print(f"Condition: {g.content.condition}")
    print(f"Action: {g.content.action}")
    print(f"Metadata: {g.metadata}")
    print("---")
```

#### 2. 检查 Journey 路径

```python
# 打印当前路径
print(f"Current path: {context.state.journey_paths.get(journey_id, [])}")
```

#### 3. 使用日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 在关键位置添加日志
logger.debug(f"Journey activated: {journey.id}")
logger.debug(f"Selected node: {selected_node.id}")
```

#### 4. 生成 Mermaid 图表

```python
# 通过 API 获取 Journey 的可视化
GET /journeys/{journey_id}?include_mermaid_chart=true
```


### Q8: 如何优化 Journey 性能？

#### 1. 减少节点数量
```python
# ❌ 过多的节点
初始 → 验证1 → 验证2 → 验证3 → 处理 → 验证4 → 结束

# ✅ 合并相关节点
初始 → 验证 → 处理 → 结束
```

#### 2. 使用清晰的条件
```python
# ✅ 清晰的条件让 LLM 更容易判断
condition="用户消息中包含城市名称"

# ❌ 模糊的条件需要更多推理
condition="用户可能想查询天气"
```

#### 3. 利用自动返回
```python
# 如果工具节点后只有一个后续节点，会自动跳转
工具节点 → [唯一后续] → 下一个节点
# 不需要 LLM 推理，直接跳转
```

#### 4. 合理使用节点剪枝
- 系统会自动剪枝不相关的节点
- 保持 Journey 结构清晰有助于剪枝效果


---

## 完整示例：天气查询 Journey

### 代码结构

```python
# 1. 定义工具
@p.tool
async def get_weather(context: p.ToolContext, location: str) -> p.ToolResult:
    # 查询天气逻辑
    ...

# 2. 创建 Journey
async def create_weather_journey(agent: p.Agent) -> p.Journey:
    journey = await agent.create_journey(
        title="查询天气",
        description="帮助用户查询城市天气",
        conditions=["用户想查询天气", "用户提到城市名称"]
    )
    
    # 3. 定义流程
    # 路径1: 用户已提到城市
    t1 = await journey.initial_state.transition_to(
        tool_state=get_weather,
        condition="用户消息中包含城市名称"
    )
    
    # 路径2: 用户未提到城市
    t2 = await journey.initial_state.transition_to(
        chat_state="友好地询问用户想查询哪个城市的天气",
        condition="用户没有提到具体城市"
    )
    
    t3 = await t2.target.transition_to(tool_state=get_weather)
    
    # 4. 处理结果
    # 成功
    t4 = await t1.target.transition_to(
        chat_state="简洁友好地告诉用户天气情况",
        condition="查询成功"
    )
    
    t5 = await t3.target.transition_to(
        chat_state="简洁友好地告诉用户天气情况",
        condition="查询成功"
    )
    
    # 失败
    t6 = await t1.target.transition_to(
        chat_state="告知暂不支持该城市，列出可查询的城市列表",
        condition="查询失败"
    )
    
    t7 = await t3.target.transition_to(
        chat_state="告知暂不支持该城市，列出可查询的城市列表",
        condition="查询失败"
    )
    
    # 5. 询问是否继续
    t8 = await t4.target.transition_to(
        chat_state="询问用户是否还想查询其他城市"
    )
    
    t9 = await t5.target.transition_to(
        chat_state="询问用户是否还想查询其他城市"
    )
    
    # 6. 继续或结束
    await t8.target.transition_to(
        tool_state=get_weather,
        condition="用户想查询其他城市"
    )
    
    await t8.target.transition_to(
        state=p.END_JOURNEY,
        condition="用户不想继续查询"
    )
    
    # 7. Journey 内的 Guideline
    await journey.create_guideline(
        condition="用户输入的城市名称不清晰或有歧义",
        action="礼貌地请用户确认具体是哪个城市"
    )
    
    return journey

# 8. 主函数
async def main():
    async with p.Server(nlp_service=p.NLPServices.ollama) as server:
        agent = await server.create_agent(
            name="小天",
            description="友好的天气助手"
        )
        
        await create_weather_journey(agent)
        
        # 全局 Guideline
        await agent.create_guideline(
            condition="用户问候",
            action="友好回应，简单介绍自己可以查询天气"
        )
```


### 对话流程示例

#### 场景 1: 用户直接提到城市

```
用户: "北京天气怎么样？"
    ↓
系统: 激活 Journey "查询天气"
    ↓
系统: 投影 Journey 为 Guideline
    ↓
系统: 匹配条件 "用户消息中包含城市名称" ✓
    ↓
系统: 选择节点 "查询天气" (TOOL)
    ↓
系统: 调用 get_weather(location="北京")
    ↓
系统: 返回 {"success": True, "temperature": 15, "condition": "晴朗", ...}
    ↓
系统: 匹配条件 "查询成功" ✓
    ↓
系统: 选择节点 "展示结果" (CHAT)
    ↓
Agent: "北京今天天气晴朗，温度15°C，湿度45%。"
    ↓
系统: 选择节点 "询问继续" (CHAT)
    ↓
Agent: "还想查询其他城市的天气吗？"
```


#### 场景 2: 用户未提到城市

```
用户: "我想查天气"
    ↓
系统: 激活 Journey "查询天气"
    ↓
系统: 匹配条件 "用户没有提到具体城市" ✓
    ↓
系统: 选择节点 "询问城市" (CHAT)
    ↓
Agent: "您想查询哪个城市的天气呢？我可以查询北京、上海、广州等城市。"
    ↓
用户: "上海"
    ↓
系统: 选择节点 "查询天气" (TOOL)
    ↓
系统: 调用 get_weather(location="上海")
    ↓
Agent: "上海今天多云，温度20°C，湿度60%。"
    ↓
Agent: "还想查询其他城市的天气吗？"
```

#### 场景 3: 查询失败

```
用户: "火星天气怎么样？"
    ↓
系统: 调用 get_weather(location="火星")
    ↓
系统: 返回 {"success": False, "message": "暂时没有火星的天气数据", ...}
    ↓
系统: 匹配条件 "查询失败" ✓
    ↓
Agent: "抱歉，暂时没有火星的天气数据。我可以查询北京、上海、广州、成都、深圳、杭州等城市。"
    ↓
用户: "那查一下深圳吧"
    ↓
系统: 调用 get_weather(location="深圳")
    ↓
Agent: "深圳今天晴朗，温度26°C，湿度65%。"
```


---

## 架构总结

### 数据流

```
用户消息
    ↓
引擎 (Engine)
    ↓
查找激活的 Journey (向量搜索 + 条件匹配)
    ↓
投影 Journey 为 Guideline (JourneyGuidelineProjection)
    ↓
匹配 Guideline (GuidelineMatcher)
    ↓
选择节点 (JourneyNodeSelectionBatch + LLM)
    ↓
执行节点 (调用工具或生成回复)
    ↓
更新路径 (journey_paths)
    ↓
返回响应
```

### 关键组件

1. **JourneyStore**: 存储 Journey、节点、边
2. **GuidelineStore**: 存储 Guideline
3. **JourneyGuidelineProjection**: 投影 Journey 为 Guideline
4. **GuidelineMatcher**: 匹配 Guideline
5. **JourneyNodeSelectionBatch**: 选择下一个节点
6. **Engine**: 协调整个流程


### 存储架构

```
Journey 存储
├─ DocumentDatabase
│  ├─ journeys collection (Journey 文档)
│  ├─ journey_nodes collection (节点)
│  ├─ journey_edges collection (边)
│  ├─ journey_tags collection (标签关联)
│  └─ journey_conditions collection (条件关联)
└─ VectorDatabase
   └─ journeys collection (向量化的 Journey 内容)

Guideline 存储
└─ DocumentDatabase
   ├─ guidelines collection (Guideline 文档)
   └─ guideline_tags collection (标签关联)
```

**双存储架构的优势**:
- DocumentDatabase: 快速的结构化查询
- VectorDatabase: 语义搜索，找到相关 Journey
- 两者结合，既快又准

---

## 进阶主题

### 1. 多 Journey 并行

系统支持同时激活多个 Journey：

```python
# 用户消息可能激活多个 Journey
active_journeys = [
    journey_weather,    # 查询天气
    journey_translate,  # 翻译
]

# 每个 Journey 独立投影和匹配
for journey in active_journeys:
    guidelines = await projection.project_journey_to_guidelines(journey.id)
    # ...
```

**冲突解决**:
- LLM 会根据上下文选择最相关的 Journey
- 可以通过优先级或标签控制


### 2. Journey 嵌套

虽然系统不直接支持 Journey 嵌套，但可以通过标签和条件实现类似效果：

```python
# 主 Journey
main_journey = await agent.create_journey(
    title="客户服务",
    conditions=["用户需要帮助"]
)

# 子 Journey（通过条件关联）
weather_journey = await agent.create_journey(
    title="查询天气",
    conditions=["用户想查询天气"],
    tags=["sub_journey", "customer_service"]
)

payment_journey = await agent.create_journey(
    title="处理支付",
    conditions=["用户想支付"],
    tags=["sub_journey", "customer_service"]
)
```

### 3. 动态 Journey

可以根据运行时信息动态修改 Journey：

```python
# 添加新节点
new_node = await journey_store.create_node(
    journey_id=journey.id,
    action="新的动作",
    tools=[],
    metadata={"kind": "CHAT"}
)

# 添加新边
new_edge = await journey_store.create_edge(
    journey_id=journey.id,
    source=existing_node.id,
    target=new_node.id,
    condition="新的条件"
)
```

**注意**: 修改后，下次激活时会使用新的结构。


### 4. 跨会话 Journey

通过持久化 `journey_paths`，可以支持跨会话恢复：

```python
# 会话结束时保存
await session_store.update_session(
    session_id=session.id,
    journey_paths=context.state.journey_paths
)

# 会话恢复时加载
session = await session_store.read_session(session_id)
context.state.journey_paths = session.journey_paths
```

**用例**:
- 用户中断对话后继续
- 多轮复杂流程
- 长期任务跟踪

---

## 参考资料

### 相关文档
- [01-overview.md](./01-overview.md) - 架构概览
- [02-core-models.md](./02-core-models.md) - 数据模型
- [06-journey-guideline-projection.md](./06-journey-guideline-projection.md) - 投影机制
- [08-complete-flow.md](./08-complete-flow.md) - 完整流程
- [09-collaboration-mechanism.md](./09-collaboration-mechanism.md) - 协作机制

### 示例代码
- [weather_agent.py](./weather_agent.py) - 天气查询代理
- [examples/healthcare.py](../examples/healthcare.py) - 医疗咨询代理
- [examples/travel_voice_agent.py](../examples/travel_voice_agent.py) - 旅行语音代理


### 核心源代码文件
- `src/parlant/core/journeys.py` - Journey 核心模型和存储
- `src/parlant/core/guidelines.py` - Guideline 核心模型和存储
- `src/parlant/core/journey_guideline_projection.py` - 投影机制
- `src/parlant/core/app_modules/journeys.py` - Journey 应用层
- `src/parlant/core/engines/alpha/guideline_matching/guideline_matcher.py` - Guideline 匹配
- `src/parlant/core/engines/alpha/guideline_matching/generic/journey_node_selection_batch.py` - 节点选择

---

## 总结

本指南通过 `weather_agent.py` 这个具体示例，详细展示了：

1. **核心概念**: Guideline 和 Journey 的定义和区别
2. **数据模型**: Journey、JourneyNode、JourneyEdge、Guideline 的结构
3. **创建流程**: 从用户代码到数据库存储的完整过程
4. **执行流程**: 从用户消息到 Agent 响应的完整过程
5. **投影机制**: 如何将图结构转换为 Guideline 列表
6. **最佳实践**: 如何设计和实现高质量的 Journey
7. **常见问题**: 开发中可能遇到的问题和解决方案

通过理解这些内容，你可以：
- 快速上手 Journey 和 Guideline 的开发
- 设计复杂的多步骤对话流程
- 理解系统的内部工作原理
- 调试和优化你的 Agent

**下一步**:
- 运行 `weather_agent.py` 体验完整流程
- 阅读其他示例代码学习更多模式
- 查看源代码深入理解实现细节
- 开始构建你自己的 Journey！

---

**文档版本**: 1.0  
**最后更新**: 2025-11-05  
**基于代码**: weather_agent.py + journey-guideline-analysis/*
