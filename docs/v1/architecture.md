# V1 Architecture

今天的大模型推理引擎，是从
“单模型、单请求、单机 GPU token generator”一路补丁式演化到
“多租户、多模型、多模态、长上下文、PD 分离、KV Cache复用、投机解码……”的系统，
因此带有不少历史包袱与设计缺陷。


## 分离式推理

在逻辑层面做好Prefill/Decode、Attention/FFN分离。实际部署时可以考虑同进程或多进程部署。

### P/D分离

按推理阶段拆分

#### 多模态推理：EPD分离

vision encoder、audio encoder

Prefill-Only inference: https://github.com/sgl-project/sglang/issues/15344

### A/F分离

按层内算子拆分

分离原因：

1. MoE架构天然可以将F看成独立的专家service

普通 Dense Transformer 里，FFN 是固定的一组矩阵；MoE 里，FFN 被替换成很多 experts，每个 token 只激活少数几个 expert。这样 `F` 侧天然适合被看成一个独立的 expert service / expert pool。

2. Attention和FFN的瓶颈不同

Attention
缺点：每一层之间都要跨层传输，通信开销可能大于收益，A -> F -> A

## 模型并行

| 并行方式                     |                   切分维度 | 主要解决什么问题                       |
| ------------------------ | ---------------------: | ------------------------------ |
| Data Parallel, DP        |               请求 batch | 提高吞吐，多副本服务不同请求                 |
| Tensor Parallel, TP      | hidden / head / FFN 维度 | 单层矩阵太大，单卡算不动                   |
| Pipeline Parallel, PP    |               layer 维度 | 模型层数太多，单卡放不下                   |
| Expert Parallel, EP      |             MoE expert | MoE 专家分布式                      |
| **Context Parallel, CP** |  **sequence/token 维度** | **长上下文 KV Cache / prefill 太大** |

### Tensor Parallelism
### Pipeline Parallelism
### Data Parallelism
### Expert Parallelism
### Distributed Weight Data Parallelism
### Context Parallelism

https://github.com/sgl-project/sglang/issues/21788

#### Prefill Context Parallelism
#### Decode Context Parallelism

## KV Cache Centric 设计

### KV Cache 复用

早期推理引擎以“请求”为中心：一个 request 进来，prefill，decode，返回 tokens。KV Cache只是Request的一个内部成员。

```text
Request {
  input_tokens
  output_tokens
  kv_blocks
  sampling_state
}
```

基于前缀树，早期的SGLang和vLLM能做到单个实例内跨请求KV Cache复用，无法做到
跨GPU/跨实例/跨节点KV Cache复用。

安全和一致性问题：model_id，tokenizer……是否完全一致？租户之间是否允许共享？

### KV Cache 分层存储（Off-Loading）

L0: GPU HBM
~~同节点其他 GPU HBM~~
L1: CPU DRAM
L2: 本地 SSD
L3: 远端 DRAM / KV server
L4: 远端 SSD / object storage

- prefetch
- invalidation机制：后续是否还有复用价值
- Cost Model: 搬运时间是否小于重新计算的时间
- KV Cache Transfer（网络通信）

https://github.com/sgl-project/sglang/issues/21846

### KV Cache Locality-Aware Scheduling

### KV Cache 生命周期管理

### KV Cache Layout

### KV Cache 压缩/量化

### KV Cache 和PD分离结合

- Prefill Node: 生成、发送KV Cache
- Decode Node: 接收KV Cache
- Scheduler: 将KV Cache位置作为选择目标Worker的一大参考因素

### KV Cache和Speculate Decoding的耦合

draft token被拒绝时，对应KV Cache不能加入到KV Cache存储中。

### KV Cache和模型并行的耦合

### KV Cache 部分复用

不仅局限于前缀复用

### KV Cache 跨形态转换

### 内存分配器

## 调度

- Continuous Batching: 面对不确定性的动态长度的推理序列，及时去掉推理结束的请求。
- Chunked Prefill: 防止过长的前缀请求阻塞其它请求。

## Model Support

### MoE

专家并行、Expert Parallel Load Balancing

### Diffusion Model

架构会和LLM推理有很大区别，不要将LLM推理和Diffusion推理做成一个系统。

## 长上下文推理


## 多模态

## Quantization

## Multi Token Prediction

模型原生 MTP Head

## Speculate Decoding

## 算子和硬件支持

- 先保证算子可用，不深入算子优化
- 优先支持CPU，但在接口设计层面预留GPU、NPU支持

算子碎片化？

### Runtime Compiler

## 前端

- Router / Gateway / Load Balancer / API Server
- Tokenizer / Detokenizer
- Structured output / grammar parser / tool call parser

### 前端Prompt编排地位下降

早期的SGLang论文将自己的前端Prompt编排DSL作为一大卖点。它认为当时的
LangChain、LMQL、Guidance、DSPy 这类工具主要关注前端编排，但容易牺牲 runtime
performance；而 vLLM、TGI、TensorRT-LLM 这类后端引擎只关注单次 generation
call / OpenAI Completion API 风格，缺少对应用结构的感知。
于是，当时的 SGLang 提出frontend language + backend runtime 需要 co-design。

然而，今天的SGLang已将工作中心转向后端引擎。 OpenAI-compatible API
成了事实标准，应用层也不愿意将自己的业务逻辑迁移到SGLang前端语言。

## Tokenizer / Detokenizer

https://huggingface.co/docs/tokenizers/python/latest/index.html

## LoRA

## 强化学习

## 编程语言

### Python的问题

Python虽然在AI大模型方面生态丰富，但也具备GIL、高内存开销、运行速度慢、冷启动慢影响弹性扩缩容等问题。

GIL: 多线程CPU并行受限，系统被迫走多进程/AsyncIO路线，导致架构复杂度上升。

Pickle内部通信跨语言不友好、安全性差、性能一般。


### 用Rust重写

适合Rust重写的模块

前端
- Router / Gateway / Load Balancer / API Server
- Tokenizer / Detokenizer
- Structured output / grammar parser / tool call parser

可能适合用Rust重写的模块：

- Scheduler
- KV Cache Manager

https://github.com/sgl-project/sglang/issues/23206

## Auto-Tuning
## 可观测性

## 模块划分

- API server（Rust）
- Router: 选择Prefill Node和Decode Node
- scheduler
- KV cache manager
- Model executor

