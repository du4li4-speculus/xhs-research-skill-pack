# xhs-research-skill-pack

一个面向“研究/检索/资料提取”的小红书 Agent Skill，重点解决：**正文能读，但真正的信息藏在图片里**。

它不复制 `xiaohongshu-mcp` 源码，而是把它当外部依赖，负责研究编排、图片落地与视觉读取规范。

## 能做什么

- 按博主名寻找账号和公开笔记
- 按关键词 / 考试 / 题型 / 时间搜索笔记
- 获取完整笔记正文与元数据
- 将 `get_feed_detail` 返回的 `note.imageList` 原图下载到本地
- 强制 Agent 逐张用视觉模型读取，而不是只看图片 URL
- 对 TOEFL / IELTS / SAT / ACT / A-Level 等考试资料做结构化提取
- 同题多来源合并，区分 P0/P1/P2 可信度

## 默认不做

为了控制费用和复杂度，默认不做：

- 视频下载
- 视频 ASR
- 字幕抓取
- 视频逐帧分析

视频仍会读取标题、正文和可用的静态图片/封面，并明确标注“动态画面未分析”。

## 底层依赖

使用：`xpzouying/xiaohongshu-mcp`

MCP 默认地址：

```text
http://localhost:18060/mcp
```

先按上游项目说明完成部署和小红书登录。

## 安装 Skill

把：

```text
skills/xhs-research/
```

复制或链接到你的 Agent 的 skills 目录。

同时确保 Agent 可以：

1. 调用 `xiaohongshu-mcp` 的 `check_login_status`、`search_feeds`、`get_feed_detail`、`user_profile`；
2. 执行本地 Python；
3. 把本地图片文件作为 image/vision 输入交给多模态模型。

## 图片下载

详情返回后保存 JSON，例如：

```text
feed_detail.json
```

执行：

```bash
python scripts/download_xhs_images.py \
  --input feed_detail.json \
  --out-dir .xhs-cache/FEED_ID
```

输出目录包含：

```text
01-xxxxxxxxxxxx.jpg
02-xxxxxxxxxxxx.webp
...
manifest.json
```

`manifest.json` 是“图片是否真的下载成功”的审计记录。

如果 CDN 需要登录 Cookie，可临时设置：

```bash
export XHS_COOKIE='你的 cookie'
```

不要把 Cookie 写进仓库。

## 推荐调用例

- `搜小红书博主 XX托福 最近半年所有 TOEFL 2026 写作新题，图片都要看。`
- `找过去一个月 IELTS 口语新题，多博主重复的合并。`
- `查 XX雅思 最近发布的图文资料，把图片里的题目完整提取。`

## 结果完整性要求

一个图文笔记只有满足以下条件，才可以说“已经读取”：

- 详情正文已取得；
- 与研究结论有关的图片已下载；
- 下载后的本地图片已被视觉模型实际查看；
- 未读/失败图片明确列出。

这能避免 Agent 把“拿到了图片 URL”误写成“已经看过图片”。
