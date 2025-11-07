# Weather Agent 和 SDK 源代码分析

## 概述

本文档记录了对 `weather_agent.py` 和 Parlant SDK 源代码的深入分析，包括关键类、方法签名、调用流程和实现细节。

## 目录

1. [Weather Agent 结构分析](#weather-agent-结构分析)
2. [SDK 核心类分析](#sdk-核心类分析)
3. [启动流程关键方法](#启动流程关键方法)
4. [Journey 创建流程](#journey-创建流程)
5. [关键方法签名汇总](#关键方法签名汇总)

---

## Weather Agent 结构分析

### 文件: `weather_agent.py`

#### 环境配置
```python
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "qwen2.5:latest"
os.environ["OLLAMA_EMBEDDING_MODEL"] = "nomic-embed-text:latest"
os.environ["OLLAMA_API_TIMEOUT"] = "300"
```

#### 工具定义

**get_weather 工具**
- 装饰器: `@p.tool`
- 签名: `async def get_weather(context: p.ToolContext, location: str) -> p.ToolResult`
- 功能: 查询指定地区的天气信息
- 返回: `p.ToolResult` 包含天气数据或错误信息
- 支持城市: 北京、上海、广州、成都、深圳、杭州、New York、Los Angeles、Chicago、London、Tokyo

#### Journey 创建函数

**create_weather_journey**
- 签名: `async def create_weather_journey(agent: p.Agent) -> p.Journey`
- 功能: 创建天气查询流程
- 返回: Journey 对象

**Journey 结构:**

1. **初始状态 (initial_state)**: Journey 的起点
2. **转换 (transitions)**: 
   - t1: 用户消息中包含城市名称 → 直接查询天气 (tool_state=get_weather)
   - t2: 用户没有提到具体城市 → 询问城市 (chat_state)
   - t3: 用户回复城市后 → 查询天气
   - t4, t5: 查询成功 → 展示结果 (chat_state)
   - t6, t7: 查询失败 → 提示可用城市
   - t8, t9: 成功后 → 询问是否继续
   - 继续查询 → 回到查询流程
   - 不继续 → END_JOURNEY

3. **Journey 内 Guidelines**:
   - 城市名称不清晰或有歧义 → 请用户确认
   - 用户一次提到多个城市 → 逐个查询并对比

#### 主函数

**main 函数**
- 签名: `async def main() -> None`
- 流程:
  1. 创建 Server (使用 async context manager)
  2. 创建 Agent
  3. 创建 Journey
  4. 创建全局 Guidelines

---

## SDK 核心类分析

### 1. Server 类

**位置**: `.venv/lib/site-packages/parlant/sdk.py`

**类定义**:
```python
class Server:
    """主服务器类，管理 agent、journeys、tools 和其他组件"""
```

**构造函数签名**:
```python
def __init__(
    self,
    port: int = 8800,
    tool_service_port: int = 8818,
    nlp_service: Callable[[Container], NLPService] = NLPServices.openai,
    session_store: Literal["transient", "local"] | str | SessionStore = "transient",
    customer_store: Literal["transient", "local"] | str | CustomerStore = "transient",
    log_level: LogLevel = LogLevel.INFO,
    modules: list[str] = [],
    migrate: bool = False,
    configure_hooks: Callable[[EngineHooks], Awaitable[EngineHooks]] | None = None,
    configure_container: Callable[[Container], Awaitable[Container]] | None = None,
    initialize_container: Callable[[Container], Awaitable[None]] | None = None,
) -> None
```

**关键属性**:
```python
self.port: int
self.tool_service_port: int
self.log_level: LogLevel
self.modules: list[str]
self._migrate: bool
self._nlp_service_func: Callable[[Container], NLPService]
self._evaluator: _CachedEvaluator
self._session_store: SessionStore
self._customer_store: CustomerStore
self._plugin_server: PluginServer
self._container: Container
self._guideline_evaluations: dict[GuidelineId, ...]
self._node_evaluations: dict[JourneyStateId, ...]
self._journey_evaluations: dict[JourneyId, ...]
self._creation_progress: Progress | None
self._retrievers: dict[AgentId, dict[str, Callable]]
self._exit_stack: AsyncExitStack
```

**关键方法**:

1. **__aenter__** (启动服务器)
```python
async def __aenter__(self) -> Server:
    """
    启动服务器，初始化所有组件
    
    流程:
    1. 调用 start_parlant() 获取 startup context manager
    2. 进入 startup context，获取 Container
    3. 初始化 creation progress bar
    4. 返回 Server 实例
    """
```

2. **__aexit__** (关闭服务器)
```python
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    tb: TracebackType | None,
) -> bool:
    """
    关闭服务器，清理资源
    
    流程:
    1. 关闭 creation progress bar
    2. 处理所有待评估的 evaluations
    3. 设置 retrievers
    4. 退出 startup context
    5. 清理 exit stack
    """
```

3. **create_agent**
```python
async def create_agent(
    self,
    name: str,
    description: str,
    composition_mode: CompositionMode = CompositionMode.FLUID,
    max_engine_iterations: int | None = None,
    tags: Sequence[TagId] = [],
) -> Agent:
    """创建新的 Agent"""
```

4. **create_journey**
```python
async def create_journey(
    self,
    title: str,
    description: str,
    conditions: list[str | Guideline],
) -> Journey:
    """创建新的 Journey"""
```

5. **_process_evaluations** (处理评估)
```python
async def _process_evaluations(self) -> None:
    """
    处理所有待评估的 guidelines、nodes 和 journeys
    
    流程:
    1. 创建所有评估任务 (asyncio.Task)
    2. 并发执行所有评估
    3. 显示进度条 (如果不是 TRACE 日志级别)
    4. 将评估结果写入 metadata
    """
```

6. **_setup_retrievers**
```python
async def _setup_retrievers(self) -> None:
    """设置所有 retrievers，注册 engine hooks"""
```

7. **_add_guideline_evaluation**
```python
def _add_guideline_evaluation(
    self,
    guideline_id: GuidelineId,
    guideline_content: GuidelineContent,
    tool_ids: Sequence[ToolId],
) -> None:
    """添加 guideline 到待评估队列"""
```

8. **_add_state_evaluation**
```python
def _add_state_evaluation(
    self,
    state_id: JourneyStateId,
    guideline_content: GuidelineContent,
    tools: Sequence[ToolId],
) -> None:
    """添加 journey state 到待评估队列"""
```

9. **_add_journey_evaluation**
```python
def _add_journey_evaluation(
    self,
    journey: Journey,
) -> None:
    """添加 journey 到待评估队列"""
```

---

### 2. Agent 类

**位置**: `.venv/lib/site-packages/parlant/sdk.py`

**类定义**:
```python
@dataclass(frozen=True)
class Agent:
    """代理实体，可以与客户交互、管理 journeys 和执行各种任务"""
```

**属性**:
```python
_server: Server
_container: Container
id: AgentId
name: str
description: str | None
max_engine_iterations: int
composition_mode: CompositionMode
tags: Sequence[TagId]
retrievers: Mapping[str, Callable[[RetrieverContext], Awaitable[JSONSerializable]]]
```

**关键方法**:

1. **create_journey**
```python
async def create_journey(
    self,
    title: str,
    description: str,
    conditions: list[str | Guideline],
) -> Journey:
    """
    创建新的 Journey
    
    流程:
    1. 调用 server.create_journey()
    2. 调用 attach_journey() 将 journey 关联到 agent
    3. 返回 Journey 对象
    """
```

2. **attach_journey**
```python
async def attach_journey(self, journey: Journey) -> None:
    """
    将现有 journey 附加到 agent
    
    实现:
    - 在 JourneyStore 中为 journey 添加 agent tag
    """
```

3. **create_guideline**
```python
async def create_guideline(
    self,
    condition: str,
    action: str | None = None,
    tools: Iterable[ToolEntry] = [],
    metadata: dict[str, JSONSerializable] = {},
    canned_responses: Sequence[CannedResponseId] = [],
) -> Guideline:
    """
    创建 guideline
    
    流程:
    1. 启用所有 tools
    2. 在 GuidelineStore 中创建 guideline
    3. 关联 canned responses (如果有)
    4. 添加到评估队列
    5. 创建 tool associations
    6. 返回 Guideline 对象
    """
```

4. **create_observation**
```python
async def create_observation(
    self,
    condition: str,
    canned_responses: Sequence[CannedResponseId] = [],
) -> Guideline:
    """创建观察型 guideline (没有 action)"""
```

5. **attach_tool**
```python
async def attach_tool(
    self,
    tool: ToolEntry,
    condition: str,
) -> GuidelineId:
    """将 tool 附加到 agent，在指定条件下可用"""
```

6. **create_variable**
```python
async def create_variable(
    self,
    name: str,
    description: str | None = None,
    tool: ToolEntry | None = None,
    freshness_rules: str | None = None,
) -> Variable:
    """创建上下文变量"""
```

7. **attach_retriever**
```python
async def attach_retriever(
    self,
    retriever: Callable[[RetrieverContext], Awaitable[JSONSerializable | RetrieverResult]],
    id: str | None = None,
) -> None:
    """附加 retriever 函数到 agent"""
```

---

### 3. Journey 类

**位置**: `.venv/lib/site-packages/parlant/sdk.py`

**类定义**:
```python
@dataclass(frozen=True)
class Journey:
    """由多个状态和转换组成的 Journey"""
```

**属性**:
```python
id: JourneyId
title: str
description: str
conditions: list[Guideline]
states: Sequence[JourneyState]
transitions: Sequence[JourneyTransition[JourneyState]]
tags: Sequence[TagId]
_start_state_id: JourneyStateId
_server: Server
_container: Container
```

**关键方法**:

1. **initial_state** (属性)
```python
@property
def initial_state(self) -> InitialJourneyState:
    """返回 journey 的初始状态"""
```

2. **_create_state**
```python
async def _create_state(
    self,
    state_type: type[TState],
    action: str | None = None,
    tools: Sequence[ToolEntry] = [],
) -> TState:
    """
    创建新的 state
    
    流程:
    1. 确定 metadata type (fork/tool/chat)
    2. 启用所有 tools
    3. 在 JourneyStore 中创建 node
    4. 设置 node metadata
    5. 返回对应类型的 State 对象
    """
```

3. **create_transition**
```python
async def create_transition(
    self,
    condition: str | None,
    source: JourneyState,
    target: TState,
) -> JourneyTransition[TState]:
    """
    创建状态间的转换
    
    流程:
    1. 推进创建进度
    2. 如果 target 不是 END_JOURNEY，添加 state 评估
    3. 在 JourneyStore 中创建 edge
    4. 返回 JourneyTransition 对象
    """
```

4. **create_guideline**
```python
async def create_guideline(
    self,
    condition: str,
    action: str | None = None,
    tools: Iterable[ToolEntry] = [],
    metadata: dict[str, JSONSerializable] = {},
    canned_responses: Sequence[CannedResponseId] = [],
) -> Guideline:
    """
    在 journey 内创建 guideline
    
    流程:
    1. 启用所有 tools
    2. 创建 guideline
    3. 关联 canned responses
    4. 添加到评估队列
    5. 创建与 journey 的 dependency 关系
    6. 创建 tool associations
    7. 返回 Guideline 对象
    """
```

5. **attach_tool**
```python
async def attach_tool(
    self,
    tool: ToolEntry,
    condition: str,
) -> GuidelineId:
    """将 tool 附加到 journey"""
```

6. **create_canned_response**
```python
async def create_canned_response(
    self,
    template: str,
    tags: list[TagId] = [],
    signals: list[str] = [],
) -> CannedResponseId:
    """创建 journey 范围的 canned response"""
```

7. **prioritize_over**
```python
async def prioritize_over(
    self,
    target: Guideline | Journey,
) -> Relationship:
    """创建优先级关系"""
```

8. **depend_on**
```python
async def depend_on(
    self,
    target: Guideline,
) -> Relationship:
    """创建依赖关系"""
```

---

### 4. JourneyState 类及其子类

**位置**: `.venv/lib/site-packages/parlant/sdk.py`

**基类**:
```python
@dataclass(frozen=True)
class JourneyState:
    """Journey 中可以转换到或转换自的状态"""
    
    id: JourneyStateId
    action: str | None
    tools: Sequence[ToolEntry]
    metadata: Mapping[str, JSONSerializable]
    _journey: Journey | None
```

**子类**:

1. **InitialJourneyState**: 初始状态
2. **ChatJourneyState**: 聊天交互状态
3. **ToolJourneyState**: 工具调用状态
4. **ForkJourneyState**: 条件分支状态
5. **EndJourneyState**: 结束状态 (END_JOURNEY)

**关键方法**:

**transition_to** (各子类有不同的重载)
```python
async def transition_to(
    self,
    *,
    condition: str | None = None,
    chat_state: str | None = None,
    tool_instruction: str | None = None,
    state: TState | None = None,
    tool_state: ToolEntry | Sequence[ToolEntry] = [],
    canned_responses: Sequence[CannedResponseId] = [],
) -> JourneyTransition[Any]:
    """
    创建到另一个状态的转换
    
    参数:
    - condition: 转换条件
    - chat_state: 聊天状态的 action
    - tool_instruction: 工具状态的 instruction
    - state: 目标状态 (如果已存在)
    - tool_state: 要调用的工具
    - canned_responses: 关联的 canned responses
    """
```

---

### 5. Guideline 类

**位置**: `.venv/lib/site-packages/parlant/sdk.py`

**类定义**:
```python
@dataclass(frozen=True)
class Guideline:
    """定义条件和要采取的行动的 guideline"""
    
    id: GuidelineId
    condition: str
    action: str | None
    tags: Sequence[TagId]
    metadata: Mapping[str, JSONSerializable]
    _server: Server
    _container: Container
```

**关键方法**:

1. **entail**
```python
async def entail(self, guideline: Guideline) -> Relationship:
    """创建蕴含关系"""
```

2. **prioritize_over**
```python
async def prioritize_over(self, target: Guideline | Journey) -> Relationship:
    """创建优先级关系"""
```

3. **depend_on**
```python
async def depend_on(self, target: Guideline | Journey) -> Relationship:
    """创建依赖关系"""
```

4. **disambiguate**
```python
async def disambiguate(
    self,
    targets: Sequence[Guideline | Journey],
) -> Sequence[Relationship]:
    """创建消歧关系 (至少需要 2 个目标)"""
```

5. **reevaluate_after**
```python
async def reevaluate_after(self, tool: ToolEntry) -> Relationship:
    """创建重新评估关系"""
```

---

### 6. _CachedEvaluator 类

**位置**: `.venv/lib/site-packages/parlant/sdk.py`

**类定义**:
```python
class _CachedEvaluator:
    """缓存评估器，用于评估 guidelines 和 journeys"""
```

**内部类**:
```python
@dataclass(frozen=True)
class JourneyEvaluation:
    node_properties: dict[JourneyStateId, dict[str, JSONSerializable]]
    edge_properties: dict[JourneyTransitionId, dict[str, JSONSerializable]]

@dataclass(frozen=True)
class GuidelineEvaluation:
    properties: dict[str, JSONSerializable]
```

**关键方法**:

1. **__aenter__**
```python
async def __aenter__(self) -> _CachedEvaluator:
    """
    初始化评估器
    
    流程:
    1. 进入数据库 context
    2. 获取或创建 guideline_evaluations 集合
    3. 获取或创建 journey_evaluations 集合
    """
```

2. **evaluate_guideline**
```python
async def evaluate_guideline(
    self,
    entity_id: GuidelineId,
    g: GuidelineContent,
    tool_ids: Sequence[ToolId] = [],
) -> _CachedEvaluator.GuidelineEvaluation:
    """
    评估 guideline
    
    流程:
    1. 计算请求的 hash
    2. 检查缓存
    3. 如果有缓存，直接返回
    4. 如果没有缓存:
       a. 创建评估任务 (BehavioralChangeEvaluator)
       b. 轮询评估状态
       c. 获取评估结果
       d. 缓存结果
       e. 返回结果
    """
```

3. **evaluate_state**
```python
async def evaluate_state(
    self,
    entity_id: JourneyStateId,
    g: GuidelineContent,
    tool_ids: Sequence[ToolId] = [],
) -> _CachedEvaluator.GuidelineEvaluation:
    """评估 journey state (内部调用 _evaluate_guideline)"""
```

4. **evaluate_journey**
```python
async def evaluate_journey(
    self,
    journey: Journey,
) -> _CachedEvaluator.JourneyEvaluation:
    """
    评估 journey
    
    流程:
    1. 计算请求的 hash
    2. 检查缓存
    3. 如果有缓存，直接返回
    4. 如果没有缓存:
       a. 创建评估任务
       b. 轮询评估状态
       c. 获取评估结果 (node_properties 和 edge_properties)
       d. 缓存结果
       e. 返回结果
    """
```

5. **_hash_guideline_evaluation_request**
```python
def _hash_guideline_evaluation_request(
    self,
    g: GuidelineContent,
    tool_ids: Sequence[ToolId],
    journey_state_propositions: bool,
    properties_proposition: bool,
) -> str:
    """生成 guideline 评估请求的 hash"""
```

6. **_hash_journey_evaluation_request**
```python
def _hash_journey_evaluation_request(
    self,
    journey: Journey,
) -> str:
    """生成 journey 评估请求的 hash"""
```

---

## 启动流程关键方法

### 1. start_parlant 函数

**位置**: `.venv/lib/site-packages/parlant/bin/server.py`

**签名**:
```python
def start_parlant(params: StartupParameters) -> AsyncContextManager[Container]:
    """
    启动 Parlant 系统
    
    返回: AsyncContextManager，进入时返回 Container
    """
```

**StartupParameters**:
```python
@dataclass
class StartupParameters:
    port: int
    tool_service_port: int
    nlp_service_func: Callable[[Container], NLPService]
    session_store: SessionStore | Literal["transient", "local"] | str
    customer_store: CustomerStore | Literal["transient", "local"] | str
    log_level: LogLevel
    modules: list[str]
    migrate: bool
    configure_hooks: Callable[[EngineHooks], Awaitable[EngineHooks]] | None
    configure_container: Callable[[Container], Awaitable[Container]] | None
    initialize_container: Callable[[Container], Awaitable[None]] | None
```

### 2. Application 类

**位置**: `.venv/lib/site-packages/parlant/core/application.py`

**关键方法**:

1. **create_customer_session**
```python
async def create_customer_session(
    self,
    customer_id: CustomerId,
    agent_id: AgentId,
    title: Optional[str] = None,
    allow_greeting: bool = False,
) -> Session:
    """创建客户会话"""
```

2. **post_event**
```python
async def post_event(
    self,
    session_id: SessionId,
    kind: EventKind,
    data: Mapping[str, Any],
    source: EventSource = EventSource.CUSTOMER,
    trigger_processing: bool = True,
) -> Event:
    """发布事件到会话"""
```

3. **dispatch_processing_task**
```python
async def dispatch_processing_task(self, session: Session) -> str:
    """分派会话处理任务"""
```

4. **_process_session**
```python
async def _process_session(self, session: Session) -> None:
    """
    处理会话
    
    流程:
    1. 创建 event emitter
    2. 调用 Engine.process()
    """
```

5. **utter**
```python
async def utter(
    self,
    session: Session,
    requests: Sequence[UtteranceRequest],
) -> str:
    """
    生成话语
    
    流程:
    1. 创建 event emitter
    2. 调用 Engine.utter()
    """
```

---

## Journey 创建流程

### weather_agent.py 中的流程

```python
async def main() -> None:
    async with p.Server(nlp_service=p.NLPServices.ollama) as server:
        # 步骤 1: 创建 Agent
        agent = await server.create_agent(
            name="小天",
            description="友好的天气助手，用自然对话方式帮助用户查询天气"
        )
        
        # 步骤 2: 创建 Journey
        await create_weather_journey(agent)
        
        # 步骤 3: 创建全局 Guidelines
        await agent.create_guideline(...)
```

### create_weather_journey 详细流程

```python
async def create_weather_journey(agent: p.Agent) -> p.Journey:
    # 1. 创建 Journey
    journey = await agent.create_journey(
        title="查询天气",
        description="帮助用户查询城市天气",
        conditions=["用户想查询天气", "用户提到城市名称"]
    )
    # 内部调用链:
    # agent.create_journey() 
    #   -> server.create_journey()
    #   -> JourneyStore.create_journey()
    #   -> agent.attach_journey()
    #   -> JourneyStore.upsert_tag()
    
    # 2. 创建转换 (从 initial_state)
    t1 = await journey.initial_state.transition_to(
        tool_state=get_weather,
        condition="用户消息中包含城市名称"
    )
    # 内部调用链:
    # InitialJourneyState.transition_to()
    #   -> JourneyState._transition()
    #   -> journey._create_state(ToolJourneyState, tools=[get_weather])
    #   -> JourneyStore.create_node()
    #   -> JourneyStore.set_node_metadata()
    #   -> journey.create_transition()
    #   -> server._add_state_evaluation()
    #   -> JourneyStore.create_edge()
    
    t2 = await journey.initial_state.transition_to(
        chat_state="友好地询问用户想查询哪个城市的天气",
        condition="用户没有提到具体城市"
    )
    # 类似流程，但创建 ChatJourneyState
    
    # 3. 从 t2.target 继续创建转换
    t3 = await t2.target.transition_to(tool_state=get_weather)
    
    # 4. 从 t1.target 和 t3.target 创建成功/失败分支
    t4 = await t1.target.transition_to(
        chat_state="简洁友好地告诉用户天气情况：温度、天气状况、湿度",
        condition="查询成功"
    )
    
    # ... 更多转换
    
    # 5. 创建 Journey 内的 Guidelines
    await journey.create_guideline(
        condition="用户输入的城市名称不清晰或有歧义",
        action="礼貌地请用户确认具体是哪个城市"
    )
    # 内部调用链:
    # journey.create_guideline()
    #   -> GuidelineStore.create_guideline()
    #   -> server._add_guideline_evaluation()
    #   -> RelationshipStore.create_relationship() (dependency)
    #   -> GuidelineToolAssociationStore.create_association()
    
    return journey
```

---

## 关键方法签名汇总

### Server 类方法

```python
# 生命周期管理
async def __aenter__(self) -> Server
async def __aexit__(self, exc_type, exc_value, tb) -> bool

# Agent 管理
async def create_agent(self, name: str, description: str, ...) -> Agent
async def list_agents(self) -> Sequence[Agent]
async def get_agent(self, id: AgentId | str) -> Agent

# Journey 管理
async def create_journey(self, title: str, description: str, conditions: list[str | Guideline]) -> Journey

# Customer 管理
async def create_customer(self, name: str, ...) -> Customer
async def get_customer(self, id: CustomerId | str) -> Customer

# Tag 管理
async def create_tag(self, name: str) -> Tag

# 内部方法
def _advance_creation_progress(self) -> None
def _add_guideline_evaluation(self, guideline_id, guideline_content, tool_ids) -> None
def _add_state_evaluation(self, state_id, guideline_content, tools) -> None
def _add_journey_evaluation(self, journey) -> None
async def _process_evaluations(self) -> None
async def _setup_retrievers(self) -> None
```

### Agent 类方法

```python
# Journey 管理
async def create_journey(self, title: str, description: str, conditions: list[str | Guideline]) -> Journey
async def attach_journey(self, journey: Journey) -> None

# Guideline 管理
async def create_guideline(self, condition: str, action: str | None = None, ...) -> Guideline
async def create_observation(self, condition: str, ...) -> Guideline

# Tool 管理
async def attach_tool(self, tool: ToolEntry, condition: str) -> GuidelineId

# Variable 管理
async def create_variable(self, name: str, ...) -> Variable
async def list_variables(self) -> Sequence[Variable]
async def find_variable(self, id: str | None = None, name: str | None = None) -> Variable | None
async def get_variable(self, id: ContextVariableId | str) -> Variable

# Retriever 管理
async def attach_retriever(self, retriever: Callable, id: str | None = None) -> None

# Canned Response 管理
async def create_canned_response(self, template: str, ...) -> CannedResponseId

# Term 管理
async def create_term(self, name: str, description: str, synonyms: Sequence[str] = []) -> Term

# 实验性功能
@property
def experimental_features(self) -> ExperimentalAgentFeatures
```

### Journey 类方法

```python
# 属性
@property
def initial_state(self) -> InitialJourneyState

# State 管理
async def _create_state(self, state_type: type[TState], action: str | None = None, tools: Sequence[ToolEntry] = []) -> TState

# Transition 管理
async def create_transition(self, condition: str | None, source: JourneyState, target: TState) -> JourneyTransition[TState]

# Guideline 管理
async def create_guideline(self, condition: str, action: str | None = None, ...) -> Guideline
async def create_observation(self, condition: str, ...) -> Guideline

# Tool 管理
async def attach_tool(self, tool: ToolEntry, condition: str) -> GuidelineId

# Canned Response 管理
async def create_canned_response(self, template: str, ...) -> CannedResponseId

# Relationship 管理
async def prioritize_over(self, target: Guideline | Journey) -> Relationship
async def depend_on(self, target: Guideline) -> Relationship
async def _create_relationship(self, target, kind, direction) -> Relationship
```

### JourneyState 类方法

```python
# 基类方法
async def _transition(self, condition: str | None = None, state: TState | None = None, action: str | None = None, tools: Sequence[ToolEntry] = [], fork: bool = False, canned_responses: Sequence[CannedResponseId] = []) -> JourneyTransition[JourneyState]
async def _fork(self) -> JourneyTransition[ForkJourneyState]

# 属性
@property
def _internal_action(self) -> str | None

# 子类特定方法 (InitialJourneyState, ChatJourneyState, ToolJourneyState, ForkJourneyState)
async def transition_to(self, ...) -> JourneyTransition[...]  # 多个重载版本
async def fork(self) -> JourneyTransition[ForkJourneyState]
```

### Guideline 类方法

```python
# Relationship 管理
async def entail(self, guideline: Guideline) -> Relationship
async def prioritize_over(self, target: Guideline | Journey) -> Relationship
async def depend_on(self, target: Guideline | Journey) -> Relationship
async def disambiguate(self, targets: Sequence[Guideline | Journey]) -> Sequence[Relationship]
async def reevaluate_after(self, tool: ToolEntry) -> Relationship

# 内部方法
async def _create_relationship(self, target, kind, direction) -> Relationship
```

### _CachedEvaluator 类方法

```python
# 生命周期管理
async def __aenter__(self) -> _CachedEvaluator
async def __aexit__(self, exc_type, exc_value, tb) -> bool

# 评估方法
async def evaluate_guideline(self, entity_id: GuidelineId, g: GuidelineContent, tool_ids: Sequence[ToolId] = []) -> GuidelineEvaluation
async def evaluate_state(self, entity_id: JourneyStateId, g: GuidelineContent, tool_ids: Sequence[ToolId] = []) -> GuidelineEvaluation
async def evaluate_journey(self, journey: Journey) -> JourneyEvaluation

# 内部方法
async def _evaluate_guideline(self, entity_id, g, tool_ids, ...) -> GuidelineEvaluation
def _hash_guideline_evaluation_request(self, g, tool_ids, ...) -> str
def _hash_journey_evaluation_request(self, journey) -> str
def _set_progress(self, key: str, pct: float) -> None
def _progress_for(self, key: str) -> float
```

---

## 核心数据流

### 1. Server 初始化流程

```
main()
  └─> async with p.Server(nlp_service=p.NLPServices.ollama) as server:
        └─> Server.__aenter__()
              ├─> start_parlant(StartupParameters)
              │     ├─> 创建 Container (依赖注入容器)
              │     ├─> 初始化 DocumentDatabase
              │     ├─> 初始化 VectorDatabase
              │     ├─> 初始化 NLPService (Ollama)
              │     ├─> 初始化各种 Store (AgentStore, JourneyStore, GuidelineStore, etc.)
              │     ├─> 初始化 Engine
              │     ├─> 启动 PluginServer
              │     └─> 返回 Container
              ├─> 初始化 _CachedEvaluator
              └─> 初始化 creation progress bar
```

### 2. Agent 创建流程

```
server.create_agent(name, description)
  └─> AgentStore.create_agent()
        ├─> 生成 AgentId
        ├─> 创建 Agent 文档
        ├─> 保存到 DocumentDatabase
        └─> 返回 Agent 对象
```

### 3. Journey 创建流程

```
agent.create_journey(title, description, conditions)
  └─> server.create_journey()
        ├─> 处理 conditions (字符串转 Guideline)
        ├─> JourneyStore.create_journey()
        │     ├─> 生成 JourneyId
        │     ├─> 创建 initial_state (JourneyNode)
        │     ├─> 保存到 DocumentDatabase
        │     └─> 返回 Journey 对象
        └─> agent.attach_journey()
              └─> JourneyStore.upsert_tag() (添加 agent tag)
```

### 4. State 和 Transition 创建流程

```
journey.initial_state.transition_to(tool_state=get_weather, condition="...")
  └─> InitialJourneyState.transition_to()
        └─> JourneyState._transition()
              ├─> journey._create_state(ToolJourneyState, tools=[get_weather])
              │     ├─> PluginServer.enable_tool(get_weather)
              │     ├─> JourneyStore.create_node()
              │     │     ├─> 生成 JourneyNodeId
              │     │     ├─> 创建 Node 文档
              │     │     └─> 保存到 DocumentDatabase
              │     ├─> JourneyStore.set_node_metadata(key="journey_node", value={"kind": "tool"})
              │     └─> 返回 ToolJourneyState 对象
              └─> journey.create_transition(condition, source, target)
                    ├─> server._add_state_evaluation(target.id, GuidelineContent, tool_ids)
                    │     └─> 添加到 _node_evaluations 字典
                    ├─> JourneyStore.create_edge()
                    │     ├─> 生成 JourneyEdgeId
                    │     ├─> 创建 Edge 文档
                    │     └─> 保存到 DocumentDatabase
                    └─> 返回 JourneyTransition 对象
```

### 5. Guideline 创建流程

```
agent.create_guideline(condition, action, tools)
  ├─> 启用所有 tools
  │     └─> PluginServer.enable_tool() for each tool
  ├─> GuidelineStore.create_guideline()
  │     ├─> 生成 GuidelineId
  │     ├─> 创建 Guideline 文档
  │     └─> 保存到 DocumentDatabase
  ├─> 关联 canned_responses (如果有)
  │     └─> CannedResponseStore.upsert_tag()
  ├─> server._add_guideline_evaluation()
  │     └─> 添加到 _guideline_evaluations 字典
  └─> 创建 tool associations
        └─> GuidelineToolAssociationStore.create_association() for each tool
```

### 6. 评估处理流程 (在 Server.__aexit__ 时)

```
Server.__aexit__()
  └─> _process_evaluations()
        ├─> 创建所有评估任务
        │     ├─> 为每个 guideline 创建 asyncio.Task
        │     ├─> 为每个 node 创建 asyncio.Task
        │     └─> 为每个 journey 创建 asyncio.Task
        ├─> 并发执行所有任务 (async_utils.safe_gather)
        │     └─> 每个任务调用 _CachedEvaluator.evaluate_*()
        │           ├─> 检查缓存 (JSONFileDocumentDatabase)
        │           ├─> 如果没有缓存:
        │           │     ├─> BehavioralChangeEvaluator.create_evaluation_task()
        │           │     ├─> 轮询 EvaluationStore.read_evaluation()
        │           │     ├─> 等待评估完成
        │           │     ├─> 获取 invoice 数据
        │           │     └─> 缓存结果
        │           └─> 返回评估结果
        ├─> 显示进度条 (如果不是 TRACE 级别)
        └─> 将评估结果写入 metadata
              ├─> GuidelineStore.set_metadata() for guidelines
              ├─> JourneyStore.set_node_metadata() for nodes
              └─> JourneyStore.set_node_metadata() for journey nodes
```

---

## 重要的数据结构

### 1. ToolResult

```python
@dataclass
class ToolResult:
    data: dict[str, Any]
    metadata: dict[str, JSONSerializable] = field(default_factory=dict)
    control: ControlOptions = field(default_factory=dict)
```

### 2. GuidelineContent

```python
@dataclass
class GuidelineContent:
    condition: str | None
    action: str | None
```

### 3. JourneyTransition

```python
@dataclass(frozen=True)
class JourneyTransition(Generic[TState]):
    id: JourneyTransitionId
    condition: str | None
    source: JourneyState
    target: TState
    metadata: Mapping[str, JSONSerializable]
```

### 4. Relationship

```python
@dataclass(frozen=True)
class Relationship:
    id: RelationshipId
    kind: RelationshipKind  # ENTAILMENT, PRIORITY, DEPENDENCY, DISAMBIGUATION, REEVALUATION
    source: RelationshipEntityId
    target: RelationshipEntityId
```

### 5. Tag

```python
@dataclass(frozen=True)
class Tag:
    id: TagId
    name: str
    
    # 静态方法
    @staticmethod
    def preamble() -> TagId
    @staticmethod
    def for_agent_id(agent_id: AgentId) -> TagId
    @staticmethod
    def for_journey_id(journey_id: JourneyId) -> TagId
    @staticmethod
    def for_guideline_id(guideline_id: GuidelineId) -> TagId
    @staticmethod
    def for_journey_node_id(node_id: JourneyNodeId) -> TagId
```

---

## 关键常量和枚举

### 1. END_JOURNEY

```python
END_JOURNEY = EndJourneyState(
    id=JourneyStateId("__end__"),
    action=None,
    tools=[],
    metadata={},
    _journey=None,
)
```

### 2. RelationshipKind

```python
class RelationshipKind(enum.Enum):
    ENTAILMENT = "entailment"          # 蕴含关系
    PRIORITY = "priority"              # 优先级关系
    DEPENDENCY = "dependency"          # 依赖关系
    DISAMBIGUATION = "disambiguation"  # 消歧关系
    REEVALUATION = "reevaluation"      # 重新评估关系
```

### 3. CompositionMode

```python
class CompositionMode(enum.Enum):
    FLUID = _CompositionMode.CANNED_FLUID          # 流畅生成
    COMPOSITED = _CompositionMode.CANNED_COMPOSITED # 组合式生成
    STRICT = _CompositionMode.CANNED_STRICT        # 严格模式
```

### 4. EventKind

```python
class EventKind(enum.Enum):
    MESSAGE = "message"
    TOOL = "tool"
    STATUS = "status"
```

### 5. EventSource

```python
class EventSource(enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"
```

---

## 工具装饰器机制

### @p.tool 装饰器

```python
@p.tool
async def get_weather(context: p.ToolContext, location: str) -> p.ToolResult:
    """查询指定地区的天气信息"""
    # 实现...
```

**工作原理**:
1. `@p.tool` 装饰器将函数注册到 PluginServer
2. 函数签名被解析，生成 ToolParameterDescriptor
3. 工具被包装成 ToolEntry 对象
4. 当在 Journey 或 Guideline 中使用时，调用 `PluginServer.enable_tool()`
5. 工具在运行时通过 ToolId 被引用和调用

**ToolEntry 结构**:
```python
@dataclass
class ToolEntry:
    tool: Tool
    # Tool 包含:
    # - name: str
    # - description: str
    # - parameters: Sequence[ToolParameterDescriptor]
    # - function: Callable
```

---

## Store 层架构

### 核心 Store 接口

1. **AgentStore**: 管理 Agent 实体
2. **JourneyStore**: 管理 Journey、Node、Edge
3. **GuidelineStore**: 管理 Guideline
4. **SessionStore**: 管理 Session 和 Event
5. **CustomerStore**: 管理 Customer
6. **TagStore**: 管理 Tag
7. **RelationshipStore**: 管理 Relationship
8. **ContextVariableStore**: 管理 Variable
9. **CannedResponseStore**: 管理 CannedResponse
10. **GlossaryStore**: 管理 Term
11. **CapabilityStore**: 管理 Capability
12. **GuidelineToolAssociationStore**: 管理 Guideline-Tool 关联
13. **EvaluationStore**: 管理 Evaluation

### 持久化层

**DocumentDatabase**:
- TransientDocumentDatabase: 内存存储
- JSONFileDocumentDatabase: JSON 文件存储

**VectorDatabase**:
- TransientVectorDatabase: 内存向量存储

---

## NLP 服务集成

### NLPServices 工厂类

```python
class NLPServices:
    @staticmethod
    def azure(container: Container) -> NLPService
    
    @staticmethod
    def openai(container: Container) -> NLPService
    
    @staticmethod
    def anthropic(container: Container) -> NLPService
    
    @staticmethod
    def cerebras(container: Container) -> NLPService
    
    @staticmethod
    def together(container: Container) -> NLPService
    
    @staticmethod
    def gemini(container: Container) -> NLPService
    
    @staticmethod
    def litellm(container: Container) -> NLPService
    
    @staticmethod
    def vertex(container: Container) -> NLPService
    
    @staticmethod
    def ollama(container: Container) -> NLPService
```

### Ollama 配置

在 `weather_agent.py` 中:
```python
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "qwen2.5:latest"
os.environ["OLLAMA_EMBEDDING_MODEL"] = "nomic-embed-text:latest"
os.environ["OLLAMA_API_TIMEOUT"] = "300"
```

---

## 总结

### 核心概念关系图

```
Server
  ├─> Container (依赖注入)
  ├─> PluginServer (工具管理)
  ├─> _CachedEvaluator (评估缓存)
  └─> Agent (多个)
        ├─> Journey (多个)
        │     ├─> JourneyState (多个)
        │     │     ├─> InitialJourneyState
        │     │     ├─> ChatJourneyState
        │     │     ├─> ToolJourneyState
        │     │     ├─> ForkJourneyState
        │     │     └─> EndJourneyState
        │     ├─> JourneyTransition (多个)
        │     └─> Guideline (Journey 内，多个)
        ├─> Guideline (Agent 级别，多个)
        ├─> Variable (多个)
        ├─> Term (多个)
        ├─> CannedResponse (多个)
        └─> Retriever (多个)
```

### 关键设计模式

1. **Context Manager**: Server 使用 async context manager 管理生命周期
2. **Dependency Injection**: 使用 lagom Container 进行依赖注入
3. **Store Pattern**: 所有数据访问通过 Store 接口
4. **Decorator Pattern**: @p.tool 装饰器注册工具
5. **State Machine**: Journey 使用状态机模式
6. **Caching**: _CachedEvaluator 缓存评估结果
7. **Event-Driven**: Session 使用事件驱动架构
8. **Async/Await**: 全面使用异步编程

### 执行流程总结

1. **初始化阶段**: Server 启动 → 创建 Container → 初始化各种服务
2. **定义阶段**: 创建 Agent → 创建 Journey → 定义 States 和 Transitions → 创建 Guidelines
3. **评估阶段**: 退出 Server context → 处理所有评估 → 缓存结果 → 写入 metadata
4. **运行阶段**: 创建 Session → 发布 Event → Engine 处理 → 生成响应

---

## 参考文件位置

- **SDK 入口**: `.venv/lib/site-packages/parlant/sdk.py`
- **核心应用**: `.venv/lib/site-packages/parlant/core/application.py`
- **服务器启动**: `.venv/lib/site-packages/parlant/bin/server.py`
- **Agent 管理**: `.venv/lib/site-packages/parlant/core/agents.py`
- **Journey 管理**: `.venv/lib/site-packages/parlant/core/journeys.py`
- **Guideline 管理**: `.venv/lib/site-packages/parlant/core/guidelines.py`
- **工具系统**: `.venv/lib/site-packages/parlant/core/tools.py`
- **示例代码**: `weather_agent.py`

---

**文档版本**: 1.0  
**创建日期**: 2025-11-07  
**分析范围**: weather_agent.py + Parlant SDK v0.x
