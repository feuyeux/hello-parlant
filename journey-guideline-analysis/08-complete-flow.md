# 完整请求流程分析

## 创建 Journey 的完整流程

### 1. API 请求
```http
POST /journeys
Content-Type: application/json

{
  "title": "客户服务流程",
  "description": "处理客户咨询的标准流程",
  "conditions": [
    "客户需要帮助",
    "客户有问题"
  ],
  "tags": ["customer_service"]
}
```

### 2. API 层处理
```python
# src/parlant/api/journeys.py
async def create_journey(
    request: Request,
    params: JourneyCreationParamsDTO,
) -> JourneyDTO:
    # 2.1 授权检查
    await authorization_policy.authorize(
        request=request, 
        operation=Operation.CREATE_JOURNEY
    )
    
    # 2.2 调用应用层
    journey, guidelines = await app.journeys.create(
        params.title, 
        params.description, 
        params.conditions, 
        params.tags
    )
    
    # 2.3 返回 DTO
    return JourneyDTO(...)
```

### 3. 应用层处理
```python
# src/parlant/core/app_modules/journeys.py
async def create(
    self,
    title: str,
    description: str,
    conditions: Sequence[str],
    tags: Sequence[TagId] | None,
) -> tuple[Journey, Sequence[Guideline]]:
    # 3.1 为每个条件创建 Guideline
    guidelines = [
        await self._guideline_store.create_guideline(
            condition=condition,
            action=None,
            tags=[],
        )
        for condition in conditions
    ]
    
    # 3.2 创建 Journey
    journey = await self._journey_store.create_journey(
        title=title,
        description=description,
        conditions=[g.id for g in guidelines],
        tags=tags,
    )
    
    # 3.3 为 Guideline 添加 Journey 标签
    for guideline in guidelines:
        await self._guideline_store.upsert_tag(
            guideline_id=guideline.id,
            tag_id=Tag.for_journey_id(journey.id),
        )
    
    return journey, guidelines
```

### 4. 存储层处理
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
        # 4.1 生成 ID
        journey_checksum = md5_checksum(f"{title}{description}{conditions}")
        journey_id = JourneyId(self._id_generator.generate(journey_checksum))
        journey_root_id = JourneyNodeId(self._id_generator.generate(f"{journey_id}root"))
        
        # 4.2 创建根节点
        root = JourneyNode(
            id=journey_root_id,
            creation_utc=creation_utc,
            action=None,
            tools=[],
            metadata={},
        )
        await self._node_association_collection.insert_one(
            document=self._serialize_node(root, journey_id)
        )
        
        # 4.3 创建 Journey
        journey = Journey(...)
        
        # 4.4 组装内容并向量化
        content = self.assemble_content(title, description, [], [])
        
        # 4.5 插入文档数据库
        await self._collection.insert_one(document=self._serialize(journey))
        
        # 4.6 插入向量数据库
        await self._vector_collection.insert_one(document={...})
        
        # 4.7 创建标签关联
        for tag_id in tags or []:
            await self._tag_association_collection.insert_one(...)
        
        # 4.8 创建条件关联
        for condition in conditions:
            await self._condition_association_collection.insert_one(...)
    
    return journey
```

### 5. 数据库操作
```
DocumentDatabase:
  - journeys collection: 插入 Journey 文档
  - journey_nodes collection: 插入根节点
  - journey_tags collection: 插入标签关联
  - journey_conditions collection: 插入条件关联

VectorDatabase:
  - journeys collection: 插入向量化的 Journey 内容
```

## 执行 Journey 的完整流程

### 1. 用户发送消息
```
用户: "我需要帮助"
```

### 2. 引擎接收并处理

#### 2.1 加载上下文
```python
# 加载 Agent、Session、Customer 等信息
context = await load_engine_context(...)
```

#### 2.2 查找激活的 Journey
```python
# 根据条件匹配 Journey
active_journeys = await find_active_journeys(
    query="我需要帮助",
    available_journeys=all_journeys,
)
```

**匹配逻辑**:
1. 使用向量搜索找到相关 Journey
2. 检查 Journey 的 conditions (Guideline)
3. 返回匹配的 Journey 列表

#### 2.3 投影 Journey 为 Guideline
```python
# 对每个激活的 Journey
for journey in active_journeys:
    # 读取 Journey 的节点和边
    nodes = await journey_store.list_nodes(journey.id)
    edges = await journey_store.list_edges(journey.id)
    
    # 投影为 Guideline
    journey_guidelines = await projection.project_journey_to_guidelines(journey.id)
    
    # 添加到待匹配的 Guideline 列表
    all_guidelines.extend(journey_guidelines)
```

#### 2.4 匹配 Guideline
```python
# 使用 GuidelineMatcher
matching_result = await guideline_matcher.match_guidelines(
    context=context,
    active_journeys=active_journeys,
    guidelines=all_guidelines,
)
```

**匹配流程**:
1. 根据 Guideline 类型分组
2. 为 Journey Guideline 创建 `JourneyNodeSelectionBatch`
3. 构建节点包装器
4. 剪枝节点（只保留相关节点）
5. 生成转换图文本
6. LLM 推理选择下一步
7. 返回匹配的 Guideline

#### 2.5 执行 Guideline
```python
for match in matching_result.matches:
    guideline = match.guideline
    
    # 执行 action
    if guideline.content.action:
        response = await execute_action(guideline.content.action)
    
    # 更新 Journey 路径
    if "journey_path" in match.metadata:
        journey_id = match.metadata["step_selection_journey_id"]
        journey_path = match.metadata["journey_path"]
        context.state.journey_paths[journey_id] = journey_path
```

#### 2.6 生成响应
```python
# 基于执行结果生成响应
response = await message_generator.generate(
    context=context,
    guideline_matches=matching_result.matches,
)
```

### 3. 返回响应给用户
```
Agent: "我很乐意帮助您。请告诉我您遇到了什么问题？"
```

### 4. 状态更新
```python
# 更新 Session
await session_store.update_session(
    session_id=session.id,
    events=[...],
)

# 更新 Journey 路径
context.state.journey_paths[journey_id] = updated_path
```

## 查询 Journey 的完整流程

### 1. API 请求
```http
GET /journeys/{journey_id}
```

### 2. API 层处理
```python
async def read_journey(
    request: Request,
    journey_id: JourneyIdPath,
) -> JourneyDTO:
    # 2.1 授权检查
    await authorization_policy.authorize(...)
    
    # 2.2 调用应用层
    model = await app.journeys.read(journey_id=journey_id)
    
    # 2.3 返回 DTO
    return JourneyDTO(
        id=model.journey.id,
        title=model.journey.title,
        description=model.journey.description,
        conditions=model.journey.conditions,
        tags=model.journey.tags,
    )
```

### 3. 应用层处理
```python
async def read(self, journey_id: JourneyId) -> JourneyGraph:
    # 3.1 读取 Journey
    journey = await self._journey_store.read_journey(journey_id=journey_id)
    
    # 3.2 读取节点
    nodes = await self._journey_store.list_nodes(journey_id=journey.id)
    
    # 3.3 读取边
    edges = await self._journey_store.list_edges(journey_id=journey.id)
    
    # 3.4 返回图结构
    return JourneyGraph(journey=journey, nodes=nodes, edges=edges)
```

### 4. 存储层处理
```python
async def read_journey(self, journey_id: JourneyId) -> Journey:
    async with self._lock.reader_lock:
        # 4.1 查询 Journey 文档
        doc = await self._collection.find_one({"id": {"$eq": journey_id}})
        
        if not doc:
            raise ItemNotFoundError(item_id=UniqueId(journey_id))
        
        # 4.2 反序列化
        return await self._deserialize(doc)

async def _deserialize(self, doc: JourneyDocument) -> Journey:
    # 4.3 查询标签关联
    tags = [
        d["tag_id"]
        for d in await self._tag_association_collection.find(
            {"journey_id": {"$eq": doc["id"]}}
        )
    ]
    
    # 4.4 查询条件关联
    conditions = [
        d["condition"]
        for d in await self._condition_association_collection.find(
            {"journey_id": {"$eq": doc["id"]}}
        )
    ]
    
    # 4.5 构建 Journey 对象
    return Journey(...)
```

### 5. 数据库查询
```
DocumentDatabase:
  - journeys collection: 查询 Journey 文档
  - journey_nodes collection: 查询节点
  - journey_edges collection: 查询边
  - journey_tags collection: 查询标签关联
  - journey_conditions collection: 查询条件关联
```

## 性能优化点

1. **并行处理**: 多个匹配批次并行执行
2. **节点剪枝**: 只处理相关节点，减少 LLM 输入
3. **自动返回**: 工具节点后自动选择唯一后续节点
4. **向量搜索**: 快速找到相关 Journey
5. **缓存**: 使用 `@cached_property` 缓存计算结果
6. **读写锁**: 优化并发访问
