import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from database import init_db, add_meal, add_workout, add_body_metric, get_today_summary
import ai_service

async def test_workflow():
    print("=== 1. 初始化数据库 ===")
    await init_db()
    user_id = 123456

    print("\n=== 2. 测试食物解析（模拟用户输入：'中午吃了番茄牛腩饭，加了一个煎蛋'）===")
    food_text = "中午吃了番茄牛腩饭，加了一个煎蛋"
    intent = await ai_service.detect_intent(food_text)
    print(f"意图识别结果: {intent}")
    food_analysis = await ai_service.analyze_food_text(food_text)
    print(f"识别菜品: {[i.name for i in food_analysis.items]}")
    print(f"营养数据: {food_analysis.total_calories} kcal (蛋白质:{food_analysis.total_protein}g, 碳水:{food_analysis.total_carbs}g, 脂肪:{food_analysis.total_fat}g)")
    print(f"点评建议: {food_analysis.brief_advice}")
    await add_meal(user_id, "番茄牛腩饭加煎蛋", food_analysis.total_calories, food_analysis.total_protein, food_analysis.total_carbs, food_analysis.total_fat, food_text)

    print("\n=== 3. 测试训练记录（模拟用户输入：'今天胸部训练：平板卧推70kg做了4组8次，上斜哑铃飞鸟15kg做了3组'）===")
    workout_text = "今天胸部训练：平板卧推70kg做了4组8次，上斜哑铃飞鸟15kg做了3组"
    intent = await ai_service.detect_intent(workout_text)
    print(f"意图识别结果: {intent}")
    workout_analysis = await ai_service.analyze_workout_text(workout_text)
    for w in workout_analysis.workouts:
        print(f"动作: {w.name} | 组数: {w.sets} | 次数: {w.reps} | 重量: {w.weight_kg}kg | 预估消耗: {w.estimated_calories_burned}kcal")
        await add_workout(user_id, w.name, w.sets, w.reps, w.weight_kg, w.estimated_calories_burned, workout_text)
    print(f"教练反馈: {workout_analysis.brief_feedback}")

    print("\n=== 4. 测试身材记录（模拟用户输入：'早上空腹体重 73.2kg，腰围 82cm'）===")
    body_text = "早上空腹体重 73.2kg，腰围 82cm"
    body_analysis = await ai_service.analyze_body_text(body_text)
    print(f"解析身材: 体重={body_analysis.weight_kg}kg, 腰围={body_analysis.waist_cm}cm")
    await add_body_metric(user_id, body_analysis.weight_kg, body_analysis.waist_cm, body_text)

    print("\n=== 5. 生成今日智能教练综合建议 ===")
    summary = await get_today_summary(user_id)
    advice = await ai_service.generate_coach_advice(summary, user_question="我今晚如果想减脂，晚餐还能吃什么？")
    print("【AI 教练诊断与建议】：")
    print(advice)

if __name__ == "__main__":
    asyncio.run(test_workflow())

