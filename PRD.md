# FinTech News Monitor — 产品需求文档

**版本：** 1.0
**日期：** 2026-03-12
**状态：** 待审阅

---

## 目录

1. [项目概述](#1-项目概述)
2. [用户画像与使用场景](#2-用户画像与使用场景)
3. [功能需求](#3-功能需求)
4. [数据管道规格](#4-数据管道规格)
5. [前端规格](#5-前端规格)
6. [配置文件规范](#6-配置文件规范)
7. [自动化与部署](#7-自动化与部署)
8. [非功能性需求](#8-非功能性需求)
9. [技术架构](#9-技术架构)
10. [验收标准](#10-验收标准)
- [附录 A：未来增强功能（v2）](#附录-a未来增强功能v2)
- [附录 B：配置维护指南](#附录-b配置维护指南)

---

## 1. 项目概述

### 1.1 问题陈述

金融科技从业者、研究人员和爱好者目前需要同时关注大量分散的信息源——加密货币博客、监管公告、银行业媒体和风投通讯——才能保持信息同步。目前缺少一个统一的、持续更新的聚合层，能够：

- 过滤噪音（招聘信息、赞助内容、活动推广、无关科技资讯）
- 在异构来源之间统一应用领域分类标签
- 无需用户登录、无基础设施成本、除配置外零维护

### 1.2 产品目标

| 目标编号 | 描述 |
|---------|------|
| G-01 | 从 9 个精选 RSS 源聚合 FinTech 相关新闻，汇总到单一页面 |
| G-02 | 通过关键词黑名单自动过滤噪音内容 |
| G-03 | 将文章自动归类至最多 10 个领域标签 |
| G-04 | 提供加载速度快、移动端自适应的静态网页 |
| G-05 | 通过 GitHub Actions 每日自动更新，无需人工干预 |
| G-06 | 每次构建成功后自动部署至 Vercel |

### 1.3 范围界定

**在范围内：**
- Python 数据管道（RSS 拉取、清洗、过滤、打标签、渲染）
- 静态 HTML/CSS/JS 输出（`index.html`）
- 三个 YAML 配置文件（`sources.yml`、`keywords.yml`、`exclude.yml`）
- GitHub Actions CI/CD 工作流
- Vercel 托管部署

**不在范围内：**
- 全文爬取或文章存档
- 用户账号、身份认证或个性化功能
- 评论、评分或社交功能
- 后端 API 或数据库
- 付费或付费墙内容源
- 多语言支持（v1 仅支持英文内容）

### 1.4 成功指标

- 移动端 4G 网络下页面加载时间 < 2 秒
- 每次每日构建中零重复文章
- 至少 90% 的展示文章与 FinTech 真实相关（人工抽查）
- 黑名单过滤器命中率 100%（对包含黑名单词的文章）
- GitHub Actions 连续 5 天构建成功无失败

---

## 2. 用户画像与使用场景

### 2.1 用户画像

**画像 A — FinTech 分析师**
- 角色：专注金融科技的风投机构或对冲基金投资分析师
- 目标：每天早上扫描交易信号、监管变化和市场事件
- 行为：在桌面端打开页面，筛选"Funding_MA"或"Central_Banking_Policy"标签，阅读 5–10 条摘要后点击跳转原文
- 痛点：不想手动查看 6 个以上的网站；需要有价值的信号，而非噪音

**画像 B — RegTech 专业人员**
- 角色：合规官员或监管咨询顾问
- 目标：追踪 FCA 发布内容、AML/KYC 动态和沙盒政策
- 行为：在搜索框输入"sanctions"或"CBDC"等关键词；依赖 RegTech_Compliance 和 Central_Banking_Policy 标签
- 痛点：官方监管网站 UX 体验差；需要聚合视图

**画像 C — 银行产品经理**
- 角色：新兴银行或传统银行数字化团队的产品经理
- 目标：监控竞争格局——挑战者银行和 BaaS 供应商在发布什么？
- 行为：筛选"Digital_Banking"和"Open_Banking"；在通勤路上用手机浏览标题和摘要
- 痛点：通用科技 RSS 源文章太杂；需要银行领域专项过滤

**画像 D — 研究生 / 学术研究者**
- 角色：金融科技或数字金融方向的研究生
- 目标：从权威来源（BIS、FCA、Finovate）建立阅读清单
- 行为：不筛选标签，直接浏览全部列表；阅读摘要后点击跳转原始来源
- 痛点：没有单一的学术级 FinTech 聚合器

### 2.2 使用场景

| 场景编号 | 用户 | 目标 | 操作步骤 |
|---------|------|------|---------|
| UC-01 | 任意用户 | 浏览所有最新 FinTech 新闻 | 加载页面 → 滚动文章列表 → 点击标题跳转原文 |
| UC-02 | 分析师 | 按领域标签筛选 | 点击一个或多个标签按钮 → 列表缩小至匹配文章 |
| UC-03 | RegTech 专员 | 搜索特定主题 | 在搜索框输入关键词 → 列表实时过滤 |
| UC-04 | 任意用户 | 组合标签+搜索 | 选择标签 → 输入搜索词 → 两个过滤器同时生效 |
| UC-05 | 任意用户 | 重置视图 | 点击"清除筛选"按钮 → 恢复完整列表 |
| UC-06 | 任意用户 | 确认数据新鲜度 | 查看页头的"最后更新"时间戳 |
| UC-07 | 任意用户 | 查看数据来源 | 查看页脚 RSS 来源列表 |

---

## 3. 功能需求

### 3.1 数据采集（后端）

**FR-01 — 多源 RSS 抓取**
- 系统在每次管道运行时，必须拉取 `sources.yml` 中列出的所有来源
- 每个来源的拉取必须设置超时时间（默认：15 秒）
- 若某来源失败（网络错误、非 2xx 状态码、格式错误的 Feed），管道必须记录警告日志，跳过该来源，继续处理其余来源
- 验收：当 9 个来源中有 1 个故意设为不可达时，构建成功，其余 8 个来源正常处理

**FR-02 — 文章结构化解析**
- 每条 RSS 条目必须被标准化为包含以下字段的数据结构：`title`（标题）、`link`（链接）、`published_date`（ISO 8601 格式）、`summary`（摘要）、`source_name`（来源名称）
- 若 Feed 条目无 `summary` 字段，该字段必须设为空字符串（不得为 null）
- 若 `published_date` 缺失或无法解析，必须使用管道运行时间戳，并标记 `date_unknown: true`
- 验收：处理后输出中每篇文章的 5 个字段均存在且类型正确

**FR-03 — 文本清洗**
- 标题和摘要必须去除所有 HTML 标签
- 标题和摘要必须去除首尾空白字符
- 关键词匹配、标题去重等比较操作必须使用小写标准化文本
- HTML 实体（如 `&amp;`、`&nbsp;`、`&#8217;`）必须在处理前解码为纯文本
- 验收：渲染输出中不得出现 `<p>`、`<a>`、`<strong>` 等 HTML 标签

**FR-04 — 去重**
- 主去重键：精确 `link` URL 匹配（不区分大小写，去除末尾斜杠）
- 辅助去重键：标准化标题相似度——仅在空白、标点或大小写上有差异的文章视为重复
- 发现重复时，保留发布日期最早的条目
- 验收：将同一篇文章注入两次（一次 URL 末尾有斜杠），输出中只有 1 篇

**FR-05 — 黑名单过滤**
- 若 `exclude.yml` 中的任何词条以不区分大小写的子字符串方式出现在文章标题或摘要中，该文章必须被排除
- 黑名单过滤在相关性关键词过滤之前执行
- 验收：标题为"We Are Hiring a Compliance Engineer"的文章被排除；摘要中含"Hiring"的文章同样被排除

**FR-06 — FinTech 相关性过滤**
- 经黑名单过滤后，若文章标题或摘要未命中 `keywords.yml` 中任何标签组的关键词，必须被排除
- 匹配方式：不区分大小写的子字符串匹配
- 验收：一篇关于手机摄像头的 TechCrunch 文章（无 FinTech 关键词）被排除；一篇提及"Series B"和"digital banking"的文章被保留

**FR-07 — 自动打标签**
- 每篇通过过滤的文章必须被分配 `keywords.yml` 中一个或多个标签键
- 所有关键词命中的标签组都必须被分配（支持多标签）
- 通过 FR-06 的文章不可能有零个标签
- 验收：一篇关于"CBDC pilot sandbox"的文章同时获得 `Central_Banking_Policy` 和 `Sandbox_Innovation` 两个标签

**FR-08 — 排序**
- 最终文章列表必须按 `published_date` 降序排列（最新在前）
- `date_unknown: true` 的文章必须排在列表末尾
- 验收：输出中第一篇文章是发布时间最新的文章

**FR-09 — 静态 HTML 生成**
- 管道必须将所有处理后的文章渲染为单一 `index.html` 文件
- HTML 必须有效（无未闭合标签、无格式错误属性）
- `index.html` 文件大小在日常运行中不得超过 5 MB
- 验收：`index.html` 通过 W3C HTML5 验证，零错误

### 3.2 前端（index.html）

**FR-10 — 页头**
- 必须显示网站名称："FinTech News Monitor"
- 必须显示"最后更新"时间戳，格式易于阅读（例如："Last updated: 12 Mar 2026, 06:00 UTC"）
- 页头必须固定在顶部（滚动时保持可见）
- 验收：时间戳在桌面端和移动端均可见

**FR-11 — 标签筛选按钮**
- 必须为当前文章集中出现的每个标签渲染一个可点击按钮
- 当前构建中无文章的标签不得渲染按钮
- 已选中（激活）的标签按钮必须有视觉上的区别（例如实心背景 vs. 描边）
- 可同时选中多个标签；过滤器显示匹配任意已选标签的文章（OR 逻辑）
- 验收：同时选中"Payments"和"Crypto_Web3"，显示带有任一标签的文章；取消一个后列表相应缩小

**FR-12 — 搜索框**
- 必须是一个文本输入框，用户输入时实时过滤文章列表（无需提交按钮）
- 搜索必须匹配文章标题和摘要文本（不区分大小写）
- 触发过滤的最小输入长度：1 个字符
- 验收：在搜索框输入"CBDC"，列表仅显示标题或摘要中包含"cbdc"的文章

**FR-13 — 组合过滤逻辑**
- 当标签过滤器和搜索文本同时生效时，必须应用 AND 逻辑：文章必须同时满足标签条件和搜索条件
- 验收：选中"RegTech_Compliance"并搜索"sanctions"，仅显示带该标签且包含"sanctions"的文章

**FR-14 — 清除筛选按钮**
- 当任何过滤器（标签或搜索）处于激活状态时，按钮必须可见
- 点击后必须取消所有已选标签、清空搜索框、恢复完整文章列表
- 验收：应用标签和搜索词后，点击"清除筛选"，所有文章恢复可见，无激活状态

**FR-15 — 文章卡片**

每篇文章必须渲染以下内容：
- 标题作为可点击超链接（`target="_blank"`，`rel="noopener noreferrer"`）指向原文 URL
- 来源名称（如"CoinDesk"、"FCA"）
- 发布日期（易读格式，如"11 Mar 2026"）
- 摘要文本（展示截断至 280 字符并加省略号；完整文本保留在 DOM 中供搜索使用）
- 一个或多个标签徽章，样式与标签筛选按钮一致

**FR-16 — 空状态**
- 当当前过滤条件下无结果时，必须显示："No articles match your current filters."
- 空状态内必须提供"清除筛选"的操作入口
- 验收：选中一个无文章的标签，显示空状态提示信息

**FR-17 — 页脚**
- 必须列出 `sources.yml` 中配置的所有 RSS 来源及其名称
- 必须包含免责声明："Content sourced from third-party RSS feeds. FinTech News Monitor does not own or endorse any linked content."
- 验收：页脚在桌面端和移动端均清晰可见

---

## 4. 数据管道规格

### 4.1 处理流程

```
[sources.yml] ──────────────────────┐
[keywords.yml] ─────────────────────┤
[exclude.yml] ──────────────────────┘
        │
        ▼
  第 1 步：加载配置
        │  启动时解析全部三个 YAML 文件
        │  验证：每个来源有 name + url；keywords 至少 1 个标签；
        │  exclude 至少 1 个关键词。验证失败则终止并输出描述性错误。
        │
        ▼
  第 2 步：拉取 RSS Feed
        │  对 sources.yml 中每个来源：
        │    - 携带 User-Agent 头发起 HTTP GET
        │    - 超时：15 秒
        │    - 成功：传入解析器
        │    - 失败：记录 WARNING 日志（来源名+错误信息）；继续
        │
        ▼
  第 3 步：解析 Feed 条目
        │  对每条 Feed 条目：
        │    - 提取：title、link、published、summary/description、source_name
        │    - 将发布时间标准化为 ISO 8601 UTC 格式
        │    - 去除标题和摘要中的 HTML 标签
        │    - 解码 HTML 实体；去除首尾空白
        │
        ▼
  第 4 步：去重
        │  主键：精确 link 匹配（小写化，去末尾斜杠）
        │  辅助键：标准化标题匹配（小写，合并空白，去除非字母数字字符）
        │  冲突时保留发布日期最早的条目
        │
        ▼
  第 5 步：黑名单过滤
        │  拼接：lowercase(title) + " " + lowercase(summary)
        │  若任意排除关键词为子字符串：丢弃文章；记录 DEBUG 日志
        │
        ▼
  第 6 步：相关性过滤 + 自动打标签
        │  对每篇文章：逐一检查 keywords.yml 中的所有标签组
        │  若零个组匹配：丢弃文章
        │  若 ≥1 个组匹配：将所有匹配的标签键分配给文章
        │
        ▼
  第 7 步：排序
        │  按 published_date 降序排列
        │  date_unknown=True 的文章移至列表末尾
        │
        ▼
  第 8 步：渲染 index.html
        │  注入：文章列表、标签集合、构建时间戳、来源列表
        │  输出：index.html（有效 HTML5）
        │
        ▼
  [index.html] ──► git commit ──► Vercel 部署
```

### 4.2 边界情况与处理方式

| 边界情况 | 处理方式 |
|---------|---------|
| RSS 来源返回 HTTP 404 | 记录 WARNING；跳过该来源；管道继续 |
| RSS 来源返回格式错误的 XML | feedparser 自动处理；若设置了 bozo 标志，记录 WARNING |
| 文章无 `<pubDate>` | 使用管道运行时间戳；设置 `date_unknown=True`；排至末尾 |
| 文章标题为空字符串 | 丢弃文章；记录 DEBUG |
| 文章链接为空或非有效 URL | 丢弃文章；记录 DEBUG |
| 摘要超过 10,000 字符 | 截断至 10,000 字符再处理；日志记录 |
| 所有来源同时失败 | 管道以错误码 1 退出；现有 `index.html` 保持不变 |
| 关键词同时在黑名单和标签列表中 | 黑名单优先；文章被丢弃 |
| 所有文章过滤后为零篇 | 渲染包含空状态 UI 的页面；构建不失败 |
| 重复 URL 但来源名不同 | 保留最早日期的条目；记录来源名称 |
| 文章日期为未来时间 | 保留文章；正常排序（将出现在列表顶部） |
| Feed 返回 0 条条目 | 记录 INFO；视为空来源；继续 |
| 条目同时缺少 `summary` 和 `description` | 摘要设为空字符串；文章继续处理 |
| 标题/摘要含 Unicode / 非 ASCII 字符 | 原样保留；确保 HTML 输出为 UTF-8 编码 |

### 4.3 性能目标

| 指标 | 目标值 |
|-----|-------|
| 管道总运行时间 | < 120 秒 |
| 单来源拉取超时 | 15 秒 |
| 每日最大处理文章数 | 无硬性上限；设计支持每日最多 500 篇 |

### 4.4 日志规范

| 级别 | 记录事件 |
|-----|---------|
| INFO | 管道启动/结束；每个来源拉取成功（含文章数量）；最终输出文章数；index.html 写入完成 |
| WARNING | 来源拉取失败；检测到格式错误的 Feed；因缺少必要字段而丢弃文章 |
| DEBUG | 每篇因黑名单或相关性过滤被排除的文章（含原因） |

所有日志输出至 stdout，供 GitHub Actions 捕获。

---

## 5. 前端规格

### 5.1 技术约束

- 原生 HTML5、CSS3、JavaScript（ES6+）
- 不引入任何外部 JavaScript 库（无 jQuery、React、Vue）
- 不引入任何外部 CSS 框架（无 Bootstrap、Tailwind CDN）
- 所有 CSS 和 JavaScript 嵌入 `index.html` 文件内
- 原因：消除 CDN 依赖故障风险；文件完全自包含，可作为本地文件直接打开

### 5.2 布局结构

```
┌──────────────────────────────────────────────────┐
│  页头（固定置顶）                                 │
│  "FinTech News Monitor"      最后更新：...        │
├──────────────────────────────────────────────────┤
│  筛选栏                                          │
│  [Crypto_Web3] [Payments] [Digital_Banking] ...  │
│  [搜索框：________________________] [清除筛选]   │
├──────────────────────────────────────────────────┤
│  文章列表                                        │
│  ┌────────────────────────────────────────────┐  │
│  │ 文章卡片                                   │  │
│  │ 标题（链接）                               │  │
│  │ 来源 · 日期                                │  │
│  │ 摘要文本（≤280 字符）...                   │  │
│  │ [标签徽章] [标签徽章]                      │  │
│  └────────────────────────────────────────────┘  │
│  ... （重复）                                    │
├──────────────────────────────────────────────────┤
│  页脚                                            │
│  RSS 来源：CoinDesk | TechCrunch | ...           │
│  免责声明文字                                    │
└──────────────────────────────────────────────────┘
```

### 5.3 组件规格

**5.3.1 页头**
- 位置：固定置顶（sticky top）
- 内容：`<h1>` 网站名称 + `<span>` 最后更新时间戳
- 背景：与文章列表区域视觉上有明显区分

**5.3.2 筛选栏**
- 标签按钮：从嵌入的 `ARTICLES` 数据动态渲染
- 按钮状态：默认（描边）、激活/已选（实心填充）、悬停（视觉反馈）
- 标签显示文本：下划线替换为空格（`Digital_Banking` → "Digital Banking"）
- 搜索输入框：`type="text"`，`placeholder="Search articles..."`，移动端全宽显示
- 清除按钮：无过滤器时隐藏；任意过滤器激活时显示

**5.3.3 文章卡片**
- 语义元素：`<article>`
- 标题：`<h2>` 内嵌 `<a>` 链接；字体加粗；CSS `line-clamp` 限制两行
- 元信息行：来源名称 + 分隔符 + 格式化日期；颜色较淡
- 摘要：`<p>` 标签；展示截断至 280 字符；完整文本存储在 `data-full-summary` 属性中供搜索索引
- 标签：`<span class="tag">` 元素；视觉样式与筛选按钮一致；卡片内标签不可点击
- 卡片悬停：轻微阴影提升效果

**5.3.4 空状态**
- 元素：`<div class="empty-state">` 位于文章列表容器内
- 主文本："No articles match your current filters."
- 副文本："Try removing a tag filter or clearing your search."
- 包含内联"清除筛选"按钮

**5.3.5 页脚**
- 语义元素：`<footer>`
- 来源列表：来源名称行内展示，各来源链接至其 RSS URL
- 免责声明段落
- 构建日期（与页头时间戳相同）

### 5.4 响应式断点

| 断点 | 表现 |
|-----|------|
| ≥ 1200px（桌面） | 文章列表单列或双列；筛选栏单行 |
| 768px–1199px（平板） | 文章列表单列；筛选栏可能换行 |
| < 768px（手机） | 单列；标签按钮横向滚动或换行；搜索框全宽 |

### 5.5 JavaScript 数据模型

所有文章数据以 JavaScript 常量形式嵌入 `index.html`：

```javascript
const ARTICLES = [
  {
    title: "...",
    link: "https://...",
    source: "CoinDesk",
    date: "2026-03-11",           // ISO 日期字符串（用于排序）
    date_display: "11 Mar 2026",  // 易读格式
    summary: "...",               // 截断至 280 字符（用于展示）
    summary_full: "...",          // 完整文本（用于搜索索引）
    tags: ["Crypto_Web3", "Funding_MA"]
  },
  // ...
];
```

### 5.6 JavaScript 过滤逻辑

```
filterArticles():
  selectedTags  = 当前激活的标签按钮 ID 集合
  searchQuery   = 搜索输入框的值（去除首尾空格，转小写）

  对 ARTICLES 中每篇文章：
    tagMatch    = (selectedTags 为空)
                  OR (article.tags 与 selectedTags 有交集)
    searchMatch = (searchQuery 为空)
                  OR (article.title.toLowerCase() 包含 searchQuery)
                  OR (article.summary_full.toLowerCase() 包含 searchQuery)
    visible     = tagMatch AND searchMatch

  更新 DOM：显示/隐藏文章卡片
  若 visible 为零：显示空状态
  切换清除按钮的显示状态
```

### 5.7 无障碍要求

- 所有交互元素必须支持键盘操作（Tab + Enter）
- 标签按钮必须使用 `<button>` 元素
- 激活的标签按钮必须设置 `aria-pressed="true"`
- 搜索输入框必须有关联的 `<label>`（视觉隐藏可接受）
- 文章链接必须使用描述性文本（完整标题，而非"点击这里"）
- 颜色对比度必须满足 WCAG 2.1 AA（正文 4.5:1；大文本 3:1）
- 页面必须有唯一的 `<h1>`（网站名称），文章标题使用 `<h2>`
- 遵守 `prefers-reduced-motion` 媒体查询（为设置了该选项的用户关闭 CSS 动画）

---

## 6. 配置文件规范

### 6.1 `sources.yml`

```yaml
# 格式规范
sources:                     # 必填；列表；最少 1 项
  - name: string             # 必填；唯一；展示名称
    url: string              # 必填；有效的 https:// RSS/Atom Feed URL
    language: string         # 必填；ISO 639-1 代码（如"en"）
    focus: string            # 必填；简短的领域描述
    update_frequency: enum   # 必填；可选值：low | medium | medium_high | high
    notes: string            # 可选；维护者内部备注
```

**验证规则：**
- `name` 在所有条目中必须唯一
- `url` 必须以 `https://` 开头
- 至少需要 1 个来源
- 推荐最大值：20 个来源（管道运行时间约束）

**当前来源（v1）：**

| 名称 | 聚焦领域 | 更新频率 |
|-----|---------|---------|
| CoinDesk | 加密货币/Web3 | high |
| TechCrunch | 融资/通用科技 | high |
| The Block | 加密货币/政策 | high |
| The Fintech Times | 支付/数字银行/RegTech | high |
| Sequoia Capital Blog | 风投/趋势 | medium |
| Tearsheet | 银行科技/支付 | high |
| Financial Conduct Authority (FCA) | 监管/政策 | high |
| Finovate | FinTech 创新 | medium |
| Bank for International Settlements (BIS) | 央行/数字货币 | medium_high |

### 6.2 `keywords.yml`

```yaml
# 格式规范
tags:                        # 必填；字典；最少 1 个键
  TagName:                   # 必填；字符串键（有效的 Python 标识符）
    - keyword_string         # 必填；列表；每个标签至少 1 个；不区分大小写的子字符串匹配
```

**验证规则：**
- 标签键必须是有效的 Python 标识符（字母、数字、下划线；不含空格）
- 每个标签至少有 1 个关键词
- 少于 3 个字符的关键词可以使用，但不推荐（误匹配率高）
- 每个标签推荐最多 50 个关键词

**当前标签（v1）：**

| 标签键 | 描述 | 关键词数量 |
|-------|-----|---------|
| Crypto_Web3 | 加密货币、区块链、DeFi、Web3 | 13 |
| Payments | 支付基础设施、清算、钱包、BNPL | 33 |
| Digital_Banking | 新兴银行、BaaS、核心银行、KYC | 21 |
| Open_Banking | 开放金融 API、PIS、AIS、TPP | 14 |
| RegTech_Compliance | 合规科技、AML、制裁、欺诈 | 19 |
| Funding_MA | 风投轮次、并购、IPO、估值 | 17 |
| Central_Banking_Policy | CBDC、货币政策、BIS、央行 | 10 |
| AI_in_Finance | 金融领域 AI/ML、算法交易 | 8 |
| Sandbox_Innovation | 监管沙盒、创新中心、PoC | 6 |
| WealthTech | 财富管理、资产管理、RIA | 10 |

### 6.3 `exclude.yml`

```yaml
# 格式规范
exclude_keywords:            # 必填；扁平列表；最少 1 项
  - keyword_string           # 不区分大小写的子字符串；匹配标题+摘要拼接文本
```

**验证规则：**
- 必须是扁平列表（不分层级嵌套；注释供维护者阅读）
- 黑名单关键词优先级高于标签关键词——若两者同时匹配，文章被丢弃

**当前排除类别（v1）：**

| 类别 | 示例 | 数量（约） |
|-----|-----|---------|
| 招聘 / 求职 | "hiring"、"job opening"、"apply now" | ~15 |
| 营销 / 销售 CTA | "sponsored"、"free trial"、"book a demo" | ~18 |
| 活动 / 公关 | "webinar"、"conference"、"early bird" | ~14 |
| 媒体内容 | "podcast episode"、"watch now"、"video" | ~6 |
| 无关科技 / 娱乐 | "gaming"、"celebrity"、"movie release" | ~7 |

---

## 7. 自动化与部署

### 7.1 GitHub Actions 工作流

**文件：** `.github/workflows/update.yml`

**触发方式：** 每日定时（`cron: '0 6 * * *'`，UTC 时间 06:00）+ 手动 `workflow_dispatch`

**工作流步骤：**

```yaml
steps:
  - name: 拉取仓库代码
    uses: actions/checkout@v4

  - name: 配置 Python 环境
    uses: actions/setup-python@v5
    with:
      python-version: "3.11"

  - name: 安装依赖
    run: pip install -r requirements.txt

  - name: 运行管道脚本
    run: python pipeline.py
    # 若退出码非零，工作流停止，现有 index.html 保持不变

  - name: 检测文件变化
    id: diff
    run: |
      git diff --quiet index.html || echo "CHANGED=true" >> $GITHUB_OUTPUT

  - name: 提交并推送（仅在有变化时）
    if: steps.diff.outputs.CHANGED == 'true'
    run: |
      git config user.name "github-actions[bot]"
      git config user.email "github-actions[bot]@users.noreply.github.com"
      git add index.html
      git commit -m "chore: daily update [$(date -u '+%Y-%m-%d %H:%M UTC')]"
      git push
```

**失败行为：**
- 若 `pipeline.py` 退出码非零：工作流失败；`index.html` 不被覆盖；不触发 Vercel 部署
- GitHub Actions 在失败时发送邮件通知

### 7.2 Python 依赖规格

**文件：** `requirements.txt`

```
feedparser>=6.0.10
pyyaml>=6.0
jinja2>=3.1.0
```

使用的标准库模块：`datetime`、`re`、`html`、`logging`、`urllib.parse`

### 7.3 Vercel 配置

**文件：** `vercel.json`

```json
{
  "version": 2,
  "builds": [
    {
      "src": "index.html",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        }
      ]
    }
  ]
}
```

**Vercel 项目设置：**
- 框架预设：Other（静态）
- 构建命令：无（`index.html` 已由 GitHub Actions 预先构建）
- 输出目录：`.`（根目录）
- 触发部署的分支：仅 `main`

**部署流程：**
1. GitHub Actions 将更新后的 `index.html` 推送至 `main`
2. Vercel Webhook 检测到推送 → 部署新文件（通常在 30 秒内完成）
3. 生产环境 URL 更新为最新内容

### 7.4 仓库文件结构

```
/ （仓库根目录）
├── .github/
│   └── workflows/
│       └── update.yml          # GitHub Actions 工作流
├── sources.yml                 # RSS 来源配置          ✅ 已存在
├── keywords.yml                # 标签关键词映射         ✅ 已存在
├── exclude.yml                 # 黑名单配置            ✅ 已存在
├── pipeline.py                 # 主数据管道脚本         🔲 待创建
├── requirements.txt            # Python 依赖           🔲 待创建
├── vercel.json                 # Vercel 部署配置        🔲 待创建
├── index.html                  # 生成的静态页面         🔲 待创建
└── README.md                   # 项目说明文档           🔲 待创建
```

---

## 8. 非功能性需求

### 8.1 性能

| 需求 | 目标值 |
|-----|-------|
| 移动端 4G 网络首次加载时间 | < 2 秒 |
| index.html 文件大小 | 通常 < 5 MB；绝对上限 10 MB |
| Vercel CDN 首字节时间（TTFB） | < 200ms |
| JavaScript 过滤器响应时间（最多 500 篇文章） | < 50ms |
| 管道总运行时间 | < 120 秒 |

### 8.2 可靠性

- 若发生完全失败（所有来源不可用或管道报错），管道不得覆盖有效的现有 `index.html`
- 单个来源失败不得导致整个管道失败
- 静态站点在管道运行期间必须保持可访问（Vercel 提供旧版本直到新版本部署完成）
- 若管道产出零篇文章，必须渲染包含空状态提示的页面，而非空文件

### 8.3 无障碍访问

- 符合 WCAG 2.1 Level AA 标准
- 所有交互元素支持键盘操作
- 屏幕阅读器兼容性：语义化 HTML5 元素，必要处添加 ARIA 属性
- 激活状态除颜色外还有其他视觉区分（边框/文字样式）
- 遵守 `prefers-reduced-motion` 媒体查询

### 8.4 安全性

- 所有文章链接渲染时添加 `rel="noopener noreferrer"`，防止标签劫持
- 不使用内联 JavaScript 事件处理器（使用 `addEventListener`）
- 不加载外部 CDN 或第三方脚本（消除供应链 XSS 风险）
- 管道不执行或运行 RSS Feed 中的任何内容
- 不存储或传输任何用户提交的数据
- RSS 来源 URL 必须使用 `https://`（配置验证阶段强制执行）
- `vercel.json` 中设置 `Content-Security-Policy` 响应头

### 8.5 可维护性

- 新增 RSS 来源：仅编辑 `sources.yml`，零代码改动
- 新增或删除关键词：仅编辑 `keywords.yml`，零代码改动
- 新增黑名单词条：仅编辑 `exclude.yml`，零代码改动
- `pipeline.py` 中每个主要处理步骤必须有内联注释说明
- `keywords.yml` 中的标签键是唯一来源；HTML 和 JS 以编程方式使用它们

### 8.6 兼容性

- 浏览器支持：Chrome 90+、Firefox 90+、Safari 14+、Edge 90+
- 移动端：iOS Safari 14+、Android Chrome 90+
- `index.html` 必须在作为本地文件直接打开时也能正常渲染（无 CORS 依赖）

---

## 9. 技术架构

### 9.1 技术栈

| 层次 | 技术 | 选用理由 |
|-----|-----|---------|
| 数据管道 | Python 3.11 | 跨平台；RSS 库生态成熟 |
| RSS 解析 | feedparser 6.x | 健壮；支持 Atom + RSS 2.0；具备 bozo 检测（格式错误 Feed） |
| 配置管理 | PyYAML 6.x | 人类可读；文档完善 |
| HTML 模板 | Jinja2 3.x | 模板与逻辑分离；自动安全转义 |
| 前端渲染 | 原生 HTML/CSS/JS | 零依赖；最大可移植性；支持离线访问 |
| 托管 | Vercel（静态） | 免费套餐；全球 CDN；Git 触发即时部署 |
| CI/CD | GitHub Actions | 与仓库原生集成；公开仓库免费；支持定时工作流 |

### 9.2 数据流示意图

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions 运行环境                   │
│                                                             │
│  [sources.yml] + [keywords.yml] + [exclude.yml]            │
│                         │                                   │
│                         ▼                                   │
│                   pipeline.py                               │
│                         │                                   │
│         ┌───────────────┼───────────────┐                  │
│         ▼               ▼               ▼                  │
│    [CoinDesk]     [TechCrunch]    [...共9个来源]             │
│       RSS             RSS             RSS                   │
│         └───────────────┴───────────────┘                  │
│                         │                                   │
│                    原始文章池                                │
│                         │                                   │
│       解析&清洗 → 去重 → 黑名单过滤 → 相关性过滤+打标签      │
│                         │                                   │
│                      排序                                   │
│                         │                                   │
│               渲染 index.html（Jinja2）                     │
│                         │                                   │
└─────────────────────────┼───────────────────────────────────┘
                          │ git commit + push
                          ▼
                    GitHub 仓库（main 分支）
                          │ Webhook
                          ▼
                    Vercel CDN 部署
                          │
                          ▼
                    用户浏览器
                （标签筛选 + 搜索，纯 JS 实现）
```

### 9.3 管道模块结构（`pipeline.py`）

```
pipeline.py
├── load_config()                        # 加载并验证全部 3 个 YAML 文件
├── fetch_feed(source)                   # 拉取单个 RSS 来源，返回原始条目
├── fetch_all_feeds(sources)             # 编排所有来源，汇总结果
├── parse_entry(entry, source_name)      # 标准化为规范字典结构
├── clean_text(text)                     # 去除 HTML；解码实体；标准化空白
├── normalize_url(url)                   # 小写化 + 去末尾斜杠
├── normalize_title(title)              # 小写化 + 去标点 + 合并空白
├── deduplicate(articles)               # 主键 + 辅助键去重
├── apply_blacklist(articles, keywords) # 按 exclude.yml 过滤
├── apply_relevance_and_tags(articles, tags)  # 过滤 + 分配标签
├── sort_articles(articles)             # 按日期降序；未知日期排末尾
├── render_html(articles, tags, sources, build_time)  # Jinja2 渲染
└── main()                              # 编排所有步骤；处理退出码
```

---

## 10. 验收标准

### 10.1 管道验收标准

| 标准编号 | 验收条件 | 测试方法 |
|---------|---------|---------|
| AC-P01 | 9 个来源全部可达时，管道无错误完成 | 运行 `python pipeline.py`；确认退出码为 0；`index.html` 已创建 |
| AC-P02 | 1 个来源不可达时，管道以 WARNING 完成 | 模拟 1 个来源超时；确认退出码为 0；其余 8 个来源的文章存在 |
| AC-P03 | 输出中无重复文章 | 注入带/不带末尾斜杠的同一 URL；确认输出中只有 1 篇 |
| AC-P04 | 含黑名单词的文章不出现在输出中 | 确认无含"hiring"、"webinar"、"sponsored"等词的文章 |
| AC-P05 | 所有输出文章至少有一个来自 `keywords.yml` 的标签 | 随机抽查 20 篇文章；每篇至少有 1 个标签 |
| AC-P06 | 文章按最新优先排序 | 检查输出中前 5 篇文章的日期；必须为降序 |
| AC-P07 | 未知日期的文章排在末尾 | 注入无 pubDate 的文章；确认其出现在所有有日期文章之后 |
| AC-P08 | 多标签分配正常 | 确认"CBDC pilot sandbox"的文章同时获得两个标签 |
| AC-P09 | `index.html` 为有效 HTML5 | 使用 W3C 验证器检查生成文件；零错误 |
| AC-P10 | 管道运行时间 < 120 秒 | 在干净环境中计时运行；所有来源可达 |

### 10.2 前端验收标准

| 标准编号 | 验收条件 | 测试方法 |
|---------|---------|---------|
| AC-F01 | 页面加载且所有文章正常渲染 | 在 Chrome 中打开 `index.html`；确认文章列表已填充 |
| AC-F02 | 页头中"最后更新"时间戳可见 | 打开页面；确认时间戳与构建时间一致 |
| AC-F03 | 点击标签按钮过滤文章列表 | 点击"Payments"；确认仅显示带该标签的文章 |
| AC-F04 | 点击多个标签显示并集结果 | 点击"Payments"+"Crypto_Web3"；确认带任一标签的文章均显示 |
| AC-F05 | 搜索框实时过滤 | 输入"CBDC"；确认列表在 100ms 内缩小 |
| AC-F06 | 标签+搜索应用 AND 逻辑 | 选"RegTech_Compliance"并搜索"sanctions"；确认仅显示交集 |
| AC-F07 | 清除筛选恢复完整列表 | 应用过滤后点击清除；确认所有文章可见，无激活状态 |
| AC-F08 | 空状态信息正确显示 | 选择一个无文章的标签；确认显示空状态提示 |
| AC-F09 | 文章链接在新标签页打开 | 点击文章标题；确认 `target="_blank"` 行为生效 |
| AC-F10 | 页面在手机端（375px 宽）可用 | 使用 Chrome DevTools 手机模拟；无横向滚动；文字可读 |
| AC-F11 | 标签按钮支持键盘操作 | Tab 键导航至按钮；Enter 键激活；确认过滤生效 |
| AC-F12 | 激活标签按钮有视觉区别 | 激活标签；确认按钮样式发生变化 |
| AC-F13 | 页脚列出全部 9 个 RSS 来源 | 滚动至页脚；数来源名称；必须为 9 个 |
| AC-F14 | 页脚中有免责声明 | 确认页脚中免责声明文字可见 |

### 10.3 自动化验收标准

| 标准编号 | 验收条件 | 测试方法 |
|---------|---------|---------|
| AC-A01 | GitHub Actions 工作流每天 UTC 06:00 运行 | 查看工作流运行历史；连续 5 天确认成功运行 |
| AC-A02 | 工作流可手动触发 | 在 GitHub Actions 界面使用"Run workflow"按钮 |
| AC-A03 | 成功运行后 `index.html` 提交至 `main` | 触发手动运行；确认 git log 有"chore: daily update"提交 |
| AC-A04 | Vercel 在 git push 后 2 分钟内完成部署 | 查看 Vercel 部署日志；确认生产 URL 更新了时间戳 |
| AC-A05 | 工作流失败不会覆盖现有 `index.html` | 在 `pipeline.py` 中引入语法错误；触发运行；确认 `index.html` 未变化 |
| AC-A06 | `requirements.txt` 包含所有依赖 | 检查文件存在且包含正确的版本约束 |

### 10.4 内容质量验收标准

| 标准编号 | 验收条件 | 测试方法 |
|---------|---------|---------|
| AC-Q01 | 每次日常构建后至少有 10 篇文章 | 统计渲染页面中的文章卡片；必须 ≥ 10 |
| AC-Q02 | 无招聘或求职类文章可见 | 手动扫描前 50 篇文章；零招聘/求职文章 |
| AC-Q03 | 无赞助/广告类内容可见 | 手动扫描前 50 篇文章；零"sponsored"/"paid post"文章 |
| AC-Q04 | 来源激活时 FCA 文章出现 | 确认输出中至少有 1 篇 FCA 来源的文章 |
| AC-Q05 | BIS 文章出现且标签正确 | 确认 BIS 文章存在；标记了 `Central_Banking_Policy` |

---

## 附录 A：未来增强功能（v2）

以下功能明确不在 v1 范围内，但记录于此以指导未来迭代：

1. **话题趋势图** — 按标签展示每周文章数量的柱状图，由管道生成为内嵌 SVG
2. **来源健康仪表盘** — 页脚中显示每个来源最后一次成功拉取时间戳的表格
3. **RSS 输出 Feed** — 与 `index.html` 同步生成 `feed.xml`，供高级用户在 RSS 阅读器中订阅经过过滤的 Feed
4. **可配置日期范围过滤** — JavaScript 实现"过去 24 小时 / 7 天 / 30 天"的过滤器
5. **多语言来源支持** — YAML 中标记非英文来源；可选接入 DeepL API 翻译
6. **关键词频率分析** — 管道生成 `stats.json` 附属文件，记录每次运行中各标签下命中最多的关键词

---

## 附录 B：配置维护指南

### 新增 RSS 来源
1. 编辑 `sources.yml`，添加新条目（填写所有必填字段：`name`、`url`、`language`、`focus`、`update_frequency`）
2. 无需修改任何代码
3. 下次管道运行时将自动包含新来源

### 新增标签
1. 编辑 `keywords.yml`，添加新键（有效 Python 标识符）及至少一个关键词
2. 无需修改任何代码；下次构建后标签按钮将自动出现在前端

### 新增黑名单词条
1. 编辑 `exclude.yml`，向 `exclude_keywords` 列表追加新词条
2. 无需修改任何代码

### 临时禁用某个来源
1. 在 `sources.yml` 中注释掉或删除该来源条目
2. 下次构建将不包含该来源的任何文章

### 删除某个标签
1. 在 `keywords.yml` 中删除该标签键及其关键词列表
2. 仅与该标签匹配的文章将在下次构建中从输出中消失
3. 无需修改任何代码
