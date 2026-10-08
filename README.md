# FoodTrack AI - Telegram 个人健康 & 健身教练机器人

这是一个基于 **Telegram Bot + Gemini AI 大模型** 的个人健康管理软件，帮你自动化解决**饮食打卡**、**健身记录**、**身材追踪**和**智能教练建议**。

---

## 🌟 核心特性与体验

1. **🥗 饮食追踪（零繁琐输入）**
   - **拍照识菜**：直接在 Telegram 发送食物照片，多模态 AI 自动识别盘中食物、估算分量并计算卡路里及三大营养素（碳水/蛋白/脂肪）。
   - **自然语言记账**：打字输入（如 `中午吃了兰州牛肉面加了个煎蛋`），AI 自动提取营养数据并存储。
2. **🏋️ 健身运动记录**
   - 随手发训练笔记（如 `卧推70kg 4组8次，哑铃飞鸟15kg 3组`），AI 自动结构化解析动作、组数、负荷并估算消耗卡路里。
3. **⚖️ 身材与体重追踪**
   - 记录每日体重、腰围（如 `今早空腹 72.5kg`），自动归档趋势。
4. **🧠 AI 私人健康教练**
   - 输入 `/today` 或直接提问（如 `我今天还能吃夜宵吗？`），AI 综合你的摄入、训练与目标，给出个性化调整建议。

---

## 🛠️ 项目结构

```
Foodtrack/
├── bot.py           # Telegram 机器人主程序（处理交互、指令与图片）
├── ai_service.py    # AI 分析模块（意图识别、食物图像/文本解析、训练提取、教练建议）
├── database.py      # SQLite 异步数据库（存储用户饮食、训练、身材数据）
├── demo_sim.py      # 本地模拟测试脚本（无需连网即可验证完整链路）
├── requirements.txt # 项目依赖
├── .env.example     # 环境变量模板
└── README.md
```

---

## 🚀 如何运行并连接到你的 Telegram？

### 步骤 1：获取两个 Key（完全免费）
1. **Telegram Bot Token**：
   - 打开 Telegram，搜索并联系官方机器人 [@BotFather](https://t.me/BotFather)。
   - 发送 `/newbot`，按照提示输入名字，即可拿到一串 Token（如 `123456789:ABCdefGhIJK...`）。
2. **Gemini API Key**：
   - 访问 [Google AI Studio](https://aistudio.google.com/) 点击 **Create API Key** 获取。

### 步骤 2：配置环境变量
复制 `.env.example` 为 `.env`：
```bash
cp .env.example .env
```
用编辑器打开 `.env` 并填入上面的两个密钥：
```env
TELEGRAM_BOT_TOKEN=你的_Telegram_Bot_Token
GEMINI_API_KEY=你的_Gemini_API_Key
```

### 步骤 3：启动机器人
```bash
# 激活虚拟环境并启动
.venv/bin/python bot.py
```
终端显示 `🚀 Telegram Bot 已启动，正在等待消息...` 后，在 Telegram 里打开你的机器人点击 **Start** 即可体验！

