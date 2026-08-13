# VoiceBrief 后端部署指南（隐藏 AI key，免费）

这一步的目的是：让**陌生人打开链接就能用**，不用自己贴 key。
做法：把后端（worker.js）部署到 Cloudflare Workers —— 免费、不用绑卡、自动送一个 `*.workers.dev` 子域名。

> 域名问题：不用买自己的 .com。Cloudflare 免费送 `voicebrief.xxxx.workers.dev`。
> 以后真要品牌域名（如 voicebrief.com，约 $10/年）再买，不急。

---

## 方法 A：你自己点（约 3 分钟，免费）

1. 打开 https://cloudflare.com → 右上角 **Sign Up**（用邮箱注册，免费，**不用绑卡**）。
2. 登录后左边菜单点 **Workers & Pages** → 点 **Create** → 选 **Worker**。
3. 名字填 `voicebrief` → 点 **Deploy**（先随便部署一个占位）。
4. 部署完点 **Edit code**（或进 Worker 后点 **Quick edit**），把里面默认代码**全删掉**，粘贴本项目里的 `worker.js` 全部内容 → **Save and deploy**。
5. 回到 Worker 页面，点 **Settings** → **Variables**（或 Environment Variables）→ 加一行：
   - Variable name: `GROQ_KEY`
   - Value: 填你自己的 Groq key（就是 `gsk_` 开头那串，你在 groq.com 后台「API 密钥」里拿到的）
   - 点 **Save**（如果是生产环境变量，选 Encrypt）。
6. 部署完，页面顶部会显示你的地址，形如：
   `https://voicebrief.<你的子域名>.workers.dev`
   复制它。
7. 打开 VoiceBrief 落地页 https://liuxiaohang666888.github.io/voicebrief/ ，
   把上面那个地址粘进 **「VoiceBrief backend URL」** 框（只粘这一次，浏览器记住）。
8. 选音频 → Process → 几秒出结果 = 成功。现在任何人打开链接都能用，不用 key。

---

## 方法 B：让我从这边替你部署（你只给一个 token）

Cloudflare 网络从这台机器能连通，所以**只要你给我一个 Cloudflare API Token，我直接部署好，你啥都不用点**。

拿 token 步骤（1 分钟）：
1. 登录 Cloudflare → 右上角头像 → **My Profile** → **API Tokens** → **Create Token**。
2. 选 **Edit Cloudflare Workers** 模板（或自定义：Permissions 勾 `Account > Workers Scripts > Edit` 和 `Account > Workers KV Storage > Edit`）。
3. 生成后把那串 `CFP...` 发给我。

我拿到后：创建 Worker、写入代码、写入 GROQ_KEY、部署，然后把 `*.workers.dev` 地址发你。
你只需粘到落地页的 backend URL 框即可。

---

## 验证是否成功

打开落地页 → 粘 backend URL → 传一段语音 → 出「Transcript + Action items + Reply draft」即成功。
如果报错，把错误信息发我。

## 费用

- Cloudflare Workers 免费档：每天 10 万次请求，足够验证期和早期用户。
- Groq 转写：永久免费（见语音限制说明），每天 8 小时音频额度，单用户验证完全够。
- 合计：**0 元**。
