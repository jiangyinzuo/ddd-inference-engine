# V1 Architecture

## 编程语言

Rust, Python3

## 推理引擎架构

### 分离式推理

在逻辑层面做好Prefill/Decode、Attention/FFN分离。实际部署时可以考虑同进程或多进程部署。

#### P/D分离

按推理阶段拆分

#### A/F分离

按层内算子拆分

分离原因：

1. MoE架构天然可以将F看成独立的专家service

普通 Dense Transformer 里，FFN 是固定的一组矩阵；MoE 里，FFN 被替换成很多 experts，每个 token 只激活少数几个 expert。这样 `F` 侧天然适合被看成一个独立的 expert service / expert pool。

2. Attention和FFN的瓶颈不同

Attention
缺点：每一层之间都要跨层传输，通信开销可能大于收益，A -> F -> A

### 模块划分

- API server（Rust）
- Router: 选择Prefill Node和Decode Node
- scheduler
- KV cache manager
- Model executor

## 算子和硬件支持

- 先保证算子可用，不深入算子优化
- 优先支持CPU，但在接口设计层面预留GPU、NPU支持

