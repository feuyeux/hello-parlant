# Journey 和 Guideline 源代码分析概览

## 文档目的

本文档系列对 `src/parlant` 目录中 Journey 和 Guideline 相关的代码逻辑进行深入分析，包括：
- 核心数据模型和业务逻辑
- 类和方法之间的关系
- 加载和请求的完整流程
- 两者的协作机制

## 文档结构

1. **01-overview.md** - 概览和架构总览
2. **02-core-models.md** - 核心数据模型分析
3. **03-storage-layer.md** - 存储层实现
4. **04-application-layer.md** - 应用层模块
5. **05-api-layer.md** - API 层实现
6. **06-journey-guideline-projection.md** - Journey 到 Guideline 的投影机制
7. **07-engine-integration.md** - 引擎层集成
8. **08-complete-flow.md** - 完整请求流程
9. **09-collaboration-mechanism.md** - 协作机制总结

## 核心概念

### Guideline（指南）
- **定义**: 条件-动作规则，用于指导 AI Agent 的行为
- **结构**: `condition` (条件) + `action` (动作)
- **用途**: 定义 Agent 在特定情况下应该如何响应

### Journey（旅程）
- **定义**: 有向图结构，表示用户交互的多步骤流程
- **组成**: 
  - `JourneyNode` (节点): 表示旅程中的步骤
  - `JourneyEdge` (边): 表示步骤之间的转换条件
- **用途**: 引导用户完成复杂的多步骤任务

### 关键关系
- Journey 通过 `conditions` 字段关联多个 Guideline ID
- Journey 可以被"投影"为一组 Guideline，用于引擎处理
- Guideline 可以独立存在，也可以作为 Journey 的一部分

## 架构层次

```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI)             │
│  - journeys.py, guidelines.py           │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      Application Layer (Modules)        │
│  - app_modules/journeys.py              │
│  - app_modules/guidelines.py            │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         Core Business Logic             │
│  - journeys.py, guidelines.py           │
│  - journey_guideline_projection.py      │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         Storage Layer (Stores)          │
│  - JourneyVectorStore                   │
│  - GuidelineDocumentStore               │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│      Persistence (DB/Vector DB)         │
│  - DocumentDatabase                     │
│  - VectorDatabase                       │
└─────────────────────────────────────────┘
```

## 下一步

请继续阅读后续文档以了解详细的实现细节。
