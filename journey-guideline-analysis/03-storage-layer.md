# 存储层实现分析

## GuidelineDocumentStore

### 核心职责
- Guideline 的 CRUD 操作
- 标签关联管理
- 元数据管理

### 关键方法

#### 创建 Guideline
```python
async def create_guideline(
    self,
    condition: str,
    action: Optional[str] = None,
    metadata: Mapping[str, JSONSerializable] = {},
    creation_utc: Optional[datetime] = None,
    enabled: bool = True,
    tags: Optional[Sequence[TagId]] = None,
) -> Guideline
```

**流程**:
1. 生成 ID (基于 condition + action + enabled + metadata 的 MD5)
2. 创建 Guideline 对象
3. 序列化并插入数据库
4. 为每个标签创建关联记录

#### 查询 Guideline
```python
async def list_guidelines(
    self,
    tags: Optional[Sequence[TagId]] = None,
) -> Sequence[Guideline]
```

**支持的查询模式**:
- 无标签: 返回所有 Guideline
- 空标签列表 `[]`: 返回没有任何标签的 Guideline
- 指定标签: 返回包含任意指定标签的 Guideline

#### 标签管理
```python
async def upsert_tag(
    self,
    guideline_id: GuidelineId,
    tag_id: TagId,
    creation_utc: Optional[datetime] = None,
) -> bool

async def remove_tag(
    self,
    guideline_id: GuidelineId,
    tag_id: TagId,
) -> None
```

## JourneyVectorStore

### 核心职责
- Journey、Node、Edge 的 CRUD 操作
- 向量化存储用于相似度搜索
- 条件和标签关联管理

### 双存储架构
```
JourneyVectorStore
├── DocumentDatabase (结构化数据)
│   ├── journeys collection
│   ├── journey_nodes collection
│   ├── journey_edges collection
│   ├── journey_tags collection
│   └── journey_conditions collection
└── VectorDatabase (向量化数据)
    └── journeys collection (用于相似度搜索)
```

### 关键方法

#### 创建 Journey
```python
async def create_journey(
    self,
    title: str,
    description: str,
    conditions: Sequence[GuidelineId],
    creation_utc: Optional[datetime] = None,
    tags: Optional[Sequence[TagId]] = None,
) -> Journey
```

**流程**:
1. 生成 Journey ID
2. 创建根节点 (root_id)
3. 组装内容用于向量化
4. 插入文档数据库
5. 插入向量数据库
6. 创建标签关联
7. 创建条件关联

#### 节点管理
```python
async def create_node(
    self,
    journey_id: JourneyId,
    action: Optional[str],
    tools: Sequence[ToolId],
) -> JourneyNode

async def list_nodes(
    self,
    journey_id: JourneyId,
) -> Sequence[JourneyNode]
```

**特殊节点**:
- `END_NODE_ID = "end"`: 虚拟结束节点
- 根节点: 每个 Journey 自动创建

#### 边管理
```python
async def create_edge(
    self,
    journey_id: JourneyId,
    source: JourneyNodeId,
    target: JourneyNodeId,
    condition: Optional[str] = None,
) -> JourneyEdge
```

#### 相似度搜索
```python
async def find_relevant_journeys(
    self,
    query: str,
    available_journeys: Sequence[Journey],
    max_journeys: int = 5,
) -> Sequence[Journey]
```

**流程**:
1. 将查询文本分块
2. 对每个块进行向量搜索
3. 合并结果并去重
4. 按距离排序返回 top-k

### 内容组装策略
```python
@staticmethod
def assemble_content(
    title: str,
    description: str,
    nodes: Sequence[JourneyNode],
    edges: Sequence[JourneyEdge],
) -> str:
    return f"{title}\n{description}\nNodes: {', '.join(n.action for n in nodes if n.action)}\nEdges: {', '.join(e.condition for e in edges if e.condition)}"
```

**用途**: 将 Journey 的结构化信息转换为文本，用于向量化和相似度搜索
