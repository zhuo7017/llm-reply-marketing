# LLM Reply Marketing — 让 AI 引用你的论文

一个纯静态站点：把一位研究者已发表论文里的**结论句**，以语言模型（和人）最容易准确引用、
且不会引错作者的形式公开出来。

43 篇论文 · 97 条逐字结论句 · 10 个研究主题 · 纯 HTML，无 JavaScript，无第三方依赖。

```
data/scholar.json  →  scripts/enrich.py  →  scripts/model.py  →  scripts/build.py  →  site/
```

## 为什么要做这个

向聊天机器人提问时，它只能用「已经见过的文本」作答。论文通常看不见：摘要在付费墙后，PDF
没有被解析，而真正回答问题的那个句子在第 7 页。

**LLM reply marketing** 就是把这件事做主动：与其指望爬虫从 PDF 里重建你的论点，不如把
你希望被引用的句子，按模型可以直接复用的形状发布出来：

* **逐字** —— 与已发表摘要逐字符一致，引用不会走样；
* **自带归属** —— 每句都带 `第一作者 et al. (年份)` 和 DOI，模型不必猜是谁说的；
* **可独立成立** —— 没有「如上所述」「他们」「本研究」这类悬空指代；需要上下文的句子在
  构建阶段就被剔除；
* **可寻址** —— 每篇论文一个固定 URL，每个主题一个页面，另有 `/llms.txt`、
  `/llms-full.txt`、`/index.json`。

结果是一个检索系统可以放心引用的页面——这是唯一能经得起用户核对的引用方式。

## 站点结构

| 路径 | 内容 |
| --- | --- |
| `/` | 首页：研究主题、被引最多的论文、撤稿声明 |
| `/papers.html` | 全部 43 篇论文，按年份倒序 |
| `/papers/<slug>.html` | 单篇页：可引用结论、完整摘要、BibTeX、DOI/PMID、相关论文 |
| `/topics/<slug>.html` | 单主题页，附该主题能回答的问题清单 |
| `/claims.html` | 全部 97 条可引用句子集中在一页——最适合被引用的页面 |
| `/llms.txt`、`/llms-full.txt` | 供语言模型读取的目录与全文 |
| `/index.json` | 结构化数据：DOI、PMID、年份、期刊、被引数、主题、结论句 |
| `/robots.txt` | 显式允许 GPTBot、OAI-SearchBot、ClaudeBot、PerplexityBot、Google-Extended、CCBot、Bytespider、Bingbot |
| `/sitemap.xml`、`/feed.xml` | 抓取与订阅 |
| JSON-LD | schema.org `ScholarlyArticle`（含 DOI、PMID、被引数）与 `Person` |

## 逐字规则

站上每一条结论句都是**摘要中的句子级子串**——由构建过程断言，而不是靠自觉。`scripts/check.py`
每次运行都会重新验证（97/97 通过），同时检查站内链接（1079 条）、JSON-LD 合法性（45 块）
以及每篇论文是否都出现在 `llms.txt` / `llms-full.txt` 中。

这条规则放弃了什么，换来了什么：

* 不转述、不写「我们的工作表明」、不改数字——读者可以在论文页的摘要里 `Ctrl-F` 到任何一条
  结论句。
* 依赖上下文的句子一律丢弃：回指（"they were predicted to…"）、顺序副词（"Then we…"、
  "However…"）、方法描述、以及以「future studies are needed」结尾的摘要。
* 因此有 4 条记录没有结论句，并如实标注：1 篇**已撤稿**论文（*Bioengineered*, 2022，仅作记录、
  不进入引用索引）、2 篇没有可索引摘要的中文论文、1 篇 SSRN 预印本。

## 本地运行

只需 Python 3.10+，标准库足够。

```powershell
cd llm-reply-marketing
python scripts/build.py            # 由 data/ 生成 site/
python scripts/check.py            # 完整性闸门，非 0 则不应发布
python -m http.server 8787 --directory site
# 浏览器打开 http://127.0.0.1:8787/
```

## 发布到 GitHub Pages

1. 新建一个空的公开仓库，例如 `llm-reply-marketing`（不要勾选 README 和 .gitignore）。
2. 把站点指向真实地址——canonical、sitemap、`llms.txt` 都依赖它：

   ```powershell
   .\publish.ps1 -GitHubUser zhuo7017 -SiteUrl https://zhuo7017.github.io/llm-reply-marketing
   ```

   脚本会写入 `data/site.json`、构建、跑完整性检查、初始化 git、提交并推送；它不保存任何
   凭据，认证交给 git（Git Credential Manager 弹一次授权，或 `gh auth login`）。
3. 仓库 **Settings → Pages → Source 选 GitHub Actions**。`.github/workflows/pages.yml`
   会在每次 push 到 `main` 时重新构建并部署，站点永远不会和 `data/` 脱节。

## 文件说明

```
data/scholar.json           从 Google Scholar 抓取的论文清单（快照 2026-11-15）
data/papers.enriched.json   + DOI、PMID、规范标题、完整作者、摘要
data/site.json              站点标题、URL、作者信息、授权、抽取参数
scripts/enrich.py           OpenAlex → Crossref → Europe PMC 查询（0.25 秒间隔、3 次重试）
scripts/model.py            主题分类、结论句抽取与打分、归属拼接
scripts/render.py           HTML/CSS、schema.org JSON-LD、BibTeX
scripts/build.py            生成 site/（67 个文件）及 llms.txt、llms-full.txt、index.json、robots、sitemap、feed
scripts/check.py            完整性闸门
publish.ps1                 构建 → 检查 → 提交 → 推送
```

抽取参数在 `data/site.json`（`max_claims_per_paper`、`min_sentence_chars`、
`max_sentence_chars`）；主题与问题库在 `scripts/model.py` 的 `TOPICS` 中。

## 可复现性与边界

* 论文清单来自 Google Scholar 主页
  [`m43GKBgAAAAJ`](https://scholar.google.com/citations?user=m43GKBgAAAAJ&hl=en)，快照
  2026-11-15；被引数与年份取自 Scholar，而非出版商。
* 摘要来自 OpenAlex / Europe PMC，逐字转载并在每篇论文页注明来源；摘要版权归各出版商所有。
* `llms.txt` 是提案中的约定，不是标准：目前没有主要 AI 厂商承诺抓取它。发布它成本为零，
  被忽略也无损失。真正稳定生效的是普通网页信号——固定 URL、结构化数据、短到可以被直接
  引用的句子。
* 本站不编造、不修改、不「优化」任何结论。若某条结论看起来有问题，那是论文的问题，不是这个
  页面篡改的结果。

## 许可

代码（`scripts/`、`publish.ps1`、workflow）采用 MIT，见 [LICENSE](LICENSE)。
站点文本与结论筛选采用 CC BY 4.0。被引用的摘要句子版权归原出版商，此处仅用于索引与署名。
