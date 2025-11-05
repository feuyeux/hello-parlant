# Journey 和 Guideline 源代码分析

## 概述

本目录包含对 `src/parlant` 中 Journey 和 Guideline 相关代码的深入分析，涵盖数据模型、存储层、应用层、API 层、引擎集成以及两者的协作机制。

## 文档列表

1. **[01-overview.md](./01-overview.md)** - 概览和架构总览
   - 核心概念介绍
   - 架构层次说明
   - 文档结构导航

2. **[02-core-models.md](./02-core-models.md)** - 核心数据模型分析
   - Guideline 数据模型
   - Journey 数据模型（Journey, JourneyNode, JourneyEdge）
   - 关联关系说明

3. **[03-storage-layer.md](./03-storage-layer.md)** - 存储层实现
   - GuidelineDocumentStore 实现
   - JourneyVectorStore 实现
   - 双存储架构（文档数据库 + 向量数据库）
   - CRUD 操作详解

4. **[04-application-layer.md](./04-application-layer.md)** - 应用层模块
   - GuidelineModule 业务逻辑
   - JourneyModule 业务逻辑
   - 关系管理
   - 生命周期管理

5. **[05-api-layer.md](./05-api-layer.md)** - API 层实现
   - RESTful API 端点
   - 数据传输对象 (DTO)
   - Mermaid 图表生成
   - 授权策略

6. **[06-journey-guideline-projection.md](./06-journey-guideline-projection.md)** - Journey 到 Guideline 的投影机制
   - JourneyGuidelineProjection 类
   - 投影算法详解
   - Guideline ID 格式
   - 元数据结构
   - 投影示例

7. **[07-engine-integration.md](./07-engine-integration.md)** - 引擎层集成
   - GuidelineMatcher 实现
   - JourneyNodeSelectionBatch 详解
   - 节点类型和状态
   - LLM 推理流程
   - 路径验证

8. **[08-complete-flow.md](./08-complete-flow.md)** - 完整请求流程
   - 创建 Journey 的完整流程
   - 执行 Journey 的完整流程
   - 查询 Journey 的完整流程
   - 性能优化点

9. **[09-collaboration-mechanism.md](./09-collaboration-mechanism.md)** - 协作机制总结
   - 核心协作模式
   - 数据流向
   - 关键设计决策
   - 协作优势
   - 潜在改进点

10. **[10-class-diagrams.md](./10-class-diagrams.md)** - 类图和关系图
   - 核心数据模型类图
   - 存储层类图
   - 应用层类图
   - 投影机制类图
   - 引擎集成类图
   - API 层类图
   - 完整系统交互序列图
   - 数据流图
   - 关系图

## 快速导航

### 按角色导航

**后端开发者**:
- 从 [02-core-models.md](./02-core-models.md) 了解数据模型
- 阅读 [03-storage-layer.md](./03-storage-layer.md) 了解存储实现
- 查看 [04-application-layer.md](./04-application-layer.md) 了解业务逻辑

**API 开发者**:
- 阅读 [05-api-layer.md](./05-api-layer.md) 了解 API 设计
- 查看 [08-complete-flow.md](./08-complete-flow.md) 了解请求流程

**AI 引擎开发者**:
- 阅读 [06-journey-guideline-projection.md](./06-journey-guideline-projection.md) 了解投影机制
- 查看 [07-engine-integration.md](./07-engine-integration.md) 了解引擎集成

**架构师**:
- 从 [01-overview.md](./01-overview.md) 开始
- 阅读 [09-collaboration-mechanism.md](./09-collaboration-mechanism.md) 了解整体设计

### 按主题导航

**数据模型**: 02 → 03
**业务逻辑**: 04 → 05
**引擎集成**: 06 → 07
**完整流程**: 08
**设计思想**: 09

## 核心概念速查

### Guideline
- **定义**: 条件-动作规则
- **结构**: `condition` + `action`
- **存储**: GuidelineDocumentStore
- **用途**: 指导 AI Agent 行为

### Journey
- **定义**: 有向图结构的多步骤流程
- **组成**: Journey + JourneyNode + JourneyEdge
- **存储**: JourneyVectorStore (双存储)
- **用途**: 引导用户完成复杂任务

### 投影 (Projection)
- **定义**: 将 Journey 图转换为 Guideline 列表
- **实现**: JourneyGuidelineProjection
- **目的**: 使引擎能够处理 Journey

### 节点选择 (Node Selection)
- **定义**: 选择 Journey 中下一个要执行的节点
- **实现**: JourneyNodeSelectionBatch
- **方法**: LLM 推理 + 路径验证

## 关键文件位置

```
src/parlant/
├── core/
│   ├── guidelines.py                    # Guideline 核心模型和存储
│   ├── journeys.py                      # Journey 核心模型和存储
│   ├── journey_guideline_projection.py  # 投影机制
│   ├── guideline_tool_associations.py   # Guideline-Tool 关联
│   ├── app_modules/
│   │   ├── guidelines.py                # Guideline 应用层
│   │   └── journeys.py                  # Journey 应用层
│   └── engines/alpha/
│       └── guideline_matching/
│           ├── guideline_matcher.py     # Guideline 匹配器
│           └── generic/
│               ├── journey_node_selection_batch.py  # 节点选择
│               └── common.py            # 通用工具
├── api/
│   ├── guidelines.py                    # Guideline API
│   └── journeys.py                      # Journey API
```

## 图表

### 架构层次
```
API Layer (FastAPI)
    ↓
Application Layer (Modules)
    ↓
Core Business Logic
    ↓
Storage Layer (Stores)
    ↓
Persistence (DB/Vector DB)
```

### 协作关系
```
Journey ──conditions──→ Guideline
   │                        │
   │                        │
   ├──投影──→ Guideline List │
   │                        │
   └──标签──→ Journey Tag ──→┘
```

## 贡献者注意事项

1. **不可变性**: Guideline 和 Journey 核心对象是不可变的 (`frozen=True`)
2. **元数据**: 使用元数据存储扩展信息
3. **标签**: 使用特殊标签管理 Journey-Guideline 关联
4. **投影**: Journey 修改后需要重新投影
5. **并发**: 使用读写锁保护并发访问

## 版本信息

- **分析日期**: 2025-11-05
- **代码版本**: 基于当前 main 分支
- **存储版本**: 
  - GuidelineDocumentStore: v0.4.0
  - JourneyVectorStore: v0.3.0

## 联系方式

如有问题或建议，请参考项目的 CONTRIBUTING.md 文件。
