# FitCheck - AI Nutritionist & Fitness Coach Telegram Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-blue.svg)](https://core.telegram.org/bots)
[![Powered by Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange.svg)](https://ai.google.dev/)

**FitCheck** is an all-in-one AI-driven Personal Health and Fitness Coach built directly inside Telegram. Powered by Google Gemini multimodal intelligence, FitCheck turns Telegram into an effortless personal health logger and proactive fitness coach.

---

## ✨ Key Features

- 🥗 **Instant Meal Tracking via Photos & Natural Language**:
  - Send food photos or type natural text (e.g., *"A bowl of beef noodles with an egg"*).
  - Multimodal AI estimates portions (grams), calories, and macronutrients (protein, carbs, fat).
  - Real-time inline meal adjustment commands (e.g., *"skipped the soup, subtract 150 kcal"*).
  - One-click meal deletion & reversal directly in Telegram.
- 🏋️ **Intelligent Workout & Progressive Overload Tracking**:
  - Log workouts naturally (e.g., *"bench press 70kg 4 sets 8 reps"*).
  - Automatically identifies muscle groups and tracks previous weights to encourage progressive overload.
- 📐 **Scientific Metabolic Calculation (BMR & TDEE)**:
  - Uses the **Mifflin-St Jeor Equation** based on gender, age, height, and weight.
  - Dynamically computes baseline BMR, TDEE, BMI, and personalized daily caloric & protein targets.
  - Recalculates metabolism dynamically whenever a new weigh-in is logged.
- 💧 **Hydration & Sleep Recovery Logging**:
  - Track water intake (e.g., *"drank 500ml water"*) and sleep duration (*"slept 8 hours"*).
- 📈 **Weekly Macro Review (`/weekly`)**:
  - Generates deep 7-day cyclical reviews covering caloric consistency, muscle group balance, and weight smoothing trends.
- ⏰ **Proactive Evening Accountability Coach**:
  - Automated evening checkup (APScheduler) at 20:30 scanning for missing workouts or severe caloric/protein deficits.

---

## 🏗️ Architecture

```
FitCheck/
├── bot.py             # Telegram Bot application & event dispatcher
├── ai_service.py      # Google Gemini AI multimodal & NLP parsing engine
├── database.py        # SQLite async engine with Mifflin-St Jeor metabolic math
├── requirements.txt   # Python dependencies
├── Dockerfile         # Production Docker container setup
├── .dockerignore      # Docker build exclusion
├── .gitignore         # Strict git ignore (prevents key & db leaks)
└── README.md          # Documentation
```

---

## 🚀 Quick Start (Local Setup)

### 1. Clone the repository
```bash
git clone https://github.com/zishuaishu-ctrl/fitcheck.git
cd fitcheck
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Populate your API credentials inside `.env`:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```
> - Get `TELEGRAM_BOT_TOKEN` for free from [@BotFather](https://t.me/BotFather) on Telegram.
> - Get `GEMINI_API_KEY` for free from [Google AI Studio](https://aistudio.google.com/).

### 3. Run with Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

---

## ☁️ Cloud Deployment (Render / Docker)

FitCheck is containerized and ready for 24/7 cloud deployment.

### Deploying on Render (Background Worker)
1. Fork or push this repository to your GitHub account.
2. Log in to [Render](https://render.com/) and click **New +** -> **Background Worker**.
3. Connect your repository.
4. Set **Runtime** to `Docker`.
5. Under **Environment Variables**, add:
   - `TELEGRAM_BOT_TOKEN` = `your_token`
   - `GEMINI_API_KEY` = `your_key`
6. Click **Create Background Worker**. Render will build the Docker container and keep your coach running 24/7!

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
