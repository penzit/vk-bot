import os
import sqlite3
import psycopg

SQLITE_PATH = os.getenv('DATABASE_PATH', 'bot.db')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/vk_bot')

TABLES = [
    'categories', 'master_categories', 'shop_categories', 'food_categories',
    'faq', 'masters', 'shops', 'ratings', 'reviews', 'ads_requests',
    'user_sessions', 'verification_requests', 'master_registrations',
    'shop_registrations', 'shop_verification_requests', 'bot_settings', 'employers',
]


def columns(sqlite_conn, table):
    return [row[1] for row in sqlite_conn.execute(f'PRAGMA table_info({table})')]


def main():
    sq = sqlite3.connect(SQLITE_PATH)
    pg = psycopg.connect(DATABASE_URL)
    try:
        with pg.cursor() as cur:
            cur.execute('SET session_replication_role = replica')
            for table in reversed(TABLES):
                cur.execute(f'TRUNCATE TABLE {table} RESTART IDENTITY CASCADE')
            for table in TABLES:
                cols = columns(sq, table)
                rows = sq.execute(f'SELECT {", ".join(cols)} FROM {table}').fetchall()
                if not rows:
                    print(f'{table}: 0')
                    continue
                placeholders = ', '.join(['%s'] * len(cols))
                col_sql = ', '.join(cols)
                cur.executemany(f'INSERT INTO {table} ({col_sql}) VALUES ({placeholders})', rows)
                print(f'{table}: {len(rows)}')
            for table in TABLES:
                if 'id' in columns(sq, table):
                    cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,))
                    seq = cur.fetchone()[0]
                    if seq:
                        cur.execute(f"SELECT COALESCE(MAX(id), 1) FROM {table}")
                        max_id = cur.fetchone()[0]
                        cur.execute('SELECT setval(%s, %s, true)', (seq, max_id))
            cur.execute('SET session_replication_role = DEFAULT')
        pg.commit()
    except Exception:
        pg.rollback()
        raise
    finally:
        sq.close()
        pg.close()


if __name__ == '__main__':
    main()
