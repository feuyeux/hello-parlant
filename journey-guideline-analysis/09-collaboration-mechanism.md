# Journey 和 Guideline 协作机制总结

## 核心协作模式

### 1. 条件关联模式

**Journey 使用 Guideline 作为激活条件**

```
Journey
  ├─ conditions: [GuidelineId1, GuidelineId2]
  │
  └─ 当任一 Guideline 匹配时，Journey 被激活
```

**实现**:
```python
# Journey 创建时
journey = Journey(
    conditions=[guideline1.id, guideline2.id],
    ...
)

# 查找激活的 Journey
journeys = await journey_store.list_journeys(condition=matched_guideline_id)
```

### 2. 投影转换模式

**Journey 图结构 → Guideline 列表**

```
Journey Graph                    Projected Guidelines
┌─────────────┐                 ┌──────────────────────┐
│   Root      │                 │ Guideline 1 (Root)   │
│   ├─ Node1  │    投影         │ Guideline 2 (Node1)  │
│   ├─ Node2  │   ────→         │ Guideline 3 (Node2)  │
│   └─ Node3  │                 │ Guideline 4 (Node3)  │
└─────────────┘                 └──────────────────────┘
```

**关键机制**:
- 每个 (Edge, Node) 对生成一个 Guideline
- Guideline ID 格式: `journey_node:<node_id>[:<edge_id>]`
- 元数据中保存 `follow_ups` 关系

### 3. 标签关联模式

**Journey 通过特殊标签关联 Guideline**

```python
# Journey 创建时，为条件 Guideline 添加标签
journey_tag = Tag.for_journey_id(journey.id)
await guideline_store.upsert_tag(
    guideline_id=condition_guideline.id,
    tag_id=journey_tag,
)

# Journey 删除时，清理 Guideline
if guideline.tags == [journey_tag]:
    await guideline_store.delete_guideline(guideline_id)
else:
    await guideline_store.remove_tag(guideline_id, journey_tag)
```

**生命周期管理**:
- Guideline 可以属于多个 Journey
- 只有当 Guideline 仅属于一个 Journey 时，删除 Journey 才删除 Guideline

## 数据流向

### 创建流程
```
API Layer
  ↓ (JourneyCreationParamsDTO)
Application Layer
  ├─ 创建 Guideline (条件)
  ├─ 创建 Journey (关联 Guideline ID)
  └─ 添加 Journey 标签到 Guideline
  ↓
Storage Layer
  ├─ GuidelineDocumentStore: 存储 Guideline
  ├─ JourneyVectorStore: 存储 Journey
  ├─ 创建关联表记录
  └─ 向量化 Journey 内容
  ↓
Database
  ├─ DocumentDatabase: 结构化数据
  └─ VectorDatabase: 向量数据
```

### 执行流程
```
User Input
  ↓
Engine
  ├─ 向量搜索相关 Journey
  ├─ 检查 Journey 条件 (Guideline)
  ├─ 投影 Journey → Guideline
  ├─ 匹配 Guideline
  │   ├─ 普通 Guideline: 直接匹配
  │   └─ Journey Guideline: JourneyNodeSelectionBatch
  │       ├─ 构建节点包装器
  │       ├─ 剪枝节点
  │       ├─ LLM 推理
  │       └─ 选择下一步
  ├─ 执行 Guideline action
  ├─ 更新 Journey 路径
  └─ 生成响应
  ↓
User Output
```

## 关键设计决策

### 1. 为什么 Journey 使用 Guideline 作为条件？

**优势**:
- **统一接口**: Guideline 是系统的基本单元，复用现有机制
- **灵活性**: 条件可以独立管理和更新
- **可组合性**: 同一个 Guideline 可以作为多个 Journey 的条件

**实现**:
```python
# Journey 条件是 Guideline ID 列表
conditions: Sequence[GuidelineId]

# 激活检查
if any(guideline.id in journey.conditions for guideline in matched_guidelines):
    activate_journey(journey)
```

### 2. 为什么需要投影机制？

**原因**:
- 引擎处理的是 Guideline 列表，不是图结构
- 需要将 Journey 的图结构转换为引擎可处理的格式

**好处**:
- **透明性**: 引擎不需要知道 Journey 的存在
- **一致性**: Journey 和普通 Guideline 使用相同的处理流程
- **可扩展性**: 可以添加新的 Guideline 类型而不改变引擎

### 3. 为什么使用元数据存储 Journey 信息？

**原因**:
- Guideline 是不可变的 (`frozen=True`)
- 元数据提供灵活的扩展机制

**存储内容**:
```python
{
    "journey_node": {
        "follow_ups": [...],      # 后续节点
        "index": "1",             # 节点索引
        "journey_id": "...",      # 所属 Journey
        "kind": "chat",           # 节点类型
    },
    "customer_dependent_action_data": {
        "is_customer_dependent": true,
        "customer_action": "...",
    },
    ...
}
```

### 4. 为什么需要 JourneyNodeSelectionBatch？

**原因**:
- Journey 需要特殊的匹配逻辑
- 需要跟踪执行路径
- 需要处理节点转换

**功能**:
- 构建节点图
- 剪枝不相关节点
- LLM 推理选择下一步
- 验证路径合法性
- 更新执行状态

## 协作优势

### 1. 模块化
- Journey 和 Guideline 各自独立
- 通过明确的接口协作
- 易于测试和维护

### 2. 可扩展性
- 可以添加新的 Guideline 类型
- 可以添加新的 Journey 节点类型
- 可以添加新的匹配策略

### 3. 性能优化
- 向量搜索快速找到相关 Journey
- 节点剪枝减少 LLM 输入
- 并行处理提高吞吐量
- 自动返回避免不必要的推理

### 4. 灵活性
- Guideline 可以独立使用
- Guideline 可以作为 Journey 的一部分
- Journey 可以共享 Guideline
- 支持复杂的条件逻辑

## 潜在改进点

### 1. 投影缓存
**问题**: 每次执行都需要投影 Journey
**改进**: 缓存投影结果，只在 Journey 更新时重新投影

### 2. 路径持久化
**问题**: Journey 路径存储在内存中
**改进**: 将路径持久化到数据库，支持跨会话恢复

### 3. 条件评估优化
**问题**: 需要查询所有 Journey 的条件
**改进**: 建立条件索引，快速找到相关 Journey

### 4. 节点类型扩展
**问题**: 节点类型有限
**改进**: 支持更多节点类型（如条件分支、循环等）

### 5. 可视化工具
**问题**: 难以理解复杂的 Journey
**改进**: 提供交互式可视化工具（已有 Mermaid 图表）

## 总结

Journey 和 Guideline 的协作机制是一个精心设计的系统：

1. **Guideline 是基础**: 所有行为规则都是 Guideline
2. **Journey 是组织**: 将 Guideline 组织成有序的流程
3. **投影是桥梁**: 将 Journey 转换为引擎可处理的格式
4. **元数据是载体**: 存储 Journey 的结构信息
5. **标签是纽带**: 管理 Journey 和 Guideline 的生命周期

这种设计实现了：
- **统一性**: 引擎只需处理 Guideline
- **灵活性**: 支持复杂的交互流程
- **可维护性**: 模块化的架构
- **可扩展性**: 易于添加新功能

通过这种协作机制，系统能够同时支持简单的规则（独立 Guideline）和复杂的流程（Journey），为构建智能对话系统提供了强大的基础。
