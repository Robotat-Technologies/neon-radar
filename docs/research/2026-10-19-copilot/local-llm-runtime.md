# NeonRadar phase 4: the local language model runtime

Research date: Monday 19 October 2026.

Method. I cloned the official repositories read-only and read the source at fixed commits: ollama/ollama at tag v0.40.6, ollama/ollama-python at v0.6.3, ggml-org/llama.cpp at b11724 and its tag b11669, vllm-project/vllm v0.32.0, mozilla-ai/llamafile 0.10.6, mudler/LocalAI v4.11.0, meta-llama/llama-models, the BFCL code, website and result repositories, and neo4j/neo4j-graphrag-python main. Package metadata came from the PyPI JSON API. On CPython 3.14.6 with uv 0.11.32 I installed `ollama` 0.6.3 and `neo4j-graphrag[ollama]` 1.22.0, resolved dependency sets, and ran a smoke test of the Python client against a fake HTTP transport (no server, no model). Web pages (ollama.com library pages, Hugging Face model cards, Google and Meta licence pages, GitHub issues and discussions, the Docker Hub API, the BFCL leaderboard page, LM Studio terms) were read with the web fetch tool, which returns summaries and short quotes; important numbers were read twice where possible. Blocked or limited: from the shell, ollama.com, registry.ollama.ai, huggingface.co, gorilla.cs.berkeley.edu and api.github.com were refused by the egress proxy, so no model could be downloaded or run here and nothing in this note was measured with a real model; GitHub issue search is closed to the fetch tool, so only issues found through web search were read; the BFCL leaderboard table loads dynamically, so its scores come from the data file in the website's source branch, which is byte-identical to the BFCL-Result snapshot of 2025-12-16. Tags [L1] to [L27] point to the Sources list. "Inference" marks my reasoning, "Proposal" marks a design suggestion, and UNVERIFIED marks what I could not confirm.

## 0. Answers for the spec writer

1. **Ollama.** The latest release is v0.40.6, tagged 2026-10-16 and marked "Latest"; a v0.40.7 pre-release exists (tag v0.40.7-rc0, 2026-10-17) [L3]. Licence: MIT [L1]. In v0.40.6, "All GGUF models are served via the upstream llama-server subprocess" (llama.cpp b11669) [L1]. Proposal: use the native `POST /api/chat` with `format` set to a JSON schema (turned into a llama.cpp grammar), `stream: false`, `think: false`, `keep_alive`, and `options` with temperature 0, top_k 1, top_p 1, a seed, `num_ctx` and `num_predict` [L1][L2]. Defaults when unset: temperature 0.8, top_k 40, top_p 0.9, seed -1 (random), num_predict -1 (no limit), keep_alive 5m, num_ctx 4096 below 24 GiB of VRAM [L1][L2]. Tool calling exists but cannot be forced: there is no `tool_choice` [L1][L2]. The OpenAI-compatible `/v1/chat/completions` accepts `response_format` and `seed` but cannot set the context size [L2]. The Python client `ollama` 0.6.3 (2026-09-29) is MIT, needs Python `>=3.8`, depends on `httpx>=0.27` and `pydantic>=2.9`, has `Client` and `AsyncClient`, and has no timeout by default [L5]; it installs and works on CPython 3.14.6 [L6]. The Docker image is `ollama/ollama:0.40.6` (Ubuntu 24.04 base, `OLLAMA_HOST=0.0.0.0:11434` inside the container) [L1][L4]. **Phoning home:** I found no analytics library, but the server sends signed background requests to ollama.com at start and about every 4 hours (cloud model catalogue, model recommendations) unless `OLLAMA_NO_CLOUD=1` or `"disable_ollama_cloud": true` in `~/.ollama/server.json` [L1][L2]. The macOS and Windows desktop app checks for updates at start and every hour and calls ollama.com `/api/me` at start; the cloud switch does not stop either [L1]. Offline recipe (Proposal): run `ollama serve` or the Docker image, not the desktop app, with `OLLAMA_NO_CLOUD=1` and `OLLAMA_HOST=127.0.0.1:11434`, and check that `GET /api/status` returns `"disabled": true` [L1][L2].
2. **Determinism.** Not guaranteed. At temperature 0, llama.cpp takes the highest logit (greedy), so the seed has no effect [L7]. But Ollama always sends `"cache_prompt": true` [L1], and llama.cpp warns that this "can cause nondeterministic results" because logits differ between batch sizes [L7]. Ollama issue #5321 lists three causes of differing outputs: operating system, CPU versus GPU, and KV cache reuse [L9]; a pull request to make caching configurable was closed as stale on 2026-04-23 [L9]. Inference: expect repeatable output on one machine, one Ollama version and one model digest most of the time; do not expect it across CPU, Apple Metal and CUDA, or across Ollama versions [L9][L12]. The spec must not require byte-identical model output.
3. **Models (8B or fewer, official Ollama library).** Qwen3 0.6B to 8B, Qwen3.5 0.8B, 2B and 4B, Llama 3.1 8B, Llama 3.2 1B and 3B, Gemma 3 270M to 4B, Gemma 4 E2B and E4B, Phi-4-mini 3.8B, Granite 4.1 and 4.2 (3B, 8B), Ministral 3 (3B, 8B) and Mistral 7B v0.3 [L13]. SmolLM3 appears only under user namespaces [L13]. Apache-2.0: Qwen3, Qwen3.5, Granite 4.x, Ministral 3, Gemma 4, Mistral 7B. MIT: Phi-4-mini. Restricted: Llama 3.1 and 3.2 (community licence plus acceptable use policy; the model cards put languages other than the 8 supported ones, including Arabic and Russian, out of scope) and Gemma 3 (Gemma Terms of Use plus a Prohibited Use Policy that bans "Making automated decisions in domains that affect material or individual rights or well-being", naming finance) [L14][L16][L17]. Best published single-turn function-calling scores in this size class: Qwen3-8B and Qwen3-4B-Instruct-2507 (BFCL V4 non-live AST 87.58 and 87.88, live 80.53 and 76.39, irrelevance detection 79.07 and 84.93) [L18]. Full table in section 3.
4. **Hardware.** Weights at Q4_K_M: 2.5 GB for Qwen3 4B Instruct, 5.2 GB for Qwen3 8B, 1.4 GB for Qwen3 1.7B [L13]. KV cache at `num_ctx` 4096 in f16: 576 MiB for Qwen3 4B or 8B, 448 MiB for Qwen3 1.7B (arithmetic from the model configs) [L14]. Neo4j: 2 GB heap plus 2 GB page cache plus native memory that "will grow dynamically as needed" [L20]; Docker Desktop's VM "Defaults to 50% of your host's memory" [L21]. Inference: on a 16 GB CPU-only laptop a 4B model fits next to Neo4j and an 8B model is tight; on 8 GB, ship template-only mode and offer Qwen3 1.7B as an opt-in. Apple Silicon generation speed for Llama 2 7B Q4_0 in llama.cpp runs from 14.15 tokens/s (M1, 8 GPU cores) to 50.74 tokens/s (M4 Pro, 20 cores) in the rows quoted in 4.3 [L19]. On CPU, generation is bounded by memory bandwidth and prompt processing is only tens of tokens per second for a 7B model [L7] (Inference for laptops). Keep the system prompt short, warm the model up once, and keep it loaded.
5. **Pinning.** Tags move: today the bare `qwen3:4b` tag is the Thinking-2507 build, not `qwen3:4b-q4_K_M`, and many Qwen3.5 tags were re-pushed in the last two weeks [L13]. Ollama cannot pull by digest: the documented `@digest` form is not parsed [L1] (Inference). Record the tag, the manifest digest (`/api/tags` `digest`; the `ollama list` ID is its first 12 hex characters), the weights blob digest (`ollama show --modelfile`, the `FROM .../sha256-...` line), runner and format (`/api/show` `manifests`), the Ollama version and its bundled llama.cpp build, and every option [L1]. Freeze a local copy with `ollama cp` (Inference). On Apple Silicon a tag that is a manifest list resolves to an MLX build, so use quantisation-specific GGUF tags for cross-platform numbers [L1][L13].
6. **Alternatives.** llama.cpp `llama-server` (MIT; `json_schema` and GBNF grammars; `--offline`; binds 127.0.0.1 by default) fits and is the engine Ollama runs [L7]. llamafile 0.10.6 (Apache-2.0) fits but trails upstream llama.cpp [L24]. LocalAI v4.11.0 (MIT) fits by licence, but loads model galleries by default and is large [L25]. vLLM v0.32.0 (Apache-2.0) is a GPU server and "collects anonymous usage data by default" [L12]. LM Studio's desktop app is proprietary ("exclusive property of Company"; licensed for "personal and / or internal business purposes") and cannot be a dependency [L26].
7. **neo4j-graphrag.** Latest 1.22.0 (2026-10-01), Python `>=3.10.0,<3.15`, installs on 3.14 [L22]. Its `[ollama]` extra requires `ollama<0.5.0,>=0.4.4`, so it cannot be installed together with `ollama` 0.6.3 today; uv reports "your requirements are unsatisfiable" [L22]. Main changed the pin to `>=0.6.3,<0.7.0` on 2026-10-15, not yet released [L22]. `OllamaLLM` raises "OllamaLLM does not currently support structured output" when given `response_format` [L22]. With the extra it brings 23 packages and 189 MB (scipy, numpy, pypdf), against 12 packages and 13 MB for `ollama` alone [L22][L6]. Text2CypherRetriever runs `EXPLAIN` and refuses any query whose type is not "r" [L22]. Recommendation: do not depend on it; call `/api/chat` directly.
8. **For the spec.** Default model `qwen3:4b-instruct-2507-q4_K_M` (Apache-2.0, 4.02B, 2.5 GB, no thinking mode) [L13][L14]. Alternatives: `qwen3:8b-q4_K_M` (Apache-2.0, 5.2 GB; send `think: false`) and `phi4-mini:3.8b-q4_K_M` (MIT, 2.5 GB, Arabic and Russian listed, weaker published function-calling scores) [L13][L14][L18]. For 8 GB machines: `qwen3:1.7b-q4_K_M` or no model. Exact server settings and request body are in 8.2. Test without a model by injecting `httpx.MockTransport` into the client (verified with `ollama` 0.6.3 on Python 3.14) and by replaying recorded responses [L6]. Before publishing, a human must measure accuracy per script (Latin, Arabic, Cyrillic), agreement over repeated runs, cold and warm latency, peak memory next to Neo4j and the absence of outbound connections, and must record the full environment (8.4).

## 1. Ollama: release, API, client, image, network (question 1)

### 1.1 Release, licence and engine

- Latest release: v0.40.6, commit 2476d5e, tagged 2026-10-16; the GitHub releases page marks it "Latest" and marks a v0.40.7 entry "Pre-release"; the newest tag is v0.40.7-rc0 (2026-10-17) [L3].
- Phase 1 recorded v0.40.5 (commit d919272, 2026-10-15) [L27][L3]. Seven releases, v0.40.0 to v0.40.6, were tagged between 2026-10-06 and 2026-10-16 [L3].
- Licence: "MIT License", "Copyright (c) Ollama" [L1].
- Engine: "All GGUF models are served via the upstream llama-server subprocess." (`llm/server.go`) [L1]. The bundled llama.cpp build (`LLAMA_CPP_VERSION`) is b11669 in v0.40.5 and v0.40.6, b11351 in v0.40.0 and b11081 in v0.35.0 (2026-09-28) [L1]. In llama.cpp, b11669 is the commit tagged v0.7.0 on 2026-10-15 [L7].
- Ollama starts llama-server with `--host 127.0.0.1`, `--no-webui`, `--offline` and `-c` set to `num_ctx` times the number of parallel slots [L1]. llama.cpp describes `--offline` as "Offline mode: forces use of cache, prevents network access" [L7].
- Structured output path: "a JSON schema is passed to llama-server via its json_schema field and the "json" format as a builtin grammar via the grammar field" (`llm/llama_server.go`) [L1].
- Runner choice: a model tag can be a manifest list with several builds. On macOS on Apple Silicon Ollama prefers the runners in the order mlx, llamacpp, ggml; elsewhere llamacpp, ggml, mlx (`manifest.runnerPreferences`) [L1].

### 1.2 Endpoints

| Endpoint | What it does | Use in NeonRadar |
|---|---|---|
| `POST /api/chat` | chat completion with `format`, `options`, `think`, `tools`, `keep_alive`, `logprobs`, `truncate`, `runner` [L1] | the intent call |
| `POST /api/generate` | prompt completion; `raw: true` skips the chat template [L2] | not needed |
| `GET /api/tags` | local models with `digest`, `size`, `details` (format, family, parameter size, quantisation) [L1] | presence and digest check |
| `POST /api/show` | parameters, template, licence, `model_info`, `capabilities`, `thinking`, and `manifests` (digest, runner, format, selected) [L1] | record what ran |
| `GET /api/ps` | loaded models with `digest`, `context_length`, `runner`, `size_vram` [L1] | record runner and context |
| `GET /api/version` | server version [L1] | record |
| `GET /api/status` | `{"cloud": {"disabled": ..., "source": ...}}`, source is "none", "env", "config" or "both" [L1] | offline check |
| `POST /api/pull` | pull by `model`, optional `runner` [L1] | setup only, never automatic |
| `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/models`, `/v1/responses` | OpenAI-compatible [L1][L2] | not needed |
| `/v1/messages` | Anthropic-compatible [L1] | not needed |
| `/v1/systemone` | "decision models": typed yes/no, choice and score questions with probabilities [L2] | not in v1 (see 1.6) |

The repository notes that "Ollama's API docs are moving to https://docs.ollama.com/api" [L2].

### 1.3 Parameters for schema-constrained, repeatable output

| Field | Meaning and behaviour in v0.40.6 | Default |
|---|---|---|
| `format` | "Format can be `json` or a JSON schema" [L2]. A schema goes to llama-server `json_schema`; with thinking on, Ollama converts it to a grammar that applies after the thinking block [L1]. The docs add: "It is ideal to also pass the JSON schema as a string in the prompt to ground the model's response." [L2] | none |
| `options.temperature` | 0 makes llama.cpp use its greedy sampler (see 2.1) [L7] | 0.8 [L1] |
| `options.seed` | "For reproducible outputs, set `seed` to a number" [L2]; llama-server: "Default: `-1`, which is a random seed" [L7] | -1 [L1] |
| `options.top_k`, `top_p`, `min_p` | passed to llama-server [L1] | 40, 0.9, 0 [L1] |
| `options.repeat_penalty`, `presence_penalty`, `frequency_penalty` | passed to llama-server [L1] | 1.0, 0, 0 [L1] |
| `options.num_ctx` | context length; changing it between requests reloads the model (`needsReload` compares runner options) [L1] | `OLLAMA_CONTEXT_LENGTH`, else 4096 below 23 GiB of VRAM, 32768 from 23 GiB, 262144 from 47 GiB [L1]; docs: "< 24 GiB VRAM: 4k context" [L2] |
| `options.num_predict` | maximum tokens to generate | -1, no limit [L1] |
| `options.num_batch`, `num_thread`, `num_gpu` | load-time runner options; a change reloads the model [L1] | 512, 0 (auto), -1 (auto) [L1] |
| `keep_alive` | "a duration string (such as "10m" or "24h")", "a number in seconds", "any negative number which will keep the model loaded in memory", "'0' which will unload the model immediately after generating a response" [L2] | 5m [L1][L2] |
| `think` | "Can be a boolean or a thinking level (`"low"`, `"medium"`, `"high"`, or `"max"`)" [L2]. A thinking-capable model without thinking metadata thinks when `think` is unset; a model without thinking capability rejects `think: true` with "does not support thinking" and accepts `false` [L1] | model default |
| `stream` | "true by default" (ChatRequest comment) [L1] | true |
| `tools` | tool calling; there is no `tool_choice` field in the native request type [L1] | none |
| `logprobs`, `top_logprobs` | token log probabilities; top_logprobs "Valid values are 0-20" [L1] | off |
| `truncate` | when true, "truncates the chat history messages if the rendered prompt exceeds the context length limit"; system messages are kept [L1] | true [L1] |
| `runner` | "selects a runner variant from a manifest list" [L1] | platform preference |

Two traps found in the source:

- Unknown option names are dropped with only a server log line, "invalid option provided" (`Options.FromMap`) [L1]. Proposal: validate option names in NeonRadar before sending.
- A model's own parameters layer applies unless the request overrides it; the Qwen3 tags ship a params layer that sets `"repeat_penalty": 1` and stop tokens [L13]. Proposal: send every sampling option explicitly and record `/api/show` `parameters`.

### 1.4 Tool calling, OpenAI compatibility and thinking

- Tool calling: "Ollama supports tool calling (also known as function calling) which allows a model to invoke tools and incorporate their results into its replies." [L2] The native API cannot force a call (no `tool_choice` [L1]); the OpenAI-compatible list leaves "`tool_choice`", "`logit_bias`", "`user`" and "`n`" unticked [L2]. Inference: a `format` schema constrains the whole reply, while a tool call is optional for the model, so `format` is the better tool for intent extraction.
- OpenAI compatibility (`/v1/chat/completions`): ticked fields include `response_format`, `seed`, `temperature`, `top_p`, `max_tokens`, `tools` and `reasoning_effort` [L2]. "The OpenAI API does not have a way of setting the context size for a model." The workaround is a Modelfile with `PARAMETER num_ctx` [L2]. There is no `top_k` field in that list [L2].
- "Ollama's cloud currently does not support structured outputs." [L2] (Local models do.)
- Thinking: `/api/show` returns a `thinking` object with `values` and `default`; "`values: [false]` means the model does not support thinking" [L2]. For the original Qwen3 template (digest prefix ae370d884f10, which the library shows for `qwen3:8b` and `qwen3:1.7b`) the source sets thinking values false and true with default true [L1][L13]. So `qwen3:8b` thinks unless the request says `think: false` (Inference). Qwen3-4B-Instruct-2507 "supports only non-thinking mode" [L14].

### 1.5 Python client `ollama`

- Version 0.6.3, uploaded to PyPI 2026-09-29; tag commit 8785556 (2026-09-28) "types/client: relax think type to support model-defined thinking levels" [L5].
- Licence MIT; `requires-python = '>=3.8'`; dependencies `httpx>=0.27` and `pydantic>=2.9`; no trove classifiers [L5].
- `Client` wraps `httpx.Client` and `AsyncClient` wraps `httpx.AsyncClient`. Extra keyword arguments go to httpx. Defaults: "`follow_redirects`: True" and "`timeout`: None" [L5].
- When no host is given it reads `OLLAMA_HOST`, else uses `http://127.0.0.1:11434`. If `OLLAMA_API_KEY` is set and no authorization header is given, it sends `Bearer <key>` [L5]. Passing `Authorization: None` does not stop this, because `None` headers are dropped before the check [L5] (Inference from the code).
- Errors: HTTP status errors become `ResponseError`, connection failures become the built-in `ConnectionError`, and timeouts are not caught [L5]. Checked here with fake transports: a 404 raised `ResponseError` with status 404, a read timeout raised `httpx.ReadTimeout`, a refused connection raised `ConnectionError` [L6].
- It wraps chat, generate, embed, embeddings, list (`/api/tags`), show, ps, pull, push, create, copy and delete. It does not wrap `/api/version` or `/api/status`, and `chat()` has no `runner` or `truncate` argument [L5].
- Python 3.14: the CI runs `uvx hatch test -acp`, so the Python versions come from Hatch's default matrix and are not listed in the repository [L5]. Measured here: `ollama` 0.6.3 installed on CPython 3.14.6 with 12 packages in total (13 MB of site-packages: httpx 0.28.1, pydantic 2.14.1 and their dependencies); synchronous and asynchronous `chat()` against `httpx.MockTransport` returned the recorded reply; the request body held `format` (equal to the schema), `options` (temperature 0 kept), `keep_alive`, `think` and `stream`; the default client timeout printed as `Timeout(timeout=None)` [L6].

### 1.6 Decision models

Ollama documents "System One" decision models, which need "v0.35.0 or later": "Use System One to classify text, answer yes/no questions, or score text against a rubric." [L2] A `choice` question takes named options and returns each option's probability [L2]. The library lists small ones: tev1 (0.8B and 4B, from Together AI, "Choice and score questions take 2 to 26 options", "Tev1 was trained on 2 to 24, so stay in that range"; only the dataset builders and training scripts are stated as MIT; non-English use untested) and nimble (9B, Apache 2.0, 9.3 GB to 9.5 GB) [L13]. Inference: this could later route questions to template ids with calibrated probabilities, but it does not fill slots, has a 26-option limit, and the small models have no stated weights licence or non-English testing. Not for v1.

### 1.7 Docker image

- `ollama/ollama:0.40.6` was pushed 2026-10-17; manifest-list digest `sha256:265409e1d931028a8f7d5a32bcbafddd7bffbc6cc629d77efe9560adf692a5e7`; the linux/amd64 image is 3,785,734,447 bytes; `0.40.6-rocm` is 1,450,946,100 bytes [L4].
- Final Dockerfile stage: `FROM ubuntu:24.04`, `ENV OLLAMA_HOST=0.0.0.0:11434`, `EXPOSE 11434`, `ENTRYPOINT ["/bin/ollama"]`, `CMD ["serve"]` [L1]. Proposal: publish the port as `127.0.0.1:11434:11434`, never as `11434:11434`.
- CPU-only start: `docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama` [L2].
- "GPU acceleration is not available for Docker Desktop in macOS due to the lack of GPU passthrough and emulation." [L2] On a Mac, run Ollama natively to use Metal.
- Outside Apple Silicon, integrated GPUs are dropped unless allowed by default (CUDA, some ROCm targets) or `OLLAMA_IGPU_ENABLE=1`; the log line is "dropping integrated GPU; to enable, set OLLAMA_IGPU_ENABLE=1" [L1]. Inference: a typical Intel or AMD laptop runs Ollama on the CPU by default.

### 1.8 Outbound network requests (read in the source)

I searched the Go and TypeScript sources for analytics libraries and found none [L1]. These are the requests that leave the machine:

| Component | Request | When | Switched off by `OLLAMA_NO_CLOUD` |
|---|---|---|---|
| Server (all platforms, Docker) | `GET https://ollama.com/api/tags` and `POST /api/show` for each cloud model, signed | once at start (`modelShowCache.runStartup`) | yes [L1] |
| Server | `GET https://ollama.com/api/experimental/model-recommendations`, signed | at start, then every 4 hours with jitter, plus refresh on reads | yes [L1] |
| Server | registry pulls and pushes | only on `pull`/`push` | no (user action) [L1] |
| Server | cloud models, web search and fetch, balance, usage (proxied to ollama.com) | only when such a model or endpoint is used | yes: refused with HTTP 403 when cloud is disabled [L1] |
| Server | sign-in, `POST /api/me` (whoami), sign-out | only when the user calls them | no check found [L1] |
| Desktop app (macOS, Windows only) | `GET https://ollama.com/api/update?os=...&arch=...&version=...&ts=...&nonce=...`, signed; on macOS also the device `id` if one is stored | 3 s after start, then every hour; "Always check for updates" | no [L1] |
| Desktop app | download of the new release | when an update exists and `AutoUpdateEnabled` is on | no [L1] |
| Desktop app | `POST https://ollama.com/api/me`, signed | at start | no [L1] |

Details:

- "Signed" means an `Authorization` header built from the installation's key pair in `~/.ollama/id_ed25519`; the value is `<pubkey>:<signature>`, so it carries a stable per-installation public key [L1]. `ollama serve` creates the key pair at start (`initializeKeypair`) [L1].
- The app's update setting only controls the download: "Update is available - check if auto-update is enabled for downloading" [L1]. The FAQ says "Ollama on macOS and Windows will automatically download updates." [L2]
- The app's settings table has a `survey` column, default true, described as "if the user allows anonymous inference information to be shared with Ollama"; I found no code in v0.40.6 that reads it to send anything [L1].
- The desktop app is built only for Windows and macOS (`//go:build windows || darwin`); Linux has the server only [L1].
- The FAQ: "Ollama runs locally. We don't see your prompts or data when you run locally." [L2]

### 1.9 Running fully offline after a pull

FAQ: "Ollama can run in local only mode by disabling Ollama's cloud features." Set `"disable_ollama_cloud": true` in `~/.ollama/server.json` or `OLLAMA_NO_CLOUD=1`, then restart; "Once disabled, Ollama's logs will show `Ollama cloud disabled: true`." [L2] The desktop app's settings toggle writes the same file [L1].

Variables that exist in v0.40.6 (`envconfig/config.go`) [L1]:

| Variable | Effect | Default |
|---|---|---|
| `OLLAMA_HOST` | bind address of the server | 127.0.0.1:11434 |
| `OLLAMA_NO_CLOUD` | "Disable Ollama cloud features (remote inference and web search)"; also skips the background calls in 1.8 | off |
| `OLLAMA_MODELS` | models directory | `$HOME/.ollama/models`; Linux installer: `/usr/share/ollama/.ollama/models` [L2] |
| `OLLAMA_NOHISTORY` | "Do not preserve readline history" (interactive CLI only) | off |
| `OLLAMA_NOPRUNE` | "Do not prune model blobs on startup" | off |
| `OLLAMA_KEEP_ALIVE` | how long models stay loaded | 5m |
| `OLLAMA_CONTEXT_LENGTH` | default context length | VRAM-based (4096 on CPU-only machines) |
| `OLLAMA_NUM_PARALLEL` | parallel requests per model | 1 |
| `OLLAMA_MAX_LOADED_MODELS` | maximum loaded models | 0 in the code; the FAQ: "3 \* the number of GPUs or 3 for CPU inference" [L2] |
| `OLLAMA_MAX_QUEUE` | queued requests before 503 | 512 |
| `OLLAMA_LOAD_TIMEOUT` | stall timeout for model loads | 5m |
| `OLLAMA_FLASH_ATTENTION` | force flash attention on or off | automatic when the GPU supports it |
| `OLLAMA_KV_CACHE_TYPE` | KV cache quantisation | f16 |
| `OLLAMA_ORIGINS` | extra allowed CORS origins | localhost, 127.0.0.1, 0.0.0.0, app, file, tauri, vscode schemes |
| `OLLAMA_REMOTES` | "Allowed hosts for remote models" | ollama.com |
| `OLLAMA_DEBUG` | log level | info |
| `OLLAMA_DEBUG_LOG_REQUESTS` | "Log inference request bodies and replay curl commands to a temp directory" | off |
| `OLLAMA_VULKAN`, `OLLAMA_IGPU_ENABLE` | Vulkan GPUs, integrated GPUs | Vulkan on, iGPUs off (see 1.7) |
| `OLLAMA_AUTH`, `OLLAMA_SCHED_SPREAD`, `OLLAMA_GO_TEMPLATE`, `OLLAMA_GPU_OVERHEAD`, `OLLAMA_LLM_LIBRARY`, `OLLAMA_MAX_TRANSFER_STREAMS`, `OLLAMA_CREATE_REMOTE`, `OLLAMA_EDITOR` | other settings | see source |
| `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` | proxy for pulls and cloud | none |

The llama-server child process inherits Ollama's environment (`cmd.Env = os.Environ()`) [L1], so llama.cpp `LLAMA_ARG_*` variables reach it; llama.cpp states that a command-line argument "will take precedence over env var" [L7].

Offline recipe (Proposal):

1. While online, pull the pinned tag once (`ollama pull qwen3:4b-instruct-2507-q4_K_M`); the pull checks every blob ("verifying sha256 digest") [L1].
2. Start the server with `OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 OLLAMA_CONTEXT_LENGTH=4096 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 ollama serve`, or run the Docker image with the same variables and a loopback port mapping.
3. On macOS and Windows, run `ollama serve` instead of the desktop app, or block the app at the firewall, because the update check and `/api/me` call ignore the cloud switch [L1].
4. NeonRadar checks `GET /api/status` at start and warns (refuses in benchmark mode) unless `cloud.disabled` is true [L1].
5. To move models to an offline machine, copy the whole models directory (manifests and blobs) and point `OLLAMA_MODELS` at it (Inference; unverified here). Never call `/api/pull` automatically.
6. Leave `OLLAMA_DEBUG_LOG_REQUESTS` off: questions contain names, which are personal data.

## 2. Determinism (question 2)

### 2.1 What the code does at temperature 0

- llama.cpp picks the greedy sampler when temperature is 0: `const bool greedy = params.n_probs == 0 && ... params.temp == 0.0f ...` (`common/sampling.cpp`); the temperature sampler at or below 0 will "find the token with the highest logit and set the rest to -inf" (`src/llama-sampler.cpp`) [L7]. Inference: at temperature 0 the seed has no effect, and output depends only on the logits.
- llama.cpp's own completion guide says "a temperature of 0 will always pick the most likely next token, leading to identical outputs in each run" [L7]. That holds only while the logits are identical.
- Ollama hard-codes prompt caching: `CachePrompt: true` in the completion path and `"cache_prompt": true` in the chat path, with no condition on the seed [L1].
- llama-server documents the risk: "Because (depending on the backend) the logits are **not** guaranteed to be bit-for-bit identical for different batch sizes (prompt processing vs. token generation) enabling this option can cause nondeterministic results." [L7] Inference: the cached prefix depends on the previous request in the slot, so the same question can see a different batch split depending on what was asked before.
- llama-server also keeps a host-memory prompt cache, `--cache-ram`, "default: 8192, 0 for decision models"; Ollama passes `--cache-ram 0` only for decision models [L7][L1].
- Flash attention is "auto" when the GPU supports it and "off" otherwise, unless `OLLAMA_FLASH_ATTENTION` is set [L1]. So numerics follow the hardware (Inference).
- Batching: "the primary reason nearly all LLM inference endpoints are nondeterministic is that the load" changes the batch size, "causing our request's output to depend on the batch size of our forward pass" [L11]. Ollama's default is one parallel request per model (`OLLAMA_NUM_PARALLEL` 1) [L1]; Inference: this avoids batching unrelated requests together.

### 2.2 Reports and project statements

- Issue #5321, "Generated outputs inconsistent across different OS despite seed, temperature and num_ctx" (first reported on Ollama 0.1.46): "Even though the output is **deterministic** and **reproducible** with a fixed `seed`, a `temperature` set to 0 and a fixed `num_ctx`, the generated output slightly differs across different OS." A commenter listed "three different issues": "1) Generating the output on different operating systems", "2) Generating the outputs on CPU vs GPU", "3) Generating the outputs using the KV cache" [L9].
- Pull request #5760, "Make llama.cpp's cache_prompt parameter configurable", was closed as stale on 2026-04-23. In that thread a user wrote that "the output of the 1st execution was different from the 2nd and following executions", and an Ollama contributor reported that "with Apple GPUs the results are consistent with and without prompt caching but Nvidia varies" [L9].
- Pull request #10064 proposed a "nocache" KV cache type "to ensure reproducibility". The maintainer reply: "caching is an internal implementation detail and we want to minimize configuration knobs that expose this to the user", and proposed that "when the user sets a seed, we automatically disable these two" [L10]. v0.40.6 does not do this: caching stays on whatever the seed [L1].
- Issue #12559, "Non-deterministic structured output with same seed" (Ollama 0.12.3, Linux, Nvidia GPU): "If I run this script twice, I expect to have the same list of numbers, but instead I get two very different ones." The page does not show whether temperature was 0 [L8].
- vLLM, for comparison: "Even with the above settings, vLLM only provides reproducibility when it runs on the same hardware and the same vLLM version." [L12]
- Version churn: the bundled llama.cpp moved from b11081 (v0.35.0) to b11351 (v0.40.0) to b11669 (v0.40.5) in under three weeks [L1].

### 2.3 Answer

| Scope | Repeatable? |
|---|---|
| Same machine, same Ollama version, same model digest, temperature 0, fixed `num_ctx`, `num_batch` and threads, one parallel slot | Usually, not guaranteed: prompt caching can change logits, and the first request after a load can differ from later ones [L7][L9] |
| CPU versus Apple Metal versus CUDA, or different operating systems | No guarantee; differences reported [L9] |
| Different Ollama versions | No guarantee; the engine and llama.cpp change weekly [L1] (Inference) |

Proposal for the spec: (a) never assert byte-identical model output in CI; assert schema validity and the deterministic checks in 8.2; (b) send a warm-up request with the fixed system prompt at start, so that user questions always reuse the cached prefix; (c) keep `num_ctx`, `num_batch`, `OLLAMA_NUM_PARALLEL=1` and `OLLAMA_FLASH_ATTENTION` fixed and recorded; (d) publish agreement rates over repeated runs instead of claiming determinism.

## 3. Candidate models of 8B parameters or fewer (question 3)

### 3.1 Table

Sizes and context windows are as shown by the Ollama library for the default (Q4_K_M) build; "list" means the tag is a manifest list whose size range covers a GGUF and an MLX build [L13]. BFCL figures are single-turn sub-scores from the BFCL V4 result snapshot of 2025-12-16 unless marked otherwise: non-live AST accuracy / live accuracy / irrelevance detection, with the mode (FC = native function calling, Prompt = prompt format) [L18]. Self-reported numbers come from model cards and are not comparable with the leaderboard.

| Ollama tag | Params | Download | Context (Ollama) | Licence | Arabic / Russian | Thinking | Function calling |
|---|---|---|---|---|---|---|---|
| `qwen3:4b-instruct-2507-q4_K_M` (Qwen3-4B-Instruct-2507) | 4.02B [L13] | 2.5 GB | 256K | Apache-2.0 | yes / yes (Qwen3: 119 languages and dialects) [L15] | none [L14] | BFCL V4 FC 87.88 / 76.39 / 84.93 [L18]; card BFCL-v3 61.9 [L14] |
| `qwen3:8b` = `qwen3:8b-q4_K_M` (Qwen3-8B) | 8.19B [L13] | 5.2 GB | 40K | Apache-2.0 | yes / yes [L15] | hybrid, on by default; `think: false` [L1][L14] | BFCL V4 FC 87.58 / 80.53 / 79.07 [L18] |
| `qwen3:1.7b` = `qwen3:1.7b-q4_K_M` | 2.03B [L13] | 1.4 GB | 40K | Apache-2.0 | yes / yes [L15] | hybrid | BFCL V4 FC 82.92 / 74.61 / 76.54 [L18] |
| `qwen3.5:4b` (list) or `qwen3.5:4b-q4_K_M` | "4B" (card); "5B params" with the vision encoder [L14] | list 3.3 GB to 4.0 GB; q4_K_M 3.3 GB | 256K | Apache-2.0 [L14] | 201 languages and dialects [L14] | "operate in thinking mode by default" [L14] | card BFCL-V4 50.3 (overall V4 score, mode not stated), IFEval 89.8 [L14] |
| `qwen3.5:2b` (list) or `qwen3.5:2b-q4_K_M` | 2B (tag) | list 2.7 GB to 3.1 GB; q4_K_M 1.9 GB | 256K | Apache-2.0 for the family (the 2B card was not read) | 201 languages (family claim) | on by default (family claim) | none found |
| `llama3.1:8b` | 8B | 4.9 GB | 128K | Llama 3.1 Community License and Acceptable Use Policy [L16] | not supported: 8 languages; other languages out of scope [L16] | none | BFCL V4 Prompt 84.00 / 70.76 / 42.70 [L18] |
| `llama3.2:3b` | 3.21B [L16] | 2.0 GB | 128K | Llama 3.2 Community License and Acceptable Use Policy [L16] | not supported [L16] | none | BFCL V4 FC 82.67 / 58.33 / 52.06 [L18] |
| `gemma3:4b` | 4B | 3.4 GB | 128K | Gemma Terms of Use and Prohibited Use Policy [L17] | "over 140 languages" (list not checked) [L14] | none | BFCL V4 Prompt 61.12 / 60.84 / 53.94 [L18] |
| `gemma4:e2b`, `gemma4:e4b` (lists) | E2B "2.3B effective (5.1B with embeddings)", E4B "4.5B effective (8B with embeddings)" [L14] | e2b 4.6 GB to 7.5 GB; e4b 6.6 GB to 9.5 GB | 128K | Apache-2.0 [L14][L17] | "Out-of-the-box support for 35+ languages, pre-trained on 140+ languages" (list not checked) [L14] | yes, via the system prompt [L14] | no BFCL; card Tau2 42.2% (E4B), 24.5% (E2B) [L14] |
| `phi4-mini:3.8b-q4_K_M` | 3.84B [L13] | 2.5 GB | 128K | MIT [L14] | yes / yes (23 languages listed) [L14] | none | BFCL V4 FC 73.21 / 53.07 / 80.68 (snapshot 2025-11-03; far lower in earlier snapshots) [L18] |
| `granite4.1:3b`, `granite4.1:8b` | 3B, 8B | 2.1 GB, 5.3 GB | 128K | Apache-2.0 [L13][L14] | yes / no (12 languages, Russian not listed) [L14] | none | card BFCL v3 60.80 (3B), 68.27 (8B) [L14] |
| `granite4.2:3b`, `granite4.2:8b` | 3B, 8B | 2.2 GB, 5.3 GB | 128K | Apache-2.0 [L13][L14] | yes / no (same 12 languages) [L14] | "tool calling with integrated reasoning" [L14] | card BFCL (v4) 52.41 (3B), 52.39 (8B) [L14] |
| `ministral-3:3b`, `ministral-3:8b` | 3.4B and 8.4B language model, plus 0.4B vision encoder [L14] | 3.0 GB, 6.0 GB | 256K | Apache-2.0 [L13][L14] | Arabic listed; Russian not listed [L14] | none | no BFCL; card Arena Hard 0.305 (3B), 0.509 (8B) [L14] |
| `mistral:7b` (v0.3) | 7B | 4.4 GB | 32K | Apache ("distributed with the Apache license") [L13] | not checked | none | not on the current snapshot |
| SmolLM3-3B | 3B [L14] | not in the official library; user namespaces only [L13] | 64K trained, 128K with YaRN [L14] | Apache-2.0 [L14] | 6 native languages; Arabic, Chinese and Russian with "fewer tokens" [L14] | on by default [L14] | card "BFCL" 92.3 without thinking (version not stated) [L14] |

Notes on the table:

- The default `qwen3:4b` tag is not the instruct model: `qwen3:4b` shares its digest (359d7dd4bcda) with `qwen3:4b-thinking-2507-q4_K_M`; the instruct build is `qwen3:4b-instruct-2507-q4_K_M` (0edcdef34593) [L13].
- Llama 3.2 3B and 1B, Qwen3 1.7B and 0.6B, Gemma 3 1B and 270M exist for very small machines [L13]; only Qwen3 1.7B has acceptable published live and irrelevance scores among them [L18].
- Also in the library: Granite 3.3 (2B, 8B) and Granite 4 (350M, 1B, 3B) [L13]; Granite-3.2-8B-Instruct scores 79.77 / 60.33 / 80.53 on BFCL V4 FC [L18].
- Fine-tunes of 8B or fewer score higher on the same snapshot: BitAgent-Bounty-8B (81.60 / 93.12 / 97.48), ToolACE-2-8B (FC, 87.10 / 77.42 / 90.79) and Nanbeige4-3B-Thinking-2511 (FC, 81.58 / 79.42 / 83.09), all labelled Apache-2.0 by BFCL [L18]. None of them is in the official Ollama library; ToolACE and Nanbeige appear only as user uploads [L13]. Inference: user uploads have no trusted publisher to pin to, and fine-tunes inherit their base model's licence, which BFCL's label does not show; keep them out of the defaults.

### 3.2 Licence obligations

- Apache-2.0 and MIT models carry no acceptable use policy in their cards; NeonRadar does not redistribute weights (users pull them), so only attribution in documentation is needed (Inference).
- Llama 3.1 and 3.2: if you distribute Llama materials or a product that contains them you must "prominently display "Built with Llama"" and keep a "Notice" file; licensees with more than "700 million monthly active users" need a separate licence; the Acceptable Use Policy also lists "unauthorized or unlicensed practice of any profession including, but not limited to, financial, legal" [L16]. Both model cards list "Use in languages beyond those explicitly referenced as supported in this model card." as out of scope; the supported list is English, German, French, Italian, Portuguese, Hindi, Spanish and Thai [L16]. For the Llama 3.2 multimodal models only, rights are not granted to EU-domiciled individuals or companies [L16].
- Gemma 3 (and Gemma 1 to 3n): Gemma Terms of Use, "Last modified: April 1, 2026". Distribution must "include the use restrictions referenced in Section 3.2 as an enforceable provision"; the Prohibited Use Policy "is hereby incorporated by reference"; "Google reserves the right to restrict (remotely or otherwise) usage of any of the Gemma Services" [L17]. The policy ("Last modified: February 21, 2024") bans "Making automated decisions in domains that affect material or individual rights or well-being" "(e.g., finance, legal, employment, healthcare, housing, insurance, and social welfare)" and "Tracking or monitoring people without their consent" [L17]. Inference: an AML investigation tool is close enough to these clauses to need legal review; do not make Gemma 3 the default.
- Gemma 4: the Gemma terms page says "For Gemma 4 terms, see the Gemma 4 license", which links to a page titled "Apache License 2.0 | Gemma" (updated 2026-04-01); the Hugging Face card says "License: apache-2.0" [L17][L14].

### 3.3 Reading the BFCL numbers

- BFCL V4 changed the overall score to weight Agentic 40 percent, Multi-Turn 30 percent and Live, Non-Live and Irrelevance 10 percent each [L18]. NeonRadar's task is one turn: pick one template from a closed list (similar to the "multiple" categories), copy the arguments, or abstain (similar to "irrelevance": "Function calls with irrelevant function documentation") [L18]. Use the single-turn columns, not the overall score.
- The leaderboard page says "Last Updated: 2026-04-12" and loads its table from `data_overall.csv`. That file in the website branch (gh-pages commit 927b29c, 2026-10-16) is byte-identical to the BFCL-Result snapshot dated 2025-12-16 [L18], so the numbers above are the live leaderboard's numbers. No Qwen3.5, Gemma 4, Granite 4.1 or 4.2, Ministral 3 or Phi-4-mini row is in it.
- BFCL serves local models with vLLM or SGLang from the original weights [L18], not Q4_K_M GGUF through Ollama. Inference: quantised scores will be somewhat different; NeonRadar must measure its own benchmark.
- Phi-4-mini's FC scores swing between snapshots (non-live AST 9.50 in June 2025, 0.38 in August 2025, 73.21 in November 2025) [L18]. Inference: small-model function-calling scores depend heavily on the prompt handler; treat them as weak evidence.

### 3.4 Multilingual coverage

- Qwen3: "Qwen3 models are supporting 119 languages and dialects."; the Indo-European row lists Russian and Ukrainian; the Afro-Asiatic row lists "Arabic (Standard, Najdi, Levantine, Egyptian, Moroccan, Mesopotamian, Ta'izzi-Adeni, Tunisian)" [L15]. The technical report: Qwen3 "expands multilingual support from 29 to 119 languages and dialects" [L15].
- Qwen3.5: "Expanded support to 201 languages and dialects" [L14].
- Phi-4-mini: "Arabic, Chinese, Czech, Danish, Dutch, English, Finnish, French, German, Hebrew, Hungarian, Italian, Japanese, Korean, Norwegian, Polish, Portuguese, Russian, Spanish, Swedish, Thai, Turkish, Ukrainian", with the warning "Languages other than English will experience worse performance as well as performance disparities across non-English." [L14]
- Granite 4.1 and 4.2: "English, German, Spanish, French, Japanese, Portuguese, Arabic, Czech, Italian, Korean, Dutch, and Chinese" [L14].
- Ministral 3: "Supports dozens of languages, including English, French, Spanish, German, Italian, Portuguese, Dutch, Chinese, Japanese, Korean, Arabic." [L14]
- Inference for NeonRadar: the model only has to choose a template and copy name spans verbatim. Validate in Python that every entity slot is a substring of the question after Unicode NFC normalisation, and leave transliteration and name matching to the deterministic resolver. Measure per script (8.4).

## 4. Hardware (question 4)

### 4.1 Memory components

| Component | Size | Source |
|---|---|---|
| Weights, Q4_K_M | 1.4 GB (Qwen3 1.7B), 2.5 GB (Qwen3 4B Instruct, Phi-4-mini), 5.2 GB (Qwen3 8B), 4.9 GB (Llama 3.1 8B), 2.0 GB (Llama 3.2 3B) | [L13] |
| KV cache, f16 | bytes per token = 2 x layers x KV heads x head size x 2 bytes. Qwen3-4B-Instruct-2507 and Qwen3-8B: 36 layers, 8 KV heads, head size 128, so 147,456 bytes per token, 576 MiB at 4096 tokens, 1,152 MiB at 8192. Qwen3-1.7B: 28 layers, so 448 MiB at 4096 | configs [L14]; arithmetic |
| Parallel slots | the context is multiplied by the number of slots: "Required RAM will scale by `OLLAMA_NUM_PARALLEL` * `OLLAMA_CONTEXT_LENGTH`" | [L2] |
| llama-server host prompt cache | up to 8192 MiB by default; Ollama does not set `--cache-ram` for normal models | [L7][L1] |
| Compute buffers, runtime | not measured here | UNVERIFIED |
| Neo4j | heap 2 GB plus page cache 2 GB, plus native memory: "This memory will grow dynamically as needed and is not subject to the garbage collector." For the OS: "1GB is a good starting point for a server that is dedicated to running Neo4j." Hardware guideline for personal use and development: "2GB minimum, 16GB or more recommended." | [L20] |
| Docker Desktop VM | "Defaults to 50% of your host's memory." (Mac, Linux, Windows Hyper-V; WSL 2 has its own limits) | [L21] |

Inference: the host prompt cache can hold several cached prompts of up to 576 MiB each at 4096 tokens. Setting `LLAMA_ARG_CACHE_RAM=0` in Ollama's environment should reach llama-server (see 1.9) and cap it, but I could not test this.

### 4.2 Budget (Inference; must be measured)

| | 16 GB laptop, CPU only | 16 GB Apple Silicon | 8 GB laptop |
|---|---|---|---|
| Neo4j (2 GB heap, 2 GB page cache) | 4 GB plus native memory | same, inside the Docker Desktop VM (8 GB cap by default) | does not fit the default 4 GB VM; use Phase 1 small-data mode (1 GB heap, 512 MB page cache) [L27] |
| Default model `qwen3:4b-instruct-2507-q4_K_M` | 2.5 GB + 0.56 GiB KV, about 3.1 GB plus buffers | same, run natively with Metal [L2] | too large next to Neo4j, browser and IDE |
| Alternative `qwen3:8b-q4_K_M` | 5.2 GB + 0.56 GiB KV, about 5.8 GB plus buffers: tight | possible if the VM is sized for Neo4j only | no |
| Small option `qwen3:1.7b-q4_K_M` | 1.4 GB + 0.44 GiB KV | same | about 1.9 GB plus buffers: opt-in only |
| Left for OS, desktop, browser, IDE, FastAPI | about 8.9 GB (4B) or 6.2 GB (8B), before native memory and buffers | similar | very little; template-only by default |

The arithmetic for the last row is 16 GB minus 4 GB (Neo4j) minus the model line; it ignores Neo4j native memory and compute buffers, which must be measured.

### 4.3 Speed

Apple Silicon, llama.cpp `llama-bench`, Llama 2 7B Q4_0 (3.56 GiB), measured on build 8e672ef; "`TG` means "text-generation" (`bs = 1`)" [L19]:

| Chip (GPU cores, memory bandwidth) | Prompt processing, pp512 (tokens/s) | Generation, tg128 (tokens/s) |
|---|---|---|
| M1 (8, 68 GB/s) | 117.96 | 14.15 |
| M2 (10, 100 GB/s) | 179.57 | 21.91 |
| M3 (10, 100 GB/s) | 186.75 | 21.34 |
| M4 (10, 120 GB/s) | 221.29 | 24.11 |
| M1 Pro (16, 200 GB/s) | 266.25 | 36.41 |
| M3 Pro (18, 150 GB/s) | 341.67 | 30.74 |
| M4 Pro (20, 273 GB/s) | 439.78 | 50.74 |

Inference (naive scaling of generation speed by file size, since generation is bandwidth bound; real values will differ): for the 2.5 GB Qwen3 4B Instruct, roughly 22 tokens/s on M1 and 37 tokens/s on M4; for the 5.2 GB Qwen3 8B, roughly 10 and 18 tokens/s.

CPU only: no primary benchmark for typical laptops was found (UNVERIFIED). Two anchors:

- The `llama-bench` README shows an example run on an unnamed CPU with LLaMA 7B Q4_0: generation 4.05 tokens/s on 1 thread, 16.71 on 8 threads and 16.41 on 32 threads; prompt processing (pp 64) 6.17 tokens/s on 1 thread, 32.29 on 8 and 59.00 on 32 [L7]. Inference: generation stops scaling at about 8 threads (memory bound), and CPU prompt processing is tens of tokens per second for a 7B model.
- Upper bound for generation: tokens/s cannot exceed memory bandwidth divided by the bytes read per token (about the file size). Arithmetic: dual-channel DDR4-3200 peaks at 3200 million transfers/s x 8 bytes x 2 channels = 51.2 GB/s, giving at most about 20 tokens/s for a 2.5 GB model and 9.8 for 5.2 GB; dual-channel DDR5-5600 peaks at 89.6 GB/s, giving at most about 36 and 17 tokens/s. Real speeds are lower.

Latency model (Inference): time = model load (first request only) + new prompt tokens / prompt speed + output tokens / generation speed. With prompt caching, only tokens after the shared prefix are processed again [L7]. Example arithmetic: a 600-token system prompt at the 32 tokens/s of the README example takes about 19 s cold; after a warm-up, a 40-token question and a 50-token JSON answer at 15 tokens/s take a few seconds. Proposal: keep the template catalogue in the system prompt compact, send one warm-up request at start, set `keep_alive` to 30 minutes or more, and keep the deterministic parser as the first path.

## 5. Pinning a model for a published benchmark (question 5)

### 5.1 Tags are mutable pointers

- On the library tags page today, `qwen3:4b` has digest 359d7dd4bcda and 256K context, the same as `qwen3:4b-thinking-2507-q4_K_M`, while `qwen3:4b-q4_K_M` has 2bfd38a7daaf and 40K context [L13]. The short tag does not name a fixed build.
- `qwen3.5` tags show ages of "2 weeks ago" and "5 days ago" and the page says "Updated 4 days ago" [L13]. Tags are re-pushed.
- `qwen3.5:4b` (492e37dc6907, "3.3GB" to "4.0GB") is a manifest list; `qwen3.5:4b-q4_K_M` (d8b0f5e9760c, 3.3 GB) and `qwen3.5:4b-mlx` (61aa3858e9d3, 4.0 GB, same digest as `qwen3.5:4b-nvfp4`) are separate builds [L13]. On Apple Silicon a manifest list resolves to the MLX child first [L1]. Inference: the same tag can run Q4_K_M weights on Linux and NVFP4 MLX weights on a Mac.

### 5.2 Digests in Ollama

- The manifest digest is the SHA-256 of the manifest file's bytes, checked on every read (`readVerifiedManifest`) [L1].
- `ollama list` prints NAME, ID (the first 12 hex characters of the digest), SIZE and MODIFIED; `ollama ps` adds PROCESSOR, CONTEXT and RUNNER [L1].
- `/api/tags` returns `digest`; for a manifest list it returns the digest of the child selected on this machine [L1].
- `/api/show` returns `manifests` with `digest`, `runner`, `format` and `selected` for every child, and `details` with `format`, `family`, `parameter_size` and `quantization_level` [L1].
- `ollama show --modelfile` prints `FROM <model path>`, which is the weights blob `.../blobs/sha256-<64 hex>`; for a GGUF model this is the SHA-256 of the GGUF file [L1].
- Layer media types in a manifest include `application/vnd.ollama.image.model`, `.template`, `.params`, `.system` and `.license` [L1].
- Pulling by digest: the name grammar comment lists forms such as `{ model } "@" { digest }`, but `ParseNameBare` has no code for `@`, and `IsValid` says "The digest check has been removed as is planned to be added back in at a later time." [L1] Inference: `ollama pull name@sha256:...` does not pin; do not rely on it.
- The hidden CLI flag `--runner` on `pull` and `run` ("Runner to use for manifest list selection (mlx, ggml, llamacpp)") and the `runner` request field select a child explicitly [L1]. Hidden flags can change without notice (Inference).

### 5.3 What to record (Proposal)

| Item | How to get it |
|---|---|
| Model tag, for example `qwen3:4b-instruct-2507-q4_K_M` | configuration |
| Manifest digest (full 64 hex) | `GET /api/tags` `digest` |
| Weights blob digest | `ollama show --modelfile <tag>` (FROM line) or the `application/vnd.ollama.image.model` layer in the manifest file under `$OLLAMA_MODELS/manifests` |
| Template, params and licence layer digests | manifest file |
| Runner and format | `POST /api/show` `manifests` (selected child); `GET /api/ps` `runner` |
| Ollama version and bundled llama.cpp build | `GET /api/version`; `LLAMA_CPP_VERSION` of that release (b11669 for v0.40.6) [L1] |
| Docker image, if used | `ollama/ollama:0.40.6@sha256:265409e1d931028a8f7d5a32bcbafddd7bffbc6cc629d77efe9560adf692a5e7` [L4] |
| Server settings | `OLLAMA_CONTEXT_LENGTH`, `OLLAMA_NUM_PARALLEL`, `OLLAMA_FLASH_ATTENTION`, `OLLAMA_KV_CACHE_TYPE`, `OLLAMA_NO_CLOUD` |
| Request | full options, `think`, `format` schema hash, system prompt hash, template catalogue version |
| Rendered prompt (optional) | `/api/chat` with `"_debug_render_only": true` "returns the rendered template instead of calling the model" [L1]; a debug field that may change |
| Hardware | CPU model, RAM, GPU or Apple chip, OS version |

Two ways to freeze the weights (Inference; not tested here): (1) after the first pull, `ollama cp qwen3:4b-instruct-2507-q4_K_M neonradar-intent:2026-10-19` creates a local name that later pulls of the upstream tag do not touch (`/api/copy` exists [L1]); (2) import a GGUF file whose SHA-256 is published, with a Modelfile `FROM ./file.gguf`, using `ollama create`. NeonRadar compares the configured digest with `/api/tags` at start: a warning in normal use, a refusal in benchmark mode (Proposal). The full 64-hex digests of the library builds could not be read from here (the registry was blocked); the 12-hex IDs above come from the library pages (UNVERIFIED in full).

## 6. Alternatives to Ollama (question 6)

| Runtime | Version checked | Licence | Structured output | Network behaviour | Fit for an Apache-2.0 offline project |
|---|---|---|---|---|---|
| Ollama | v0.40.6 (2026-10-16) [L3] | MIT [L1] | `format` JSON schema through llama.cpp [L1] | background ollama.com calls unless `OLLAMA_NO_CLOUD=1`; desktop app update checks [L1] | **Default**: easy install, model registry, digests |
| llama.cpp `llama-server` | b11724 (2026-10-19); Ollama bundles b11669 = v0.7.0 [L7] | MIT [L7] | `json_schema` and `grammar` fields; OpenAI `response_format` with a schema [L7] | `--host` default 127.0.0.1; `--offline`; MCP proxy "default: disabled" [L7] | **Fits**; the same engine without the registry; NeonRadar would manage GGUF files and their SHA-256 itself |
| llamafile | 0.10.6 (2026-09-15) [L24] | Apache 2.0; "our changes to llama.cpp and whisper.cpp are licensed under MIT" [L24] | inherits llama.cpp's server (not checked in detail) | single-file executable [L24] | Fits by licence; based on llama.cpp commit 7f5ee54, behind upstream [L24] |
| LocalAI | v4.11.0 (2026-10-02) [L25] | MIT [L25] | `grammar` parameter, "only supported by models that use the llama.cpp backend" [L25] | `AutoloadGalleries` and `AutoloadBackendGalleries` default "true" [L25] | Fits by licence; much larger surface (agents, MCP, auth) to lock down |
| vLLM | v0.32.0 (2026-10-17) [L12] | Apache-2.0 [L12] | xgrammar or guidance backends [L12] | "vLLM collects anonymous usage data by default"; opt out with `VLLM_NO_USAGE_STATS=1`, `DO_NOT_TRACK=1` or `VLLM_DO_NOT_TRACK=1` [L12] | GPU server class; not laptop-first |
| LM Studio | app terms "Version: August 23, 2026" [L26] | proprietary: "exclusive property of Company"; licence for "personal and / or internal business purposes"; no sublicensing or distribution [L26] | not checked | terms defer to a separate privacy policy (not read) [L26] | **Does not fit** as a dependency; the `lms` CLI is MIT [L26]. Users could point an OpenAI-compatible setting at it themselves |

Schema limits that apply to Ollama and llama-server alike, from llama.cpp's grammar guide [L7]: "Unsupported features are skipped silently."; "Can't mix `properties` w/ `anyOf` / `oneOf` in the same type"; "`minimum`, `exclusiveMinimum`, `maximum`, `exclusiveMaximum`: only supported for `"type": "integer"` for now, not `number`"; "Nested `$ref`s are broken"; "`additionalProperties` defaults to `false`". Proposal: keep the schema flat, avoid `$ref`/`$defs` (Pydantic emits them for nested models), and validate every reply in Python.

## 7. neo4j-graphrag (question 7)

- Latest on PyPI: 1.22.0, wheel uploaded 2026-10-01; `requires_python` `<3.15,>=3.10.0`; licence "Apache License, Version 2.0" [L22].
- Core dependencies: fsspec, json-repair, neo4j `>=6.3.1,<7.0.0`, numpy, pydantic, pypdf, pyyaml, scipy, tenacity and types-pyyaml [L22]. The `nlp` extra (spaCy) applies only below Python 3.14 [L22].
- Python 3.14: `neo4j-graphrag[ollama]==1.22.0` installed on CPython 3.14.6. It pulled 23 packages and 189 MB of site-packages: scipy 81 MB plus 30 MB of libraries, numpy 30 MB plus 27 MB, pypdf 1.8 MB, and `ollama` 0.4.9 [L22]. `ollama` 0.6.3 alone: 12 packages, 13 MB [L6].
- Version conflict: the published `[ollama]` extra requires `ollama<0.5.0,>=0.4.4`. Resolving it with `ollama==0.6.3` fails: "Because neo4j-graphrag[ollama]>=1.22.0 depends on ollama>=0.4.4,<0.5.0 ... your requirements are unsatisfiable." [L22] Phase 1 pinned both `neo4j-graphrag>=1.22,<2` with `[ollama]` and `ollama>=0.6.3,<0.7` [L27]; that pair cannot be installed today.
- On main, commit 691bd39 (2026-10-15), "Update dependency ollama to >=0.6.3,<0.7.0 (#668)", fixes the pin; main still says version 1.22.0, so this is unreleased [L22].
- Structured output: `OllamaLLM.invoke(..., response_format=...)` raises `NotImplementedError("OllamaLLM does not currently support structured output")` in 1.22.0 and on main [L22]. A fixed schema can still be passed through `model_params={"format": ...}`, which the adapter forwards to `client.chat(**self.model_params)` (Inference from the code).
- Text2CypherRetriever guard (1.22.0): "EXPLAIN plans the query without executing it, so we can inspect its type and refuse anything that would mutate the database before it ever runs." It refuses unless `query_type` is `"r"` ("Refusing to execute non-read-only Cypher"), then runs the query with `routing_=neo4j.RoutingControl.READ` [L22]. The guard checks the statement type only. Inference: a read query can still be slow, and `LOAD CSV` "supports accessing CSV files via HTTPS, HTTP, and FTP" [L23], so a model-written read query could reach the network.
- Recommendation: a template-first copilot should not depend on neo4j-graphrag. The model never writes Cypher, so the retrievers do not apply; the adapter lacks structured output; the published extra blocks the current client; and the core install is heavy. Call Ollama directly: with httpx (already in the stack [L27]), which gives explicit timeouts, the `runner` and `truncate` fields and no environment surprises, or with `ollama>=0.6.3,<0.7` if typed responses are wanted (Proposal).

## 8. Answers for the spec writer (question 8)

### 8.1 Models

| Role | Tag | Licence | Why | Caveats |
|---|---|---|---|---|
| Default | `qwen3:4b-instruct-2507-q4_K_M` | Apache-2.0 | 2.5 GB; no thinking mode; on BFCL V4 FC, non-live AST 87.88 and the highest irrelevance detection (84.93) of the official-library models in the table [L18]; Arabic and Russian covered [L15] | 256K context is irrelevant; use 4096 |
| Alternative A | `qwen3:8b-q4_K_M` | Apache-2.0 | the highest live accuracy (80.53) of the official-library models in the table [L18]; same languages | 5.2 GB; tight on 16 GB CPU laptops; must send `think: false` |
| Alternative B | `phi4-mini:3.8b-q4_K_M` | MIT | different vendor; 2.5 GB; Arabic and Russian listed [L14] | weaker BFCL (live 53.07) and unstable across snapshots [L18]; card warns about non-English quality [L14] |
| 8 GB machines | `qwen3:1.7b-q4_K_M`, or no model | Apache-2.0 | 1.4 GB; BFCL V4 FC 82.92 / 74.61 / 76.54 [L18] | send `think: false` |
| Evaluate as well | `qwen3.5:4b-q4_K_M` (Apache-2.0, 201 languages, thinking on by default), `granite4.1:3b` (Apache-2.0, no Russian) | | newer or different vendor | not on the BFCL snapshot |

Avoid as defaults: Llama 3.1 and 3.2 (Arabic and Russian out of scope, community licence), Gemma 3 (prohibited use clauses), Gemma 4 E2B and E4B (4.6 GB to 9.5 GB downloads for 2.3B to 4.5B effective parameters) [L13][L14][L16][L17].

### 8.2 Exact Ollama settings and call (Proposal)

Server environment:

```sh
OLLAMA_HOST=127.0.0.1:11434
OLLAMA_NO_CLOUD=1
OLLAMA_CONTEXT_LENGTH=4096
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_KEEP_ALIVE=30m
OLLAMA_FLASH_ATTENTION=0        # or 1; fix it and record it
# never set OLLAMA_DEBUG_LOG_REQUESTS in normal use
```

Compose service (optional profile; on macOS run Ollama natively instead):

```yaml
  ollama:
    image: ollama/ollama:0.40.6@sha256:265409e1d931028a8f7d5a32bcbafddd7bffbc6cc629d77efe9560adf692a5e7
    profiles: ["llm"]
    ports: ["127.0.0.1:11434:11434"]
    environment:
      OLLAMA_NO_CLOUD: "1"
      OLLAMA_CONTEXT_LENGTH: "4096"
      OLLAMA_NUM_PARALLEL: "1"
      OLLAMA_MAX_LOADED_MODELS: "1"
      OLLAMA_KEEP_ALIVE: "30m"
    volumes: ["ollama:/root/.ollama"]
```

Request, `POST http://127.0.0.1:11434/api/chat`:

```json
{
  "model": "qwen3:4b-instruct-2507-q4_K_M",
  "messages": [
    {"role": "system", "content": "<fixed system prompt: compact template catalogue, slot rules, the JSON schema as text>"},
    {"role": "user", "content": "<the user's question>"}
  ],
  "format": {
    "type": "object",
    "properties": {
      "template_id": {"type": "string", "enum": ["<id 1>", "<id 2>", "none"]},
      "entities": {"type": "array", "items": {"type": "string", "minLength": 1, "maxLength": 120}, "maxItems": 3},
      "numbers": {"type": "array", "items": {"type": "number"}, "maxItems": 3}
    },
    "required": ["template_id", "entities", "numbers"],
    "additionalProperties": false
  },
  "stream": false,
  "think": false,
  "keep_alive": "30m",
  "options": {
    "temperature": 0,
    "top_k": 1,
    "top_p": 1.0,
    "min_p": 0.0,
    "seed": 42,
    "repeat_penalty": 1.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "num_ctx": 4096,
    "num_predict": 256,
    "num_batch": 512
  }
}
```

Rules:

- Keep `num_ctx`, `num_batch` and the system prompt constant, because a change reloads the model or breaks the cached prefix [L1][L7].
- Do not send `stop`; the model's params layer sets the right stop tokens [L13].
- `think: false` is accepted by non-thinking models and needed for Qwen3 and Qwen3.5 [L1][L14].
- Accept a reply only if `done` is true and `done_reason` is `"stop"`; `"length"` means `num_predict` cut it off.
- Parse `message.content` with Pydantic; check `template_id` is in the closed list; check every entity is a substring of the NFC-normalised question; check every number occurs in the question; then map slots to template parameters in Python. On any failure, fall back to "no template matched" (Proposal).
- Keep the prompt well below `num_ctx` and log `prompt_eval_count`; with plain httpx, send `"truncate": false` so that an oversize prompt fails instead of being cut [L1].
- Timeouts: connect 2 s; warm-up up to 300 s (model load); per question 60 s on CPU. On timeout, connection error or HTTP error, fall back as above.
- Startup sequence: `GET /api/version` (record, warn if untested), `GET /api/status` (require `cloud.disabled`), `GET /api/tags` (model present, digest equals the pinned one), `POST /api/show` (record `parameters`, `template`, `manifests`), then one warm-up `/api/chat` with the fixed system prompt [L1].
- Host: accept only loopback addresses unless the user opts in; ignore `OLLAMA_HOST` and `OLLAMA_API_KEY` from the environment [L5].
- Optional: `"logprobs": true, "top_logprobs": 5` returns token probabilities that could flag low-confidence template choices [L1]; untested.

### 8.3 Testing without any model (Proposal)

1. Interface: an `IntentModel` protocol with `pick(question, catalogue) -> RawPick`. Implementations: `OllamaIntentModel` (HTTP), `FakeIntentModel` (a dictionary from question to reply), `RecordedIntentModel` (replays fixtures). Pipeline tests use the fake and never need Ollama.
2. HTTP level: inject a transport. This works with `ollama` 0.6.3 on CPython 3.14.6 [L6]:

```python
import json, httpx, ollama

RECORDED = {"model": "qwen3:4b-instruct-2507-q4_K_M", "created_at": "2026-10-19T00:00:00Z",
            "message": {"role": "assistant", "content": json.dumps(
                {"template_id": "T01_owners_of", "entities": ["Acme Ltd"], "numbers": []})},
            "done": True, "done_reason": "stop"}

def handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    assert request.url.path == "/api/chat"
    assert body["options"]["temperature"] == 0 and body["think"] is False
    return httpx.Response(200, json=RECORDED)

client = ollama.Client(host="http://127.0.0.1:11434",
                       timeout=httpx.Timeout(60.0, connect=2.0),
                       transport=httpx.MockTransport(handler))
```

   The same transport works with a plain `httpx.Client(base_url=..., transport=...)`. The `ollama` project's own tests use `pytest-httpserver` [L5].
3. Failure cases to cover: HTTP 404 for a missing model (`ResponseError`), HTTP 500, connection refused (`ConnectionError`), `httpx.ReadTimeout`, non-JSON content, a `template_id` outside the list, an entity that is not in the question, `done_reason: "length"`, and `/api/status` with `cloud.disabled: false`.
4. Recorded responses: store request, response, Ollama version and model digest under a fixture folder named by the digest. A `--record` mode, run by a human against a real server, refreshes them; CI only replays. A snapshot test of the system prompt and schema hash forces re-recording when either changes.
5. End-to-end without a model: a tiny fake server that implements `/api/version`, `/api/status`, `/api/tags`, `/api/show` and `/api/chat` with canned replies, started in the Compose test profile.
6. Real-model runs are manual (a make target or a manually dispatched workflow), never in default CI; CI stays offline and downloads no weights.

### 8.4 What a human must measure before publishing results

1. Environment record: everything in 5.3, plus CPU or chip, RAM, GPU, OS, power mode and whether other heavy programs ran.
2. Accuracy on the benchmark questions: template-id accuracy, slot exact match, and "none" precision and recall, reported separately for Latin, Arabic, Cyrillic and mixed-script questions.
3. Repeatability: each question at least 5 times in random order, both right after a model load and after warm-up; report the agreement rate and list any question whose answer changed [L9].
4. Cross-machine: if numbers come from more than one machine (CPU, Metal, CUDA), report each separately; do not pool them [L9][L12].
5. Latency: cold load time, then p50 and p95 per question after warm-up, plus `prompt_eval_count / prompt_eval_duration` and `eval_count / eval_duration` from the API (durations are in nanoseconds [L2]), on a CPU-only laptop and on Apple Silicon.
6. Memory: peak resident memory of the Ollama and llama-server processes, `ollama ps` size, `docker stats` for Neo4j with 2 GB heap and 2 GB page cache, and swap use, on 16 GB and 8 GB machines.
7. Offline proof: with `OLLAMA_NO_CLOUD=1`, capture outbound connections during start, warm-up and a full benchmark run (firewall log or a connection monitor), and show `/api/status` output. Repeat with the network unplugged.
8. Baseline: the same questions through the deterministic parser alone, so the model's added value is visible.

## Sources

All checked on 2026-10-19 unless stated otherwise.

- [L1] ollama/ollama, tag v0.40.6, commit 2476d5ead197abe04629651028f83d48dc75d2b2 (2026-10-16), read-only clone: `LICENSE`, `LLAMA_CPP_VERSION` (also at v0.35.0, v0.40.0, v0.40.5, v0.40.7-rc0), `envconfig/config.go`, `server/routes.go`, `server/model_recommendations.go`, `server/model_show_cache.go`, `server/model_caches.go`, `server/cloud_proxy.go`, `server/model_thinking.go`, `server/model_list.go`, `server/images.go`, `server/sched.go`, `server/inference_request_log.go`, `server/prompt.go`, `internal/cloud`, `llm/server.go`, `llm/llama_server.go`, `manifest/manifest.go`, `manifest/paths.go`, `types/model/name.go`, `api/types.go`, `auth/auth.go`, `cmd/cmd.go`, `discover/runner.go`, `app/updater/updater.go`, `app/cmd/app/app.go`, `app/store/store.go`, `app/store/cloud_config.go`, `app/store/database.go`, `app/ui/ui.go`, `app/ui/app/src`, `Dockerfile`. https://github.com/ollama/ollama
- [L2] Ollama documentation in the same tag: `docs/api.md`, `docs/faq.mdx`, `docs/context-length.mdx`, `docs/docker.mdx`, `docs/gpu.mdx`, `docs/macos.mdx`, `docs/linux.mdx`, `docs/capabilities/structured-outputs.mdx`, `docs/capabilities/thinking.mdx`, `docs/capabilities/tool-calling.mdx`, `docs/capabilities/decision.mdx`, `docs/api/openai-compatibility.mdx`. https://github.com/ollama/ollama/tree/v0.40.6/docs
- [L3] Ollama releases page (the "Latest" and "Pre-release" markers) https://github.com/ollama/ollama/releases, and tag commits and dates from `git ls-remote` and shallow fetches: v0.35.0 (2026-09-28), v0.40.0 0d0720e (2026-10-06), v0.40.5 d919272 (2026-10-15), v0.40.6 2476d5e (2026-10-16), v0.40.7-rc0 8be580a (2026-10-17).
- [L4] Docker Hub API, ollama/ollama tags: https://hub.docker.com/v2/repositories/ollama/ollama/tags?page_size=15&ordering=last_updated and https://hub.docker.com/v2/repositories/ollama/ollama/tags/0.40.6 (manifest-list digest read twice, identical).
- [L5] ollama/ollama-python, tag v0.6.3, commit 8785556559ec1d045d27a1ba9d9cc7330c3d3cb1 (2026-09-28): `pyproject.toml`, `ollama/_client.py`, `ollama/_types.py`, `.github/workflows/test.yaml`; PyPI JSON https://pypi.org/pypi/ollama/json (0.6.3 uploaded 2026-09-29).
- [L6] Local measurement for this note: CPython 3.14.6, uv 0.11.32, `ollama` 0.6.3 from PyPI (httpx 0.28.1, pydantic 2.14.1); smoke test of sync and async `chat()` against `httpx.MockTransport`, the snippet in 8.3 as printed, and error mapping for HTTP 404, read timeout and refused connection; package counts and site-packages sizes with `uv pip list` and `du`. Run 2026-10-19 on Linux x86_64. The scripts are not part of the repository.
- [L7] ggml-org/llama.cpp, tag b11724, commit 99db719bdf07f7d537431ca556a0512bf3d995b6 (2026-10-19): `LICENSE`, `tools/server/README.md`, `grammars/README.md`, `common/sampling.cpp`, `src/llama-sampler.cpp`, `common/arg.cpp`, `tools/llama-bench/README.md`, `tools/completion/README.md`; tag b11669 = v0.7.0, commit 620d2225cc436ab0b001e3200e590e3b286ef9ab (2026-10-15), `tools/server/README.md`. https://github.com/ggml-org/llama.cpp
- [L8] Ollama issue #12559, "Non-deterministic structured output with same seed": https://github.com/ollama/ollama/issues/12559 (open or closed state not visible to the fetch tool).
- [L9] Ollama issue #5321, "Generated outputs inconsistent across different OS despite seed, temperature and num_ctx": https://github.com/ollama/ollama/issues/5321 (state not visible to the fetch tool); pull request #5760, "Make llama.cpp's cache_prompt parameter configurable", closed 2026-04-23: https://github.com/ollama/ollama/pull/5760
- [L10] Ollama pull request #10064, "support no caching when kvCacheType is "nocache" for deterministic completion": https://github.com/ollama/ollama/pull/10064 (state and dates not visible to the fetch tool).
- [L11] Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference", 2025-09-10: https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
- [L12] vllm-project/vllm, tag v0.32.0, commit 5df63a7203cdb9328d824a27b682e77c7b9928be (2026-10-17): `LICENSE`, `docs/usage/reproducibility.md`, `docs/usage/usage_stats.md`, `vllm/usage/usage_lib.py`, `docs/features/structured_outputs.md`. https://github.com/vllm-project/vllm
- [L13] Ollama library pages on ollama.com: https://ollama.com/library/qwen3 , https://ollama.com/library/qwen3/tags , https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M , https://ollama.com/library/qwen3:8b-q4_K_M , https://ollama.com/library/qwen3:1.7b-q4_K_M , https://ollama.com/library/qwen3.5 , https://ollama.com/library/qwen3.5/tags , https://ollama.com/library/llama3.1 , https://ollama.com/library/llama3.2 , https://ollama.com/library/gemma3 , https://ollama.com/library/gemma4 , https://ollama.com/library/phi4-mini , https://ollama.com/library/phi4-mini/tags , https://ollama.com/library/phi4-mini:3.8b-q4_K_M , https://ollama.com/library/granite4.1 , https://ollama.com/library/granite4.2 , https://ollama.com/library/ministral-3 , https://ollama.com/library/mistral , https://ollama.com/library/nimble , https://ollama.com/library/tev1 , and searches https://ollama.com/search?q=qwen , ?q=gemma , ?q=granite , ?q=phi , ?q=mistral , ?q=ministral , ?q=smollm , ?q=toolace , ?q=bitagent , ?q=nanbeige , ?c=decision . Read through the fetch tool (summaries); layer digests on tag pages were inconsistent between reads and are not used, except the Qwen3 template digest that matches the Ollama source.
- [L14] Hugging Face model cards and configs: https://huggingface.co/Qwen/Qwen3-8B , https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507 , https://huggingface.co/Qwen/Qwen3.5-4B , https://huggingface.co/google/gemma-4-E4B-it , https://huggingface.co/google/gemma-3-4b-it , https://huggingface.co/microsoft/Phi-4-mini-instruct , https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512 , https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512 , https://huggingface.co/ibm-granite/granite-4.1-8b , https://huggingface.co/ibm-granite/granite-4.2-8b , https://huggingface.co/HuggingFaceTB/SmolLM3-3B ; configs https://huggingface.co/Qwen/Qwen3-8B/raw/main/config.json , https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/main/config.json , https://huggingface.co/Qwen/Qwen3-1.7B/raw/main/config.json . BFCL rows of the Qwen3-4B-Instruct-2507, Qwen3.5-4B, Granite 4.1 and Granite 4.2 cards were read twice, identical.
- [L15] Qwen Team, "Qwen3: Think Deeper, Act Faster" (blog, language table): https://qwenlm.github.io/blog/qwen3/ ; "Qwen3 Technical Report", arXiv 2505.09388v1 (2025-05-14): https://arxiv.org/abs/2505.09388
- [L16] meta-llama/llama-models, commit 0e0b8c519242d5833d8c11bffc1232b77ad7f301 (2025-10-09): `models/llama3_1/LICENSE`, `models/llama3_1/USE_POLICY.md`, `models/llama3_1/MODEL_CARD.md`, `models/llama3_2/LICENSE`, `models/llama3_2/USE_POLICY.md`, `models/llama3_2/MODEL_CARD.md`. https://github.com/meta-llama/llama-models
- [L17] Google: Gemma Terms of Use (last modified 2026-04-01) https://ai.google.dev/gemma/terms ; Gemma Prohibited Use Policy (last modified 2024-02-21) https://ai.google.dev/gemma/prohibited_use_policy ; Gemma 4 licence page (Apache License 2.0, updated 2026-04-01) https://ai.google.dev/gemma/apache_2 . Whether any separate use policy applies to Gemma 4: UNVERIFIED (the linked "Prohibited use" and "Intended use statement" pages were not read).
- [L18] Berkeley Function Calling Leaderboard: page https://gorilla.cs.berkeley.edu/leaderboard.html ("BFCL V4", "Last Updated: 2026-04-12"; table not readable through the fetch tool); website source, ShishirPatil/gorilla branch gh-pages, commit 927b29cc0f96061898a3e568ceccbc8bc81ee6a4 (2026-10-16), `leaderboard.html`, `index_main.js` (loads `./data_${datasetName}.csv`) and `data_overall.csv` (byte-identical to the 2025-12-16 snapshot below); HuanzhiMao/BFCL-Result, commit cadd76a8dc62984e7bf15ecaf358f070bae745cc (2026-09-07), files `2025-12-16/score/data_overall.csv`, `2025-11-03/score/data_overall.csv`, `2025-08-26/score/data_overall.csv`, `2025-06-14/score/data_overall.csv` https://github.com/HuanzhiMao/BFCL-Result ; ShishirPatil/gorilla, commit 6ea57973c7a6097fd7c5915698c54c17c5b1b6c8 (2026-03-23), `berkeley-function-call-leaderboard/CHANGELOG.md`, `SUPPORTED_MODELS.md`, `TEST_CATEGORIES.md`, `README.md` https://github.com/ShishirPatil/gorilla .
- [L19] ggml-org/llama.cpp discussion #4167, "Performance of llama.cpp on Apple Silicon M-series" (summary table measured on build 8e672ef; read twice, identical values): https://github.com/ggml-org/llama.cpp/discussions/4167
- [L20] neo4j/docs-operations, branch 5.x, commit 9fe394427c2a077f56386d9fe1d01b376505101b: `modules/ROOT/pages/performance/memory-configuration.adoc`, `modules/ROOT/pages/installation/requirements.adoc`. https://github.com/neo4j/docs-operations/tree/5.x
- [L21] docker/docs, branch main, commit 31d174d090fd7111ca2199ed54a3978e0d4ac74d: `content/manuals/desktop/settings-and-maintenance/settings.md`. https://docs.docker.com/desktop/settings-and-maintenance/settings/
- [L22] neo4j-graphrag: PyPI JSON https://pypi.org/pypi/neo4j-graphrag/json (1.22.0 uploaded 2026-10-01); installed wheel on CPython 3.14.6 (`neo4j_graphrag/llm/ollama_llm.py`, `neo4j_graphrag/retrievers/text2cypher.py`); `uv pip compile` of `neo4j-graphrag[ollama]==1.22.0` with `ollama==0.6.3`; neo4j/neo4j-graphrag-python main at commit 0c377a5423f306fc9621a506047d2e1bd4a997ec (2026-10-19), `pyproject.toml` history (commit 691bd39, 2026-10-15) and `src/neo4j_graphrag/llm/ollama_llm.py`. https://github.com/neo4j/neo4j-graphrag-python
- [L23] neo4j/docs-cypher, branch dev, commit 332ce0538b5decb09f1ae2fd9dfad5dbcfacd992 (2026-10-15): `modules/ROOT/pages/clauses/load-csv.adoc`. https://github.com/neo4j/docs-cypher (the 5.x page was not compared).
- [L24] mozilla-ai/llamafile, tag 0.10.6, commit 017cdeb4b7217c0fb44cc7b61f44bd8ab2749dd2 (2026-09-15): `LICENSE`, `README.md`. https://github.com/mozilla-ai/llamafile
- [L25] mudler/LocalAI, tag v4.11.0, commit 58830f7ac508845a6f4efa32cfca06af422d4d82 (2026-10-02): `LICENSE`, `core/cli/run.go`, `docs/content/features/constrained_grammars.md`. https://github.com/mudler/LocalAI
- [L26] LM Studio Desktop App Terms of Service ("Version: August 23, 2026"): https://lmstudio.ai/app-terms ; lmstudio-ai/lms `LICENSE` at HEAD 43d4b2680e3cf679ad19753fcc7af0cb0e4a12a2: https://github.com/lmstudio-ai/lms . The privacy policy was not read (UNVERIFIED what the app collects).
- [L27] NeonRadar phase 1 research note `/home/claude/neonradar-phase1/research/stack.md` (written 2026-10-16): sections 6 and 8 and the pinned versions table (Ollama v0.40.5, httpx in the stack, small-data mode sizing). Reused, not re-verified, except where this note says otherwise.
