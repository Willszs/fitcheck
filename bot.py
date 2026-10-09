import os
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from database import (
    init_db, add_meal, update_meal, delete_meal, get_recent_meals,
    add_workout, get_previous_exercise_record, add_body_metric,
    record_habit, get_today_summary, get_weekly_report_data,
    get_or_create_user, update_user_profile, get_all_user_ids
)
import ai_service

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

KEYBOARD = [
    [KeyboardButton("🥗 记录餐食"), KeyboardButton("🏋️ 记录健身")],
    [KeyboardButton("💧 记录喝水/睡眠"), KeyboardButton("📋 查看/管理餐食")],
    [KeyboardButton("⚖️ 记录体重"), KeyboardButton("📈 每周复盘报告")],
    [KeyboardButton("⚙️ 设置身材档案"), KeyboardButton("📊 今日总览与建议")]
]
REPLY_MARKUP = ReplyKeyboardMarkup(KEYBOARD, resize_keyboard=True)

async def safe_reply(update: Update, text: str, reply_markup=REPLY_MARKUP):
    try:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    user = await get_or_create_user(user_id, username)

    welcome_msg = (
        f"👋 你好 **{username}**！我是你的 **全能 AI 私人教练与身材总管**。\n\n"
        "🔥 **全新功能已全部实装**：\n"
        "1. 🏋️ **渐进超负荷追踪**：记录动作时自动比对历史重量，提醒你加重量冲极限！\n"
        "2. ✏️ **餐食微调**：随时对我说“汤没喝扣150卡”或“牛肉双份加15g蛋白”，自动实时修正！\n"
        "3. 💧 **补水与睡眠**：支持记录水与睡眠（如 `喝水500ml`、`昨晚睡了8小时`）评估身体恢复！\n"
        "4. 📈 **每周深度复盘**：点击 `[📈 每周复盘报告]` 获取过去7天宏观营养与肌群分布诊断！\n"
        "5. ⏰ **主动教练提醒**：晚间自动扫描打卡进度并主动督促！\n\n"
        f"📋 **当前档案**：{user.get('gender','男')} | 身高 {user.get('height',175)}cm | 目标 {user.get('goal','增肌')} | 预算 {user.get('target_calories',2480)}kcal\n\n"
        "👇 **点击下方菜单开始体验**："
    )
    await safe_reply(update, welcome_msg)

async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    summary = await get_today_summary(user_id)
    status_msg = await update.message.reply_text("🔍 正在综合你的代谢基线与今日数据生成诊断报告...")
    advice = await ai_service.generate_integrated_feedback(summary, trigger_type="status_query")
    try:
        await status_msg.delete()
    except Exception:
        pass
    await safe_reply(update, advice)

async def weekly_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status_msg = await update.message.reply_text("📊 正在调取过去 7 天的饮食热量、训练肌群与体重数据生成宏观周报...")
    weekly_data = await get_weekly_report_data(user_id)
    report = await ai_service.generate_weekly_report_summary(weekly_data)
    try:
        await status_msg.delete()
    except Exception:
        pass
    await safe_reply(update, report)

async def show_meal_management(update: Update, user_id: int):
    meals = await get_recent_meals(user_id, limit=6)
    if not meals:
        await safe_reply(update, "📭 你今天还没有记录任何餐食哦，点击 `[🥗 记录餐食]` 或发一张照片开始打卡吧！")
        return

    text = "📋 **最近记录的餐食明细**：\n\n"
    keyboard = []
    for m in meals:
        time_str = f"{m['meal_date'][5:]} {m['meal_time'][:5]}"
        food_short = (m['food_name'][:18] + "..") if len(m['food_name']) > 18 else m['food_name']
        text += (
            f"🔹 **#{m['id']}** [{time_str}] {m['food_name']}\n"
            f"   🔥 {m['calories']:.0f} kcal | 🥩 蛋白: {m['protein']:.1f}g | 🍚 碳水: {m['carbs']:.1f}g | 🥑 脂肪: {m['fat']:.1f}g\n\n"
        )
        keyboard.append([
            InlineKeyboardButton(f"❌ 撤销/删除: #{m['id']} {food_short}", callback_data=f"del_meal_{m['id']}")
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data

    if data.startswith("del_meal_"):
        meal_id = int(data.replace("del_meal_", ""))
        success = await delete_meal(meal_id, user_id)
        if success:
            summary = await get_today_summary(user_id)
            rem = summary["remaining"]
            tot = summary["totals"]
            user = summary["user"]
            msg = (
                f"🗑️ **已成功删除餐食 #{meal_id}！**\n\n"
                f"📊 **今日实时数据更新**：\n"
                f"• 今日已摄入：**{tot['calories']:.0f}** / {user['target_calories']} kcal\n"
                f"• 还需补充：**{rem['calories']:.0f}** kcal\n"
                f"• 蛋白质已摄入：**{tot['protein']:.1f}** / {user['target_protein']} g"
            )
            try:
                await query.edit_message_text(msg, parse_mode="Markdown")
            except Exception:
                await query.edit_message_text(msg)
        else:
            await query.edit_message_text(f"⚠️ 找不到该餐食或已被删除 (ID: #{meal_id})。")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    caption = update.message.caption or ""

    status_msg = await update.message.reply_text("👀 收到食物照片，AI 营养师正在识别成分与计算卡路里...")

    try:
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        analysis = await ai_service.analyze_food_image(bytes(image_bytes), caption)

        items_str = ", ".join([f"{it.name}(~{it.estimated_weight_g or '?'}g)" for it in analysis.items])
        meal_id = await add_meal(
            user_id=user_id,
            food_name=items_str,
            calories=analysis.total_calories,
            protein=analysis.total_protein,
            carbs=analysis.total_carbs,
            fat=analysis.total_fat,
            raw_input=f"[照片] {caption}"
        )
        context.user_data["last_meal_id"] = meal_id

        summary = await get_today_summary(user_id)
        coach_advice = await ai_service.generate_integrated_feedback(
            summary,
            trigger_type="meal",
            item_detail=f"{items_str} (+{analysis.total_calories:.0f}kcal, +{analysis.total_protein:.1f}g蛋白)"
        )

        reply_text = (
            f"🍽️ **【餐食已入库 #{meal_id}】** {items_str}\n"
            f"🔥 本餐：{analysis.total_calories:.0f} kcal (蛋:{analysis.total_protein:.1f}g | 碳:{analysis.total_carbs:.1f}g | 脂:{analysis.total_fat:.1f}g)\n\n"
            f"─────────────────\n"
            f"{coach_advice}\n\n"
            f"💡 *小贴士：如果这顿饭少喝了汤或多吃了肉，直接回复我说（如“汤没喝扣150卡”）即可微调！*"
        )
        inline_kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"❌ 撤销删除这餐 (#{meal_id})", callback_data=f"del_meal_{meal_id}")]])
        try:
            await status_msg.delete()
        except Exception:
            pass
        try:
            await update.message.reply_text(reply_text, parse_mode="Markdown", reply_markup=inline_kb)
        except Exception:
            await update.message.reply_text(reply_text, reply_markup=inline_kb)
    except Exception as e:
        logging.error(f"处理图片失败: {e}", exc_info=True)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(f"❌ 分析照片出错：{str(e)}", reply_markup=REPLY_MARKUP)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    user_data = context.user_data

    # 1. 响应点击底部按钮
    if text == "🥗 记录餐食":
        user_data["awaiting"] = "meal"
        await update.message.reply_text("📸 请直接发一张**食物照片**，或者**打字输入**（例如：`一碗牛肉面加个煎蛋`）：", reply_markup=REPLY_MARKUP)
        return
    elif text == "🏋️ 记录健身":
        user_data["awaiting"] = "workout"
        await update.message.reply_text("💪 请输入今天的训练（例如：`卧推70kg 4组8次，哑铃飞鸟15kg 3组`）：", reply_markup=REPLY_MARKUP)
        return
    elif text == "💧 记录喝水/睡眠":
        user_data["awaiting"] = "habit"
        await update.message.reply_text("💧 请输入喝水量或睡眠情况（例如：`喝水 500ml`、`昨晚睡了 8 小时`）：", reply_markup=REPLY_MARKUP)
        return
    elif text == "📋 查看/管理餐食":
        await show_meal_management(update, user_id)
        return
    elif text == "⚖️ 记录体重":
        user_data["awaiting"] = "body"
        await update.message.reply_text("⚖️ 请输入当前体重和腰围（例如：`空腹 72.5kg，腰围 81cm`）：", reply_markup=REPLY_MARKUP)
        return
    elif text == "📈 每周复盘报告":
        await weekly_cmd(update, context)
        return
    elif text == "⚙️ 设置身材档案":
        user_data["awaiting"] = "profile"
        await update.message.reply_text("📏 请输入你的身材基本信息，我将为你量身定制代谢消耗与目标：\n\n例如直接发送：\n`男，26岁，身高178cm，体重75kg，目标增肌`", reply_markup=REPLY_MARKUP)
        return
    elif text == "📊 今日总览与建议":
        await today_cmd(update, context)
        return

    # 2. 意图判断
    awaiting = user_data.get("awaiting")
    intent = awaiting if awaiting else await ai_service.detect_intent(text)
    user_data["awaiting"] = None

    if intent == "weekly":
        await weekly_cmd(update, context)

    elif intent in ["adjust"]:
        # 微调修改上一餐
        last_meal_id = user_data.get("last_meal_id")
        if not last_meal_id:
            # 取最新的一餐
            recent = await get_recent_meals(user_id, limit=1)
            if recent:
                last_meal_id = recent[0]["id"]

        if not last_meal_id:
            await update.message.reply_text("⚠️ 找不到你最近记录的餐食，请先记录一餐再进行微调。", reply_markup=REPLY_MARKUP)
            return

        status_msg = await update.message.reply_text(f"✏️ 正在为你微调上一餐 (#{last_meal_id}) 的热量与营养数据...")
        try:
            adj = await ai_service.parse_meal_adjustment(text)
            await update_meal(last_meal_id, user_id, calories_delta=adj.calories_delta, protein_delta=adj.protein_delta)
            summary = await get_today_summary(user_id)
            tot = summary["totals"]
            user = summary["user"]
            rem = summary["remaining"]
            msg = (
                f"✅ **餐食 #{last_meal_id} 已成功微调！**\n"
                f"• 调整变动：热量 {adj.calories_delta:+.0f} kcal | 蛋白质 {adj.protein_delta:+.1f} g\n"
                f"• 原因说明：{adj.reason}\n\n"
                f"📊 **今日最新累计**：已吃 {tot['calories']:.0f} / {user['target_calories']} kcal (还差 {rem['calories']:.0f} kcal)\n"
                f"🥩 蛋白质：{tot['protein']:.1f} / {user['target_protein']} g"
            )
            try:
                await status_msg.delete()
            except Exception:
                pass
            await safe_reply(update, msg)
        except Exception as e:
            await update.message.reply_text(f"❌ 微调失败: {e}", reply_markup=REPLY_MARKUP)

    elif intent in ["habit"]:
        status_msg = await update.message.reply_text("💧 正在记录生活习惯与恢复状态...")
        try:
            hab = await ai_service.parse_habit_text(text)
            await record_habit(user_id, water_ml=hab.water_ml, sleep_hours=hab.sleep_hours)
            summary = await get_today_summary(user_id)
            habits = summary["habits"]
            msg = (
                f"✅ **身体恢复状态已更新**：\n"
                f"💧 今日累计饮水：**{habits['water_ml']:.0f}** ml\n"
                f"🛌 昨晚记录睡眠：**{habits['sleep_hours']:.1f}** 小时\n\n"
                f"💡 {hab.feedback}"
            )
            try:
                await status_msg.delete()
            except Exception:
                pass
            await safe_reply(update, msg)
        except Exception as e:
            await update.message.reply_text(f"❌ 记录失败: {e}", reply_markup=REPLY_MARKUP)

    elif intent in ["profile"]:
        status_msg = await update.message.reply_text("📐 正在解析身体指标并根据运动科学公式计算代谢率...")
        try:
            prof = await ai_service.parse_profile_text(text)
            stats = await update_user_profile(
                user_id=user_id,
                gender=prof.gender,
                age=prof.age,
                height=prof.height_cm,
                weight=prof.weight_kg,
                goal=prof.goal
            )
            msg = (
                f"🎉 **身材档案建档成功！**\n\n"
                f"👤 **基本数据**：{prof.gender} | {prof.age}岁 | 身高 {prof.height_cm}cm | 体重 {prof.weight_kg}kg\n"
                f"🎯 **目标定位**：{prof.goal}\n\n"
                f"🔬 **科学代谢测算 (Mifflin-St Jeor)**：\n"
                f"• **基础代谢 (BMR)**：{stats['bmr']} kcal/天 (静息生命维持)\n"
                f"• **日常总消耗 (TDEE)**：{stats['tdee']} kcal/天\n"
                f"• **体质指数 (BMI)**：{stats['bmi']}\n\n"
                f"📋 **为你定制的每日摄入计划**：\n"
                f"🔥 **每日热量预算**：**{stats['target_calories']}** kcal\n"
                f"🥩 **蛋白质目标**：**{stats['target_protein']}** g\n"
                f"🍚 **碳水目标**：{stats['target_carbs']} g\n"
                f"🥑 **脂肪限额**：{stats['target_fat']} g\n\n"
                f"以后每次你记录饮食或锻炼，我都将严格以此科学模型监督你的进度！💪"
            )
            try:
                await status_msg.delete()
            except Exception:
                pass
            await safe_reply(update, msg)
        except Exception as e:
            await update.message.reply_text(f"❌ 档案设置失败: {e}", reply_markup=REPLY_MARKUP)

    elif intent in ["food", "meal"]:
        status_msg = await update.message.reply_text("🥗 AI 正在估算热量并调取今日进度...")
        try:
            analysis = await ai_service.analyze_food_text(text)
            items_str = ", ".join([it.name for it in analysis.items])
            meal_id = await add_meal(
                user_id=user_id,
                food_name=items_str,
                calories=analysis.total_calories,
                protein=analysis.total_protein,
                carbs=analysis.total_carbs,
                fat=analysis.total_fat,
                raw_input=text
            )
            user_data["last_meal_id"] = meal_id

            summary = await get_today_summary(user_id)
            coach_advice = await ai_service.generate_integrated_feedback(
                summary,
                trigger_type="meal",
                item_detail=f"{items_str} (+{analysis.total_calories:.0f}kcal, +{analysis.total_protein:.1f}g蛋白)"
            )

            msg = (
                f"✅ **【餐食已入库 #{meal_id}】** {items_str}\n"
                f"🔥 本餐：{analysis.total_calories:.0f} kcal (蛋:{analysis.total_protein:.1f}g | 碳:{analysis.total_carbs:.1f}g | 脂:{analysis.total_fat:.1f}g)\n\n"
                f"─────────────────\n"
                f"{coach_advice}\n\n"
                f"💡 *小贴士：如需微调（如少喝汤、加了牛肉），直接回发“汤没喝扣150卡”即可自动补正！*"
            )
            inline_kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"❌ 撤销删除这餐 (#{meal_id})", callback_data=f"del_meal_{meal_id}")]])
            try:
                await status_msg.delete()
            except Exception:
                pass
            try:
                await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=inline_kb)
            except Exception:
                await update.message.reply_text(msg, reply_markup=inline_kb)
        except Exception as e:
            await update.message.reply_text(f"❌ 记录失败: {e}", reply_markup=REPLY_MARKUP)

    elif intent in ["workout"]:
        status_msg = await update.message.reply_text("🏋️‍♂️ AI 正在分析训练动作并比对上一次历史负荷...")
        try:
            analysis = await ai_service.analyze_workout_text(text)
            overload_hints = []
            for w in analysis.workouts:
                prev = await get_previous_exercise_record(user_id, w.name)
                if prev and prev.get("weight") is not None:
                    diff_w = (w.weight_kg or 0) - (prev["weight"] or 0)
                    sign = "+" if diff_w >= 0 else ""
                    overload_hints.append(f"{w.name}: 上次是 {prev['weight']}kg，本次是 {w.weight_kg}kg ({sign}{diff_w}kg)")

                await add_workout(
                    user_id=user_id,
                    exercise_name=w.name,
                    muscle_group=w.muscle_group,
                    sets=w.sets,
                    reps=w.reps,
                    weight=w.weight_kg,
                    calories_burned=w.estimated_calories_burned,
                    raw_input=text
                )

            items_desc = ", ".join([f"{w.name}({w.muscle_group})" for w in analysis.workouts])
            overload_str = " | ".join(overload_hints) if overload_hints else "首次动作记录"

            summary = await get_today_summary(user_id)
            coach_advice = await ai_service.generate_integrated_feedback(
                summary,
                trigger_type="workout",
                item_detail=f"{items_desc} (消耗~{analysis.total_calories_burned:.0f}kcal)",
                overload_hint=overload_str
            )

            msg = (
                f"💪 **【训练已入库】**\n"
                + "\n".join([f"• {w.name} [{w.muscle_group}]: {w.sets}组 x {w.reps}次 @ {w.weight_kg}kg" for w in analysis.workouts]) +
                f"\n🔥 预估消耗：约 {analysis.total_calories_burned:.0f} kcal\n"
                + (f"📈 **渐进负荷对比**：{overload_str}\n" if overload_hints else "") +
                f"\n─────────────────\n"
                f"{coach_advice}"
            )
            try:
                await status_msg.delete()
            except Exception:
                pass
            await safe_reply(update, msg)
        except Exception as e:
            await update.message.reply_text(f"❌ 记录失败: {e}", reply_markup=REPLY_MARKUP)

    elif intent in ["body"]:
        status_msg = await update.message.reply_text("⚖️ 正在更新身体数据并比对趋势...")
        try:
            analysis = await ai_service.analyze_body_text(text)
            await add_body_metric(
                user_id=user_id,
                weight=analysis.weight_kg,
                waist=analysis.waist_cm,
                notes=text
            )

            summary = await get_today_summary(user_id)
            coach_advice = await ai_service.generate_integrated_feedback(
                summary,
                trigger_type="body",
                item_detail=f"体重 {analysis.weight_kg}kg" + (f"，腰围 {analysis.waist_cm}cm" if analysis.waist_cm else "")
            )

            waist_str = f" | 腰围: {analysis.waist_cm}cm" if analysis.waist_cm else ""
            msg = (
                f"⚖️ **【身材指标已入库】** {analysis.weight_kg} kg{waist_str}\n\n"
                f"─────────────────\n"
                f"{coach_advice}"
            )
            try:
                await status_msg.delete()
            except Exception:
                pass
            await safe_reply(update, msg)
        except Exception as e:
            await update.message.reply_text(f"❌ 记录失败: {e}", reply_markup=REPLY_MARKUP)

    else:
        summary = await get_today_summary(user_id)
        reply = await ai_service.generate_integrated_feedback(summary, trigger_type="status_query", item_detail=text)
        await safe_reply(update, reply)

# ================= 主动饮食与教练督促调度机制 =================
async def send_meal_reminder_to_all(context: ContextTypes.DEFAULT_TYPE, meal_type: str):
    """向所有用户推送个性化定点就餐提醒"""
    user_ids = await get_all_user_ids()
    for uid in user_ids:
        try:
            summary = await get_today_summary(uid)
            reminder_text = await ai_service.generate_meal_reminder(meal_type, summary)
            await context.bot.send_message(
                chat_id=uid,
                text=reminder_text,
                reply_markup=REPLY_MARKUP
            )
        except Exception as e:
            logging.error(f"发送【{meal_type}】提醒失败 uid {uid}: {e}")

async def breakfast_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    await send_meal_reminder_to_all(context, "早餐")

async def lunch_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    await send_meal_reminder_to_all(context, "午餐")

async def dinner_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    await send_meal_reminder_to_all(context, "晚餐")

async def evening_checkup_job(context: ContextTypes.DEFAULT_TYPE):
    """每天晚上 21:00 自动执行：主动扫描用户今日打卡，未完成则督促！"""
    user_ids = await get_all_user_ids()
    for uid in user_ids:
        try:
            summary = await get_today_summary(uid)
            meals = summary["meals"]
            workouts = summary["workouts"]
            rem = summary["remaining"]
            user = summary["user"]

            alerts = []
            if not workouts:
                alerts.append("🏋️ **你今天还没有记录运动！** 晚上抽空做一组或练一组核心拉伸吗？")
            if rem["calories"] > 500:
                alerts.append(f"🥩 **今天的增肌/能量目标还差 {rem['calories']:.0f} kcal**，蛋白质还差 {rem['protein']:.1f}g，睡前建议补充一杯蛋白粉或两颗鸡蛋！")

            if alerts:
                text = (
                    f"⏰ **来自私人教练的晚间例行查房**：\n\n"
                    + "\n\n".join(alerts) +
                    f"\n\n点击 `[📊 今日总览与建议]` 可查看当前全天战报。早点休息，明天继续冲！💪"
                )
                await context.bot.send_message(chat_id=uid, text=text, parse_mode="Markdown", reply_markup=REPLY_MARKUP)
        except Exception as e:
            logging.error(f"发送晚间提醒失败 uid {uid}: {e}")

from aiohttp import web

async def health_check(request):
    return web.Response(text="OK - FitCheck Bot is running healthy and active!", content_type="text/plain")

async def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Health-check Web Service listening on port {port} (Render Free Tier Ready)")

async def main_async():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    await init_db()

    # 启动健康检查 Web 服务，兼容 Render 免费 Web Service
    await run_web_server()

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("weekly", weekly_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    # 配置每日固定就餐与督促定时调度（支持北京时间 Asia/Shanghai）
    job_queue = app.job_queue
    if job_queue:
        shanghai_tz = ZoneInfo("Asia/Shanghai")
        # 1. 早餐提醒 (08:30)
        job_queue.run_daily(breakfast_reminder_job, time=time(hour=8, minute=30, tzinfo=shanghai_tz))
        # 2. 午餐提醒 (12:00)
        job_queue.run_daily(lunch_reminder_job, time=time(hour=12, minute=0, tzinfo=shanghai_tz))
        # 3. 晚餐提醒 (18:30)
        job_queue.run_daily(dinner_reminder_job, time=time(hour=18, minute=30, tzinfo=shanghai_tz))
        # 4. 晚间查房督促 (21:00)
        job_queue.run_daily(evening_checkup_job, time=time(hour=21, minute=0, tzinfo=shanghai_tz))

    print("🚀 FitCheck Telegram Bot & 饮食主动提醒已全面启动！")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # 保持长久运行
    import asyncio
    while True:
        await asyncio.sleep(3600)

def main():
    import asyncio
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
