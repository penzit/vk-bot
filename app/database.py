import re
import sqlite3
import time
from contextlib import contextmanager
from .config import DATABASE_PATH, DATABASE_URL


def _use_postgres():
    return bool(DATABASE_URL)


class _ScalarCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class PostgresConnection:
    def __init__(self):
        try:
            import psycopg2
            self.conn = psycopg2.connect(DATABASE_URL)
        except ImportError:
            import psycopg
            self.conn = psycopg.connect(DATABASE_URL)
        self._last_insert_id = None

    def _sql(self, sql):
        sql = sql.strip()
        sql = sql.replace('?', '%s')
        sql = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'SERIAL PRIMARY KEY', sql, flags=re.I)
        sql = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO\s+([^\s(]+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)',
                     r'INSERT INTO \1 (\2) VALUES (\3) ON CONFLICT DO NOTHING', sql, flags=re.I)
        sql = re.sub(r'INSERT\s+OR\s+REPLACE\s+INTO\s+bot_settings\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)',
                     r'INSERT INTO bot_settings (\1) VALUES (\2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value', sql, flags=re.I)
        sql = sql.replace('verified = 1 - verified', 'verified = CASE WHEN verified = 1 THEN 0 ELSE 1 END')
        sql = sql.replace('recommended = 1 - recommended', 'recommended = CASE WHEN recommended = 1 THEN 0 ELSE 1 END')
        return sql

    def _maybe_returning(self, sql):
        if not re.match(r'INSERT\s+INTO\s+', sql, flags=re.I):
            return sql
        if re.search(r'\bRETURNING\b', sql, flags=re.I) or re.search(r'\bON\s+CONFLICT\s+DO\s+NOTHING\b', sql, flags=re.I):
            return sql
        m = re.search(r'INSERT\s+INTO\s+(\w+)', sql, flags=re.I)
        table = m.group(1).lower() if m else ''
        if table == 'user_sessions':
            return sql + ' RETURNING user_id'
        return sql + ' RETURNING id'

    def execute(self, sql, params=None):
        sql = self._sql(sql)
        if sql.lower() == 'select last_insert_rowid()':
            return _ScalarCursor([(self._last_insert_id,)])
        params = params or []
        cur = self.conn.cursor()
        run_sql = self._maybe_returning(sql)
        try:
            cur.execute(run_sql, params)
        except Exception:
            self.conn.rollback()
            cur.close()
            raise
        if run_sql != sql:
            row = cur.fetchone()
            self._last_insert_id = row[0] if row else None
        return cur

    def executemany(self, sql, seq):
        for params in seq:
            self.execute(sql, params)

    def executescript(self, script):
        statements = [part.strip() for part in script.split(';') if part.strip()]
        for stmt in statements:
            self.execute(stmt)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_conn():
    if _use_postgres():
        return PostgresConnection()
    return sqlite3.connect(DATABASE_PATH)


@contextmanager
def get_db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                keywords TEXT NOT NULL DEFAULT '',
                answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS master_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS shop_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS food_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER DEFAULT NULL,
                owner_vk_id INTEGER DEFAULT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                contacts TEXT DEFAULT '',
                photo TEXT DEFAULT '',
                verified INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                votes_count INTEGER DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES master_categories(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER DEFAULT NULL,
                owner_vk_id INTEGER DEFAULT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                contacts TEXT DEFAULT '',
                photo TEXT DEFAULT '',
                shop_type TEXT DEFAULT 'shop' CHECK(shop_type IN ('shop', 'food')),
                verified INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                votes_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES shop_categories(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                target_type TEXT NOT NULL CHECK(target_type IN ('master', 'shop')),
                target_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, target_type, target_id)
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL DEFAULT 'master' CHECK(target_type IN ('master', 'shop', 'food')),
                target_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT DEFAULT '',
                text TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ads_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT DEFAULT '',
                message_type TEXT DEFAULT 'ad' CHECK(message_type IN ('ad', 'contact')),
                message_text TEXT DEFAULT '',
                status TEXT DEFAULT 'new' CHECK(status IN ('new', 'read', 'closed')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id INTEGER PRIMARY KEY,
                first_seen REAL NOT NULL,
                last_interaction REAL NOT NULL,
                msg_count INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS verification_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                master_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                phone TEXT DEFAULT '',
                documents_info TEXT DEFAULT '',
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (master_id) REFERENCES masters(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS master_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT DEFAULT '',
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                contacts TEXT DEFAULT '',
                category_id INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS shop_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT DEFAULT '',
                shop_type TEXT DEFAULT 'shop',
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                contacts TEXT DEFAULT '',
                category_id INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS shop_verification_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                phone TEXT DEFAULT '',
                documents_info TEXT DEFAULT '',
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS bot_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS employers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT DEFAULT '',
                company_name TEXT NOT NULL,
                description TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                vk_page TEXT DEFAULT '',
                contacts TEXT DEFAULT '',
                vacancy_text TEXT DEFAULT '',
                photo TEXT DEFAULT '',
                recommended INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS order_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS order_performers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vk_id INTEGER NOT NULL,
                name TEXT DEFAULT '',
                description TEXT DEFAULT '',
                contact TEXT DEFAULT '',
                rating REAL DEFAULT 0.0,
                reviews_count INTEGER DEFAULT 0,
                accepts_requests INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS order_performer_categories (
                performer_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (performer_id, category_id),
                FOREIGN KEY (performer_id) REFERENCES order_performers(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES order_categories(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_vk_id INTEGER NOT NULL,
                user_name TEXT DEFAULT '',
                category_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                urgency TEXT DEFAULT 'Не срочно',
                address TEXT DEFAULT '',
                contact TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                desired_time TEXT DEFAULT '',
                comment TEXT DEFAULT '',
                status TEXT DEFAULT 'new' CHECK(status IN ('new','has_responses','in_progress','completed','cancelled','expired')),
                selected_performer_id INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES order_categories(id),
                FOREIGN KEY (selected_performer_id) REFERENCES order_performers(id)
            );
            CREATE TABLE IF NOT EXISTS order_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                performer_id INTEGER NOT NULL,
                message TEXT DEFAULT '',
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected','declined')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (performer_id) REFERENCES order_performers(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS order_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                customer_vk_id INTEGER NOT NULL,
                performer_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                text TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (performer_id) REFERENCES order_performers(id) ON DELETE CASCADE
            );
        """)

    for migration in [
        "ALTER TABLE employers ADD COLUMN phone TEXT DEFAULT ''",
        "ALTER TABLE employers ADD COLUMN vk_page TEXT DEFAULT ''",
        "ALTER TABLE employers ADD COLUMN status TEXT DEFAULT 'pending'",
        "ALTER TABLE masters ADD COLUMN views_count INTEGER DEFAULT 0",
        "ALTER TABLE masters ADD COLUMN recommended INTEGER DEFAULT 0",
        "ALTER TABLE shops ADD COLUMN recommended INTEGER DEFAULT 0",
        "ALTER TABLE master_registrations ADD COLUMN photo TEXT DEFAULT ''",
        "ALTER TABLE shop_registrations ADD COLUMN photo TEXT DEFAULT ''",
        "ALTER TABLE employers ADD COLUMN photo TEXT DEFAULT ''",
        "ALTER TABLE employers ADD COLUMN recommended INTEGER DEFAULT 0",
    ]:
        try:
            with get_db() as db:
                db.execute(migration)
        except Exception:
            pass

def seed_data():
    with get_db() as db:
        cat_count = db.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if cat_count > 0:
            db.executemany("INSERT OR IGNORE INTO order_categories (name) VALUES (?)", [
                ("Электрик",), ("Сантехник",), ("Ремонт",), ("Грузчики",),
                ("Доставка",), ("Такси",), ("Помощь по дому",), ("Красота и здоровье",),
                ("Строительство",), ("Подработка",), ("Другое",),
            ])
            return

        db.executemany("INSERT OR IGNORE INTO categories (name) VALUES (?)",
            [("Доставка",), ("Оплата",), ("Возврат",), ("Общее",)])

        db.executemany("INSERT INTO faq (category_id, question, keywords, answer) VALUES (?, ?, ?, ?)", [
            (1, "Сколько идёт доставка?", "доставка сроки идёт", "Стандартная доставка занимает 3-5 рабочих дней."),
            (1, "Какие регионы доставляете?", "регионы доставка города", "Доставляем по всей России через СДЭК и Почту России."),
            (2, "Какие способы оплаты?", "оплата способы карта нал", "Принимаем карты, наличные, переводы на карту."),
            (2, "Есть ли рассрочка?", "рассрочка кредит оплата частями", "Рассрочка доступна через Т-Банк и СберБанк."),
            (3, "Как вернуть товар?", "возврат вернуть обменять", "Возврат возможен в течение 14 дней с момента получения."),
            (3, "Условия возврата?", "условия возврат обмен", "Товар должен быть в ненарушенной упаковке с чеком."),
            (4, "Есть ли гарантия?", "гарантия качество", "На все товары действует гарантия 12 месяцев."),
            (4, "Работаете в выходные?", "выходные график работа часы", "Мы работаем ежедневно с 10:00 до 21:00."),
        ])

        db.executemany("INSERT OR IGNORE INTO master_categories (name) VALUES (?)",
            [("Красота",), ("Фото",), ("Ремонт",), ("Обучение",)])

        db.executemany("INSERT OR IGNORE INTO shop_categories (name) VALUES (?)",
            [("Одежда",), ("Еда",), ("Услуги",), ("Товары",)])

        db.executemany("INSERT OR IGNORE INTO food_categories (name) VALUES (?)",
            [("Пицца",), ("Суши",), ("Бургеры",), ("Десерты",)])

        db.executemany("INSERT INTO masters (category_id, name, description, contacts, photo) VALUES (?, ?, ?, ?, ?)", [
            (1, "Анна — Визажист", "Профессиональный макияж для любых мероприятий.", "@anna_makeup, +7 (999) 123-45-67", ""),
            (2, "Сергей — Фотограф", "Предметная и портретная съёмка.", "@sergey_photo, +7 (999) 234-56-78", ""),
            (1, "Елена — Мастер ногтевого сервиса", "Маникюр, педикюр, покрытие гель-лаком.", "@elena_nails, +7 (999) 345-67-89", ""),
        ])

        db.executemany("INSERT INTO shops (category_id, name, description, contacts, photo, shop_type) VALUES (?, ?, ?, ?, ?, ?)", [
            (3, "Студия красоты 'Glamour'", "Полный спектр услуг.", "@glamour_studio, +7 (999) 456-78-90", "", 'shop'),
            (1, "Магазин одежды 'Trend'", "Модная одежда.", "@trend_shop, +7 (999) 567-89-01", "", 'shop'),
            (2, "Кофейня 'CoffeeTime'", "Вкусный кофе и десерты.", "@coffee_time, +7 (999) 678-90-12", "", 'shop'),
            (2, "Доставка суши 'Fuji'", "Свежие суши и роллы.", "@fuji_delivery, +7 (999) 111-22-33", "", 'food'),
            (2, "Пиццерия 'Italia'", "Настоящая итальянская пицца.", "@italia_pizza, +7 (999) 444-55-66", "", 'food'),
        ])

        db.executemany("INSERT OR IGNORE INTO order_categories (name) VALUES (?)", [
            ("Электрик",), ("Сантехник",), ("Ремонт",), ("Грузчики",),
            ("Доставка",), ("Такси",), ("Помощь по дому",), ("Красота и здоровье",),
            ("Строительство",), ("Подработка",), ("Другое",),
        ])


def update_session(user_id):
    now = time.time()
    with get_db() as db:
        existing = db.execute("SELECT last_interaction, msg_count FROM user_sessions WHERE user_id=?", (user_id,)).fetchone()
        if existing:
            db.execute("UPDATE user_sessions SET last_interaction=?, msg_count=msg_count+1 WHERE user_id=?", (now, user_id))
            return existing[0], existing[1] + 1
        else:
            db.execute("INSERT INTO user_sessions (user_id, first_seen, last_interaction, msg_count) VALUES (?, ?, ?, 1)", (user_id, now, now))
            return now, 1


def get_session(user_id):
    with get_db() as db:
        row = db.execute("SELECT first_seen, last_interaction, msg_count FROM user_sessions WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return {"first_seen": row[0], "last_interaction": row[1], "msg_count": row[2]}
        return None


def get_bot_setting(key):
    with get_db() as db:
        row = db.execute("SELECT value FROM bot_settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else None


def set_bot_setting(key, value):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))


def get_all_bot_settings():
    with get_db() as db:
        rows = db.execute("SELECT key, value FROM bot_settings").fetchall()
        return {r[0]: r[1] for r in rows}
