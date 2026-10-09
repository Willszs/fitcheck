import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional, List

class ProfileAnalysis(BaseModel):
    gender: str = Field(default="男", description="性别：男 或 女")
    age: int = Field(default=25, description="年龄")
    height_cm: float = Field(default=175.0, description="身高(cm)")
    weight_kg: float = Field(default=70.0, description="当前体重(kg)")
    goal: str = Field(default="增肌", description="目标：减脂、增肌、或维持")

class FoodItem(BaseModel):
    name: str = Field(description="食物名称")
    estimated_weight_g: Optional[float] = Field(description="估计重量(克)")
    calories: float = Field(description="热量(千卡 kcal)")
    protein: float = Field(description="蛋白质(克)")
    carbs: float = Field(description="碳水化合物(克)")
    fat: float = Field(description="脂肪(克)")

class NutritionAnalysis(BaseModel):
    items: List[FoodItem] = Field(description="识别出的食物列表")
    total_calories: float = Field(description="总热量(kcal)")
    total_protein: float = Field(description="总蛋白质(g)")
    total_carbs: float = Field(description="总碳水(g)")
    total_fat: float = Field(description="总脂肪(g)")
    brief_advice: str = Field(description="针对这顿饭的一句话营养点评或健康建议")

class MealAdjustment(BaseModel):
    calories_delta: float = Field(description="热量变动(大卡，如扣除150大卡填-150，增加填正数)")
    protein_delta: float = Field(description="蛋白质变动(克，如多吃15g蛋白填15，减少填负数)")
    reason: str = Field(description="微调的简短说明")

class WorkoutItem(BaseModel):
    name: str = Field(description="动作名称，如平板卧推、高位下拉、深蹲、慢跑")
    muscle_group: str = Field(description="锻炼的主要部位，如：胸部、背部、腿部、肩部、手臂、核心、有氧")
    sets: Optional[int] = Field(default=1, description="组数")
    reps: Optional[int] = Field(default=0, description="每组次数")
    weight_kg: Optional[float] = Field(default=0.0, description="负重(kg)")
    estimated_calories_burned: Optional[float] = Field(default=0.0, description="预估消耗热量(kcal)")

class WorkoutAnalysis(BaseModel):
    workouts: List[WorkoutItem] = Field(description="健身/运动动作列表")
    total_calories_burned: float = Field(description="总估算消耗热量(kcal)")
    brief_feedback: str = Field(description="针对此次训练的一句话教练鼓励或建议")

class HabitAnalysis(BaseModel):
    water_ml: Optional[float] = Field(default=None, description="本次喝水量(毫升 ml)")
    sleep_hours: Optional[float] = Field(default=None, description="昨晚睡眠时长(小时)")
    feedback: str = Field(description="教练对水或睡眠的简要反馈")

class BodyAnalysis(BaseModel):
    weight_kg: float = Field(description="体重(kg)")
    waist_cm: Optional[float] = Field(default=None, description="腰围(cm)")
    brief_comment: str = Field(description="对当前体重或变化的简要反馈")

class IntentDetection(BaseModel):
    intent: str = Field(description="分类: 'profile' (身材档案), 'habit' (喝水或睡眠), 'adjust' (微调上一餐数据), 'food' (饮食), 'workout' (健身运动), 'body' (体重身材), 'weekly' (周报), 'query' (查询或求建议), 'other' (其他)")

def get_ai_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

SYSTEM_PROMPT = """你是一位持有 NSCA-CSCS (体能训练专家) 与注册营养师资质的顶级私人教练。
你的风格：极度专业、干脆利落、富有人性化动力。
你必须基于用户实际的身高、体重、代谢率（BMR/TDEE）、渐进超负荷历史和真实打卡事实说话，给出精确的量化建议。"""

async def detect_intent(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["周报", "这周", "本周", "每周", "weekly"]):
        return "weekly"
    if any(w in text_lower for w in ["喝水", "饮水", "ml", "毫升", "睡觉", "睡了", "失眠", "醒来"]):
        return "habit"
    if any(w in text_lower for w in ["扣除", "多吃", "少吃", "没喝", "没吃", "加了", "微调", "修改刚才"]):
        return "adjust"
    if any(w in text_lower for w in ["身高", "年龄", "岁", "cm", "公分", "档案", "建档", "增肌还是减脂", "想增肌", "想减脂"]):
        return "profile"
    if any(w in text_lower for w in ["吃", "喝", "饭", "卡路里", "早饭", "午饭", "晚饭", "餐", "点心", "奶茶", "零食", "肉", "菜"]):
        return "food"
    if any(w in text_lower for w in ["练", "跑", "组", "卧推", "深蹲", "硬拉", "哑铃", "健身", "运动", "俯卧撑", "引体", "有氧"]):
        return "workout"
    if any(w in text_lower for w in ["重", "kg", "斤", "腰围", "体脂"]):
        return "body"

    client = get_ai_client()
    if not client:
        return "query"

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=f"判断用户的输入意图：\n{text}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=IntentDetection,
                temperature=0.1
            ),
        )
        data = json.loads(response.text)
        return data.get("intent", "other")
    except Exception:
        return "query"

async def parse_profile_text(text: str) -> ProfileAnalysis:
    client = get_ai_client()
    if not client:
        return ProfileAnalysis(gender="男", age=25, height_cm=175.0, weight_kg=72.0, goal="增肌")

    prompt = f"提取用户身体档案：性别(男/女)、年龄、身高(cm)、当前体重(kg，若输入斤请自动折算为kg)、目标(减脂/增肌/维持)：\n{text}"
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ProfileAnalysis,
            temperature=0.1
        )
    )
    return ProfileAnalysis.model_validate_json(response.text)

async def parse_habit_text(text: str) -> HabitAnalysis:
    """提取喝水（ml）或睡眠（小时）数据"""
    client = get_ai_client()
    if not client:
        return HabitAnalysis(water_ml=500, sleep_hours=None, feedback="水分已补充！")

    prompt = f"提取用户记录的喝水量(ml)或睡眠时长(小时)，并给出专业简短评价：\n{text}"
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=HabitAnalysis,
            system_instruction="你负责提取喝水量和睡眠数据。如果是比如两瓶水，可按1000ml折算。",
            temperature=0.1
        )
    )
    return HabitAnalysis.model_validate_json(response.text)

async def parse_meal_adjustment(text: str) -> MealAdjustment:
    """根据用户的自然语言（如：汤没喝扣除150大卡，或者牛肉吃了双份加15g蛋白）计算热量和蛋白补正"""
    client = get_ai_client()
    if not client:
        return MealAdjustment(calories_delta=-150, protein_delta=0, reason="微调修正")

    prompt = f"根据用户对刚才餐食的调整修正，估算需要增减的热量(kcal，减少填负数)和蛋白质(g)：\n{text}"
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=MealAdjustment,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1
        )
    )
    return MealAdjustment.model_validate_json(response.text)

async def analyze_food_text(text: str) -> NutritionAnalysis:
    client = get_ai_client()
    if not client:
        return NutritionAnalysis(
            items=[FoodItem(name=text, estimated_weight_g=200, calories=400, protein=25, carbs=45, fat=12)],
            total_calories=400,
            total_protein=25,
            total_carbs=45,
            total_fat=12,
            brief_advice="饮食已记录，注意补充水分与膳食纤维。"
        )

    prompt = f"请精确拆解以下饮食的食物组成、单项克数、热量(kcal)和三大宏量营养素(蛋白/碳水/脂肪)：\n{text}"
    candidate_models = ['gemini-3.1-flash-lite', 'gemini-3.5-flash-lite', 'gemini-flash-latest']
    
    last_err = None
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=NutritionAnalysis,
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2
                )
            )
            return NutritionAnalysis.model_validate_json(response.text)
        except Exception as e:
            last_err = e
            continue
    raise last_err

async def analyze_food_image(image_bytes: bytes, caption: Optional[str] = None) -> NutritionAnalysis:
    client = get_ai_client()
    if not client:
        return NutritionAnalysis(
            items=[FoodItem(name="照片中食物", estimated_weight_g=300, calories=500, protein=30, carbs=50, fat=15)],
            total_calories=500,
            total_protein=30,
            total_carbs=50,
            total_fat=15,
            brief_advice="照片已解析，能量配比基本均衡。"
        )

    prompt = "请仔细识别照片中的每种食物，结合餐盘比例估算重量(g)、热量(kcal)、蛋白质、碳水和脂肪。"
    if caption:
        prompt += f"\n用户补充说明: {caption}"

    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
    candidate_models = ['gemini-3.1-flash-lite', 'gemini-3.5-flash-lite', 'gemini-flash-latest']

    last_err = None
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=NutritionAnalysis,
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2
                )
            )
            return NutritionAnalysis.model_validate_json(response.text)
        except Exception as e:
            last_err = e
            continue
    raise last_err

async def analyze_workout_text(text: str) -> WorkoutAnalysis:
    client = get_ai_client()
    if not client:
        return WorkoutAnalysis(
            workouts=[WorkoutItem(name=text, muscle_group="综合", sets=3, reps=10, weight_kg=20, estimated_calories_burned=150)],
            total_calories_burned=150,
            brief_feedback="训练已记录，干得漂亮！"
        )

    prompt = f"请解析用户的健身运动记录，识别每个动作、归属部位（胸部/背部/腿部/肩部/手臂/核心/有氧）、组数、次数、负重(kg)，并计算预估消耗热量：\n{text}"
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=WorkoutAnalysis,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2
        )
    )
    return WorkoutAnalysis.model_validate_json(response.text)

async def analyze_body_text(text: str) -> BodyAnalysis:
    client = get_ai_client()
    if not client:
        import re
        match = re.search(r"(\d+(\.\d+)?)", text)
        w = float(match.group(1)) if match else 70.0
        return BodyAnalysis(weight_kg=w, waist_cm=None, brief_comment="体重数据已记录。")

    prompt = f"提取用户的体重(kg，若是斤请折算为kg)与腰围(cm)：\n{text}"
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BodyAnalysis,
            system_instruction="你负责准确提取身体数据。1斤=0.5kg。",
            temperature=0.1
        )
    )
    return BodyAnalysis.model_validate_json(response.text)

async def generate_integrated_feedback(summary: dict, trigger_type: str, item_detail: str = "", overload_hint: str = "") -> str:
    client = get_ai_client()
    user = summary["user"]
    totals = summary["totals"]
    rem = summary["remaining"]
    meals = summary["meals"]
    workouts = summary["workouts"]
    recent_w = summary["recent_workouts"]
    latest_body = summary["latest_body"]
    prev_body = summary["prev_body"]
    habits = summary.get("habits", {})
    current_bmi = summary.get("current_bmi", 22.0)

    today_muscles = list(set([w["muscle_group"] for w in workouts]))
    recent_muscles = [f"{rw['day']}:{rw['muscle_group']}" for rw in recent_w[:10]]

    weight_trend = "暂无对比"
    if latest_body:
        weight_trend = f"当前 {latest_body['weight']}kg"
        if prev_body:
            diff = latest_body['weight'] - prev_body['weight']
            weight_trend += f"（比上次 {prev_body['weight']}kg {'+' if diff>=0 else ''}{diff:.2f}kg）"

    habits_text = f"今日已饮水: {habits.get('water_ml', 0)}ml | 睡眠记录: {habits.get('sleep_hours', 0)}小时"

    prompt = f"""
【用户档案与目标】：
- 身高: {user.get('height', 175)}cm | 体重: {latest_body['weight'] if latest_body else '70'}kg | BMI: {current_bmi}
- 设定目标: {user['goal']} (每日热量预算: {user['target_calories']} kcal, 目标蛋白质: {user['target_protein']}g)
- 基础代谢 (BMR): {user.get('bmr', 1700)} kcal | 每日总消耗 (TDEE): {user.get('tdee', 2300)} kcal

【今日实时状态】：
- 今日摄入：{totals['calories']} / {user['target_calories']} kcal (还差 {rem['calories']} kcal)
- 今日蛋白质：{totals['protein']} / {user['target_protein']} g (还差 {rem['protein']} g)
- 今日训练：{len(workouts)}个动作，涉及部位：{today_muscles or '今日尚未锻炼！'}
- 今日运动消耗：约 {totals['calories_burned']} kcal
- 最近7天部位历史：{recent_muscles or '无'}
- 体重趋势：{weight_trend}
- 生活恢复：{habits_text}
{f"- 渐进负荷历史比对: {overload_hint}" if overload_hint else ""}

【本次触发】：{trigger_type}，记录内容：{item_detail}

【教练要求】：
1. 给出今日预算与营养缺口反馈（对于增肌，强调吃足热量和蛋白质；对于减脂，控制缺口）。
2. 如果触发了健身训练且有渐进负荷比对，必须重点评价他的力量增长（是否涨力量了、下次该冲多重）。
3. 如果今天还没锻炼，严厉且有动力地催练，并直接指定今天练什么部位。
4. 结合补水和睡眠做恢复提醒。
"""
    if not client:
        return f"今日摄入：{totals['calories']} / {user['target_calories']} kcal (差 {rem['calories']})。锻炼：{today_muscles or '未锻炼'}。"

    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3
        )
    )
    return response.text

async def generate_weekly_report_summary(weekly_data: dict) -> str:
    """生成专业的每周训练与营养周期复盘报告"""
    client = get_ai_client()
    user = weekly_data["user"]
    daily_intakes = weekly_data["daily_intakes"]
    muscle_dist = weekly_data["muscle_dist"]
    weights = weekly_data["weight_history"]

    intakes_text = "\n".join([f"- {d['day']}: {d['total_cal']:.0f}kcal (蛋白: {d['total_p']:.1f}g)" for d in daily_intakes]) or "无记录"
    dist_text = "\n".join([f"- {m['muscle_group']}: 共 {m['count']} 个动作" for m in muscle_dist]) or "无锻炼记录"
    weights_text = " -> ".join([f"{w['weight']}kg({w['day'][5:]})" for w in weights]) or "无体重记录"

    prompt = f"""
用户过去 7 天的完整健康数据：
【用户目标】：{user['goal']} (每日预算 {user['target_calories']}kcal, 目标蛋白 {user['target_protein']}g)

【过去7天饮食摄入】：
{intakes_text}

【过去7天肌群训练分布】：
{dist_text}

【过去7天体重轨迹】：
{weights_text}

请作为顶级总教练，为用户写一份深度周报：
1. 【热量与蛋白质达标率】：评估这周是否有足够的能量盈余（增肌）或赤字（减脂），蛋白质是否达标。
2. 【肌群均衡度诊断】：指出哪些部位练得多，哪些部位被忽略了（如是否逃避练腿、背部是否充足）。
3. 【下周作战计划调整】：根据本周表现，给出下周的训练重点和饮食改进指令。
排版清晰、极具专业范儿！
"""
    if not client:
        return "过去一周数据已生成，继续坚持规律训练与高蛋白饮食！"

    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3
        )
    )
    return response.text

async def generate_meal_reminder(meal_type: str, summary: dict) -> str:
    """根据餐别（早/午/晚/加餐）与当前已吃数据，由 AI 生成懂你的个性化点餐/吃餐建议"""
    client = get_ai_client()
    user = summary["user"]
    totals = summary["totals"]
    rem = summary["remaining"]
    goal = user.get("goal", "增肌")
    
    prompt = f"""
用户档案：目标={goal}，每日热量预算={user['target_calories']} kcal，目标蛋白={user['target_protein']} g。
当前时间点餐别：【{meal_type}】
今天截至目前已摄入：{totals['calories']} kcal (还剩预算 {rem['calories']} kcal)，已摄入蛋白质 {totals['protein']} g (还差 {rem['protein']} g)。

请扮演顶级贴身私人营养教练，给用户发一条【{meal_type}】就餐提醒与点单/做饭建议：
1. 亲切提醒他该吃【{meal_type}】了，别忘了拍食物照片或打字发给机器人记录。
2. 结合他今天还剩的热量和蛋白质预算（特别是增肌需要充足热量和优质蛋白质），给出一套具体的、容易买到或烹饪的食物组合建议（如主食选什么、蛋白质选什么、蔬菜选什么）。
3. 如果是早餐提醒补充水分；如果是午餐提醒吃饱；如果是晚餐提醒碳水和脂肪控制；如果是夜宵/加餐提醒睡前慢消化蛋白（酪蛋白/水煮蛋/希腊酸奶）。
字数在 150 字以内，精炼、富有动力，善用 emoji。
"""
    if not client:
        return f"⏰ 该吃{meal_type}啦！今天还需摄入约 {rem['calories']} kcal 热量和 {rem['protein']}g 蛋白质，吃完记得拍照发给我记录哦！"

    candidate_models = ['gemini-3.1-flash-lite', 'gemini-3.5-flash-lite', 'gemini-flash-latest']
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.3
                )
            )
            return response.text
        except Exception:
            continue
    return f"⏰ 该吃{meal_type}啦！今天还剩 {rem['calories']} kcal 预算，记得吃完拍照发我哦！"
