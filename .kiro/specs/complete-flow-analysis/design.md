# Design Document

## Overview

本设计文档定义了如何创建完整、清晰的 Parlant 系统流程分析文档，特别是以 `weather_agent.py` 为例，详细描述系统的启动流程、请求处理流程，包括方法间的调用关系和大模型服务（LLM）的调用次数统计。

该文档将作为 `journey-guideline-analysis` 文档集的补充，填补现有文档在实际运行流程方面的空白。

## Architecture

### 文档架构

新文档将采用以下结构：

```
journey-guideline-analysis/
├── 11-weather-agent-startup-flow.md      # 启动流程详解
├── 12-weather-agent-request-flow.md      # 请求处理流程详解
├── 13-llm-invocation-analysis.md         # LLM 调用分析
└── 14-method-call-chains.md              # 方法调用链详解
```

### 分析层次

文档将从以下三个层次进行分析：

1. **宏观层次**: 整体流程概览，使用序列图和流程图
2. **中观层次**: 模块间的交互，方法调用关系
3. **微观层次**: 具体方法实现，参数传递，LLM 调用点

## Components and Interfaces

### 核心组件识别

基于 `weather_agent.py` 和 Parlant SDK，识别以下核心组件：

#### 1. SDK 层组件
- `Server`: 服务器主类，管理整个系统生命周期
- `Agent`: 代理实体，管理 Journey 和 Guideline
- `Journey`: 对话流程图结构
- `Guideline`: 条件-动作规则
- `ToolEntry`: 工具注册和管理

#### 2. 核心服务组件
- `NLPService`: 大语言模型服务接口（Ollama）
- `Application`: 应用层核心，协调各模块
- `Container`: 依赖注入容器（Lagom）
- `PluginServer`: 工具服务器

#### 3. 存储组件
- `DocumentDatabase`: 文档数据库（JSON 文件或内存）
- `VectorDatabase`: 向量数据库（用于语义搜索）
- `GuidelineStore`: Guideline 存储
- `JourneyStore`: Journey 存储

#### 4. 引擎组件
- `Engine`: 对话引擎核心
- `GuidelineMatcher`: Guideline 匹配器
- `JourneyNodeSelectionBatch`: Journey 节点选择
- `MessageGenerator`: 响应生成器

### 接口定义

#### Server 接口
```python
class Server:
    async def __aenter__(self) -> Server:
        # 启动服务器，初始化所有组件
        
    async def __aexit__(self, ...):
        # 关闭服务器，清理资源
        
    async def create_agent(self, name, description) -> Agent:
        # 创建代理
```

#### Agent 接口
```python
class Agent:
    async def create_journey(self, title, description, conditions) -> Journey:
        # 创建 Journey
        
    async def create_guideline(self, condition, action, tools) -> Guideline:
        # 创建 Guideline
```

#### Journey 接口
```python
class Journey:
    @property
    def initial_state(self) -> InitialJourneyState:
        # 获取初始状态
        
    async def create_guideline(self, condition, action) -> Guideline:
        # 在 Journey 内创建 Guideline
```

## Data Models

### 启动流程数据流

```
Environment Variables
    ↓
Server Configuration
    ↓
Container Setup
    ↓
Database Initialization
    ↓
NLP Service Connection
    ↓
Agent Creation
    ↓
Journey/Guideline Creation
    ↓
Evaluation & Caching
```

### 请求处理数据流

```
User Message
    ↓
Session Context
    ↓
Active Journeys
    ↓
Journey Projection → Guidelines
    ↓
Guideline Matching
    ↓
Tool Execution (if needed)
    ↓
Response Generation
    ↓
State Update
```


### LLM 调用点数据模型

```python
@dataclass
class LLMInvocation:
    location: str              # 调用位置（方法名）
    purpose: str               # 调用目的
    input_type: str            # 输入类型
    output_type: str           # 输出类型
    estimated_tokens: int      # 预估 token 数
    is_optional: bool          # 是否可选
```

## Error Handling

### 启动阶段错误处理

1. **环境变量缺失**: 
   - 检查点: `NLPServices.ollama()`
   - 处理: 抛出 `SDKError` 并提示缺失的环境变量

2. **数据库初始化失败**:
   - 检查点: `DocumentDatabase.__aenter__()`
   - 处理: 回滚已初始化的组件，清理资源

3. **NLP 服务连接失败**:
   - 检查点: `OllamaService.verify_models()`
   - 处理: 提示用户检查 Ollama 服务状态

### 请求处理阶段错误处理

1. **Journey 匹配失败**:
   - 检查点: `GuidelineMatcher.match_guidelines()`
   - 处理: 使用默认响应或回退策略

2. **工具调用失败**:
   - 检查点: `ToolContext.execute()`
   - 处理: 记录错误，返回错误信息给用户

3. **LLM 调用超时**:
   - 检查点: `SchematicGenerator.generate()`
   - 处理: 重试或使用缓存结果

## Testing Strategy

### 单元测试

1. **组件初始化测试**
   - 测试 Server 初始化流程
   - 测试 Agent 创建流程
   - 测试 Journey/Guideline 创建流程

2. **数据流转测试**
   - 测试投影机制
   - 测试匹配逻辑
   - 测试状态更新

### 集成测试

1. **完整启动流程测试**
   - 从 `asyncio.run(main())` 到服务就绪
   - 验证所有组件正确初始化

2. **端到端请求测试**
   - 模拟用户输入
   - 验证完整的请求处理流程
   - 检查响应正确性

### 性能测试

1. **LLM 调用次数统计**
   - 记录每个场景的 LLM 调用次数
   - 识别优化机会

2. **响应时间测试**
   - 测量各阶段耗时
   - 识别性能瓶颈

## Design Details

### 11-weather-agent-startup-flow.md 设计

#### 内容结构

1. **概述**
   - 启动流程的目标和范围
   - 涉及的主要组件

2. **环境准备**
   - 环境变量设置
   - 依赖检查

3. **详细启动步骤**
   - 步骤 1: `asyncio.run(main())` 调用
   - 步骤 2: `Server.__aenter__()` 执行
   - 步骤 3: 容器初始化
   - 步骤 4: 数据库初始化
   - 步骤 5: NLP 服务连接
   - 步骤 6: Agent 创建
   - 步骤 7: Journey 创建
   - 步骤 8: Guideline 创建
   - 步骤 9: 评估和缓存

4. **方法调用链**
   - 完整的调用栈
   - 每个方法的参数和返回值

5. **数据库操作**
   - 创建的集合
   - 插入的文档
   - 向量化操作

6. **LLM 调用点**
   - 评估阶段的 LLM 调用
   - 调用目的和输入内容

7. **可视化**
   - Mermaid 序列图
   - 时间线图

#### 关键信息提取

从代码中提取：
- `Server.__aenter__()` 的完整实现
- `start_parlant()` 函数的流程
- `Container` 的配置过程
- `_CachedEvaluator` 的工作机制

### 12-weather-agent-request-flow.md 设计

#### 内容结构

1. **概述**
   - 请求处理的目标和范围
   - 涉及的主要组件

2. **请求场景**
   - 场景 1: 用户直接提供城市名
   - 场景 2: 用户未提供城市名
   - 场景 3: 查询不支持的城市
   - 场景 4: 连续查询多个城市

3. **详细处理步骤**（以场景 1 为例）
   - 步骤 1: 接收用户消息
   - 步骤 2: 加载会话上下文
   - 步骤 3: 查找激活的 Journey
   - 步骤 4: Journey 投影为 Guideline
   - 步骤 5: Guideline 匹配
   - 步骤 6: 节点选择（LLM 推理）
   - 步骤 7: 工具调用
   - 步骤 8: 响应生成（LLM 推理）
   - 步骤 9: 状态更新
   - 步骤 10: 返回响应

4. **方法调用链**
   - 每个步骤的详细调用栈
   - 参数传递和数据转换

5. **状态变化**
   - Journey 路径更新
   - Session 事件记录
   - 上下文变量变化

6. **LLM 调用详解**
   - 调用位置
   - 输入 prompt 结构
   - 输出 schema
   - Token 估算

7. **可视化**
   - Mermaid 流程图
   - 数据流图
   - 状态转换图

#### 关键信息提取

从代码中提取：
- Engine 的消息处理流程
- `GuidelineMatcher.match_guidelines()` 实现
- `JourneyNodeSelectionBatch.process()` 实现
- `MessageGenerator.generate()` 实现

### 13-llm-invocation-analysis.md 设计

#### 内容结构

1. **概述**
   - LLM 调用的重要性
   - 分析方法

2. **启动阶段 LLM 调用**
   - 调用点 1: Guideline 评估
     - 位置: `_CachedEvaluator.evaluate_guideline()`
     - 目的: 生成 Guideline 属性
     - 输入: Guideline 内容
     - 输出: 属性字典
   - 调用点 2: Journey 评估
     - 位置: `_CachedEvaluator.evaluate_journey()`
     - 目的: 生成节点和边属性
     - 输入: Journey 结构
     - 输出: 节点/边属性字典

3. **请求处理阶段 LLM 调用**
   - 调用点 1: Journey 激活判断
     - 位置: Journey 条件匹配
     - 目的: 判断 Journey 是否适用
     - 输入: 用户消息 + Journey 条件
     - 输出: 布尔值
   - 调用点 2: 节点选择
     - 位置: `JourneyNodeSelectionBatch.process()`
     - 目的: 选择下一个要执行的节点
     - 输入: 转换图 + 对话历史
     - 输出: 节点 ID
   - 调用点 3: 响应生成
     - 位置: `MessageGenerator.generate()`
     - 目的: 生成自然语言响应
     - 输入: Guideline action + 工具结果
     - 输出: 响应文本

4. **调用次数统计**
   - 按场景统计
   - 按阶段统计
   - 优化建议

5. **Token 消耗分析**
   - 输入 token 估算
   - 输出 token 估算
   - 成本估算

6. **优化机会**
   - 缓存策略
   - 批处理
   - 提前终止

7. **可视化**
   - LLM 调用时序图
   - Token 消耗分布图

### 14-method-call-chains.md 设计

#### 内容结构

1. **概述**
   - 方法调用链的重要性
   - 分析方法

2. **启动流程调用链**
   ```
   asyncio.run(main)
   └─ main()
      └─ Server.__aenter__()
         ├─ start_parlant()
         │  ├─ Container 初始化
         │  ├─ Database 初始化
         │  └─ NLP Service 初始化
         ├─ Agent.create_agent()
         │  └─ AgentStore.create_agent()
         └─ Agent.create_journey()
            ├─ JourneyStore.create_journey()
            ├─ GuidelineStore.create_guideline()
            └─ _CachedEvaluator.evaluate_*()
   ```

3. **请求处理调用链**
   ```
   Engine.process_message()
   ├─ load_context()
   ├─ find_active_journeys()
   ├─ project_journeys()
   │  └─ JourneyGuidelineProjection.project()
   ├─ GuidelineMatcher.match_guidelines()
   │  └─ JourneyNodeSelectionBatch.process()
   │     ├─ build_node_wrappers()
   │     ├─ get_pruned_nodes()
   │     ├─ get_journey_transition_map_text()
   │     └─ SchematicGenerator.generate() [LLM]
   ├─ execute_tools()
   │  └─ get_weather()
   ├─ MessageGenerator.generate() [LLM]
   └─ update_state()
   ```

4. **关键方法详解**
   - 每个方法的签名
   - 参数说明
   - 返回值说明
   - 副作用

5. **数据转换**
   - 输入数据格式
   - 中间数据格式
   - 输出数据格式

6. **可视化**
   - 调用树图
   - 数据流图

## Implementation Plan

### Phase 1: 代码分析和信息收集

1. 深入分析 `weather_agent.py`
2. 追踪 SDK 源代码
3. 识别所有关键方法
4. 记录 LLM 调用点
5. 绘制初步流程图

### Phase 2: 文档编写

1. 创建 `11-weather-agent-startup-flow.md`
   - 编写启动流程详解
   - 添加序列图
   - 标注 LLM 调用点

2. 创建 `12-weather-agent-request-flow.md`
   - 编写请求处理流程
   - 添加流程图
   - 详细描述各场景

3. 创建 `13-llm-invocation-analysis.md`
   - 统计 LLM 调用次数
   - 分析 Token 消耗
   - 提供优化建议

4. 创建 `14-method-call-chains.md`
   - 绘制完整调用链
   - 详细说明每个方法
   - 标注数据转换点

### Phase 3: 集成和完善

1. 更新 `README.md`
   - 添加新文档链接
   - 更新导航结构

2. 更新 `INDEX.md`
   - 添加新内容索引
   - 更新快速查找指南

3. 更新 `SUMMARY.md`
   - 补充流程分析总结
   - 更新关键指标

4. 交叉引用
   - 在新文档中引用现有文档
   - 在现有文档中引用新文档

### Phase 4: 验证和优化

1. 代码验证
   - 运行 `weather_agent.py`
   - 验证流程描述准确性
   - 确认 LLM 调用次数

2. 文档审查
   - 检查完整性
   - 检查准确性
   - 检查可读性

3. 优化改进
   - 添加更多示例
   - 优化图表
   - 补充说明

## Cross-References

### 与现有文档的关联

- `11-weather-agent-startup-flow.md` 引用:
  - [02-core-models.md](./02-core-models.md) - 数据模型定义
  - [03-storage-layer.md](./03-storage-layer.md) - 存储层初始化
  - [04-application-layer.md](./04-application-layer.md) - 应用层模块

- `12-weather-agent-request-flow.md` 引用:
  - [06-journey-guideline-projection.md](./06-journey-guideline-projection.md) - 投影机制
  - [07-engine-integration.md](./07-engine-integration.md) - 引擎集成
  - [08-complete-flow.md](./08-complete-flow.md) - 完整流程

- `13-llm-invocation-analysis.md` 引用:
  - [07-engine-integration.md](./07-engine-integration.md) - LLM 推理流程
  - [08-complete-flow.md](./08-complete-flow.md) - 性能优化点

- `14-method-call-chains.md` 引用:
  - 所有现有文档 - 方法实现细节

## Success Criteria

### 文档质量标准

1. **完整性**
   - 覆盖从启动到请求处理的完整流程
   - 包含所有关键方法的调用链
   - 统计所有 LLM 调用点

2. **准确性**
   - 流程描述与实际代码一致
   - LLM 调用次数准确
   - 方法签名和参数正确

3. **清晰性**
   - 使用清晰的语言描述
   - 提供丰富的可视化图表
   - 合理的章节结构

4. **实用性**
   - 开发者能快速理解流程
   - 能够定位性能瓶颈
   - 能够指导优化工作

### 验收标准

1. 开发者能够通过文档理解 `weather_agent.py` 的完整运行流程
2. 能够准确回答"这个场景会调用几次 LLM"的问题
3. 能够绘制出任意请求的完整方法调用链
4. 文档与现有文档集成良好，交叉引用完整
