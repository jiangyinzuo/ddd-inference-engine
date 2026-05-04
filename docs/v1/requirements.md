# V1 Requirements

重点工作：全面考虑架构设计，规避当今主流大模型推理引擎的历史包袱与设计缺陷。

## 当今大模型推理引擎的历史包袱和设计缺陷

今天的大模型推理引擎，是从
“单模型、单请求、单机 GPU token generator”一路补丁式演化到
“多租户、多模型、多模态、长上下文、PD 分离、KV Cache复用、投机解码……”的系统，
因此带有不少历史包袱与设计缺陷。

### 跨请求KV Cache复用

早期推理引擎以“请求”为中心：一个 request 进来，prefill，decode，返回 tokens。

### 前端Prompt编排地位下降

早期的SGLang论文将自己的前端Prompt编排DSL作为一大卖点。它认为当时的
LangChain、LMQL、Guidance、DSPy 这类工具主要关注前端编排，但容易牺牲 runtime
performance；而 vLLM、TGI、TensorRT-LLM 这类后端引擎只关注单次 generation
call / OpenAI Completion API 风格，缺少对应用结构的感知。
于是，当时的 SGLang 提出frontend language + backend runtime 需要 co-design。

然而，今天的SGLang已将工作中心转向后端引擎。 OpenAI-compatible API
成了事实标准，应用层也不愿意将自己的业务逻辑迁移到SGLang前端语言。
