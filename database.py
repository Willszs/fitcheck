import aiosqlite
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "foodtrack.db")

def calculate_metabolism(gender: str, age: int, height: float, weight: float, goal: str = "增肌", activity_factor: float = 1.375):
    is_female = "女" in gender or gender.lower() in ["female", "f", "woman"]
    if is_female:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age + 5

    tdee = bmr * activity_factor
    goal_lower = goal.lower()
    if "增肌" in goal_lower:
        target_calories = round(tdee + 350)
        protein_g = round(weight * 2.0)
    elif "维持" in goal_lower:
        target_calories = round(tdee)
        protein_g = round(weight * 1.6)
    else:
        target_calories = max(round(tdee - 450), round(bmr * 1.05))
        protein_g = round(weight * 2.0)

    fat_g = round((target_calories * 0.25) / 9)
    remaining_cal = target_calories - (protein_g * 4) - (fat_g * 9)
    carbs_g = max(round(remaining_cal / 4), 50)

    height_m = height / 100.0
    bmi = round(weight / (height_m * height_m), 1)

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "bmi": bmi,
        "target_calories": target_calories,
        "target_protein": protein_g,
        "target_carbs": carbs_g,
        "target_fat": fat_g
    }

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                target_calories INTEGER DEFAULT 2400,
                target_protein INTEGER DEFAULT 140,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                target_carbs INTEGER DEFAULT 260,
                target_fat INTEGER DEFAULT 60,
                goal TEXT DEFAULT '增肌',
                gender TEXT DEFAULT '男',
                age INTEGER DEFAULT 25,
                height REAL DEFAULT 175,
                activity_level REAL DEFAULT 1.375,
                bmr REAL DEFAULT 1700,
                tdee REAL DEFAULT 2300
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                food_name TEXT,
                calories REAL,
                protein REAL,
                carbs REAL,
                fat REAL,
                raw_input TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                exercise_name TEXT,
                muscle_group TEXT DEFAULT '综合',
                sets INTEGER,
                reps INTEGER,
                weight REAL,
                calories_burned REAL,
                raw_input TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS body_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                weight REAL,
                waist REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                water_ml REAL DEFAULT 0,
                sleep_hours REAL DEFAULT 0,
                day TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, day)
            )
        """)
        await db.commit()

async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            return [row[0] for row in await cursor.fetchall()]

async def get_or_create_user(user_id: int, username: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
        await db.execute(
            """INSERT INTO users 
               (user_id, username, gender, age, height, target_calories, target_protein, target_carbs, target_fat, goal, bmr, tdee) 
               VALUES (?, ?, '男', 25, 175, 2480, 140, 260, 60, '增肌', 1700, 2300)""",
            (user_id, username)
        )
        await db.commit()
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return dict(await cursor.fetchone())

async def update_user_profile(user_id: int, gender: str, age: int, height: float, weight: float, goal: str):
    stats = calculate_metabolism(gender, age, height, weight, goal)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET 
                gender = ?, age = ?, height = ?, goal = ?,
                bmr = ?, tdee = ?,
                target_calories = ?, target_protein = ?, target_carbs = ?, target_fat = ?
            WHERE user_id = ?
        """, (
            gender, age, height, goal,
            stats["bmr"], stats["tdee"],
            stats["target_calories"], stats["target_protein"], stats["target_carbs"], stats["target_fat"],
            user_id
        ))
        await db.execute(
            "INSERT INTO body_metrics (user_id, weight, notes) VALUES (?, ?, '档案初始化体重')",
            (user_id, weight)
        )
        await db.commit()
    return stats

async def add_meal(user_id: int, food_name: str, calories: float, protein: float, carbs: float, fat: float, raw_input: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO meals (user_id, food_name, calories, protein, carbs, fat, raw_input) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, food_name, calories, protein, carbs, fat, raw_input)
        )
        await db.commit()
        return cursor.lastrowid

async def update_meal(meal_id: int, user_id: int, calories_delta: float, protein_delta: float, new_name: str = None) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM meals WHERE id = ? AND user_id = ?", (meal_id, user_id)) as cursor:
            m = await cursor.fetchone()
            if not m:
                return False
            new_cal = max(round(m["calories"] + calories_delta, 1), 0)
            new_p = max(round(m["protein"] + protein_delta, 1), 0)
            name = new_name or m["food_name"]
            await db.execute(
                "UPDATE meals SET calories = ?, protein = ?, food_name = ? WHERE id = ? AND user_id = ?",
                (new_cal, new_p, name, meal_id, user_id)
            )
            await db.commit()
            return True

async def delete_meal(meal_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM meals WHERE id = ? AND user_id = ?", (meal_id, user_id))
        await db.commit()
        return cursor.rowcount > 0

async def get_recent_meals(user_id: int, limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, food_name, calories, protein, carbs, fat, time(created_at, 'localtime') as meal_time, date(created_at, 'localtime') as meal_date FROM meals WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

async def add_workout(user_id: int, exercise_name: str, muscle_group: str, sets: int, reps: int, weight: float, calories_burned: float, raw_input: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO workouts (user_id, exercise_name, muscle_group, sets, reps, weight, calories_burned, raw_input) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, exercise_name, muscle_group, sets, reps, weight, calories_burned, raw_input)
        )
        await db.commit()

async def get_previous_exercise_record(user_id: int, exercise_name: str):
    """查询该动作的上一次训练记录（用于渐进超负荷比对）"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # 模糊匹配动作关键词
        async with db.execute(
            """SELECT exercise_name, weight, sets, reps, date(created_at, 'localtime') as day 
               FROM workouts 
               WHERE user_id = ? AND (exercise_name LIKE ? OR ? LIKE '%' || exercise_name || '%')
               ORDER BY id DESC LIMIT 1 OFFSET 1""",
            (user_id, f"%{exercise_name}%", exercise_name)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def add_body_metric(user_id: int, weight: float, waist: float = None, notes: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO body_metrics (user_id, weight, waist, notes) VALUES (?, ?, ?, ?)",
            (user_id, weight, waist, notes)
        )
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                user = dict(user)
                stats = calculate_metabolism(user["gender"], user["age"], user["height"], weight, user["goal"])
                await db.execute("""
                    UPDATE users SET 
                        bmr = ?, tdee = ?,
                        target_calories = ?, target_protein = ?, target_carbs = ?, target_fat = ?
                    WHERE user_id = ?
                """, (
                    stats["bmr"], stats["tdee"],
                    stats["target_calories"], stats["target_protein"], stats["target_carbs"], stats["target_fat"],
                    user_id
                ))
        await db.commit()

async def record_habit(user_id: int, water_ml: float = None, sleep_hours: float = None):
    """记录喝水或睡眠"""
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM daily_habits WHERE user_id = ? AND day = ?", (user_id, today)) as cursor:
            row = await cursor.fetchone()
            if row:
                row_dict = dict(row)
                new_water = (row_dict["water_ml"] or 0) + (water_ml or 0)
                new_sleep = sleep_hours if sleep_hours is not None else row_dict["sleep_hours"]
                await db.execute(
                    "UPDATE daily_habits SET water_ml = ?, sleep_hours = ? WHERE user_id = ? AND day = ?",
                    (new_water, new_sleep, user_id, today)
                )
            else:
                await db.execute(
                    "INSERT INTO daily_habits (user_id, water_ml, sleep_hours, day) VALUES (?, ?, ?, ?)",
                    (user_id, water_ml or 0, sleep_hours or 0, today)
                )
        await db.commit()

async def get_today_summary(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    user = await get_or_create_user(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, food_name, calories, protein, carbs, fat FROM meals WHERE user_id = ? AND date(created_at, 'localtime') = ? ORDER BY id DESC",
            (user_id, today)
        ) as cursor:
            meals = [dict(r) for r in await cursor.fetchall()]

        async with db.execute(
            "SELECT exercise_name, muscle_group, sets, reps, weight, calories_burned FROM workouts WHERE user_id = ? AND date(created_at, 'localtime') = ?",
            (user_id, today)
        ) as cursor:
            workouts = [dict(r) for r in await cursor.fetchall()]

        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        async with db.execute(
            "SELECT exercise_name, muscle_group, date(created_at, 'localtime') as day FROM workouts WHERE user_id = ? AND date(created_at, 'localtime') >= ? ORDER BY id DESC",
            (user_id, week_ago)
        ) as cursor:
            recent_workouts = [dict(r) for r in await cursor.fetchall()]

        async with db.execute(
            "SELECT weight, waist, date(created_at, 'localtime') as day FROM body_metrics WHERE user_id = ? ORDER BY id DESC LIMIT 2",
            (user_id,)
        ) as cursor:
            body_records = [dict(r) for r in await cursor.fetchall()]

        # 今日习惯数据
        async with db.execute("SELECT * FROM daily_habits WHERE user_id = ? AND day = ?", (user_id, today)) as cursor:
            habit_row = await cursor.fetchone()
            habits = dict(habit_row) if habit_row else {"water_ml": 0, "sleep_hours": 0}

        latest_body = body_records[0] if body_records else None
        prev_body = body_records[1] if len(body_records) > 1 else None

        current_weight = latest_body["weight"] if latest_body else 70.0
        height_m = (user.get("height") or 175) / 100.0
        current_bmi = round(current_weight / (height_m * height_m), 1)

        total_cal = sum(m["calories"] for m in meals)
        total_p = sum(m["protein"] for m in meals)
        total_c = sum(m["carbs"] for m in meals)
        total_f = sum(m["fat"] for m in meals)
        total_cal_burned = sum(w["calories_burned"] for w in workouts)

        return {
            "user": user,
            "current_bmi": current_bmi,
            "meals": meals,
            "workouts": workouts,
            "recent_workouts": recent_workouts,
            "latest_body": latest_body,
            "prev_body": prev_body,
            "habits": habits,
            "totals": {
                "calories": round(total_cal, 1),
                "protein": round(total_p, 1),
                "carbs": round(total_c, 1),
                "fat": round(total_f, 1),
                "calories_burned": round(total_cal_burned, 1)
            },
            "remaining": {
                "calories": round(user["target_calories"] - total_cal, 1),
                "protein": round(user["target_protein"] - total_p, 1),
                "carbs": round(user["target_carbs"] - total_c, 1),
                "fat": round(user["target_fat"] - total_f, 1)
            }
        }

async def get_weekly_report_data(user_id: int):
    """获取过去7天的宏观统计数据（平均摄入、训练分布、体重平滑）"""
    user = await get_or_create_user(user_id)
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # 每日摄入聚合
        async with db.execute(
            """SELECT date(created_at, 'localtime') as day, 
                      SUM(calories) as total_cal, SUM(protein) as total_p 
               FROM meals 
               WHERE user_id = ? AND date(created_at, 'localtime') >= ?
               GROUP BY date(created_at, 'localtime')""",
            (user_id, week_ago)
        ) as cursor:
            daily_intakes = [dict(r) for r in await cursor.fetchall()]

        # 锻炼分布聚合
        async with db.execute(
            """SELECT muscle_group, COUNT(*) as count 
               FROM workouts 
               WHERE user_id = ? AND date(created_at, 'localtime') >= ?
               GROUP BY muscle_group""",
            (user_id, week_ago)
        ) as cursor:
            muscle_dist = [dict(r) for r in await cursor.fetchall()]

        # 过去7天的体重记录
        async with db.execute(
            """SELECT weight, date(created_at, 'localtime') as day 
               FROM body_metrics 
               WHERE user_id = ? AND date(created_at, 'localtime') >= ?
               ORDER BY id ASC""",
            (user_id, week_ago)
        ) as cursor:
            weight_history = [dict(r) for r in await cursor.fetchall()]

        return {
            "user": user,
            "daily_intakes": daily_intakes,
            "muscle_dist": muscle_dist,
            "weight_history": weight_history
        }
