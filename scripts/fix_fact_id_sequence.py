"""修复fact_measurements表的id列序列问题"""
import psycopg


def main():
    conn = psycopg.connect(
        'host=localhost dbname=pump_station_optimization user=postgres')
    conn.autocommit = True
    cur = conn.cursor()

    # 1. 创建序列
    print('Creating sequence...')
    cur.execute('CREATE SEQUENCE IF NOT EXISTS fact_measurements_id_seq')

    # 2. 设置列默认值
    print('Setting default value...')
    cur.execute(
        "ALTER TABLE public.fact_measurements ALTER COLUMN id SET DEFAULT nextval('fact_measurements_id_seq'::regclass)")

    # 3. 设置序列归属
    print('Setting sequence ownership...')
    cur.execute(
        "ALTER SEQUENCE fact_measurements_id_seq OWNED BY fact_measurements.id")

    # 4. 验证
    cur.execute("SELECT column_name, column_default FROM information_schema.columns WHERE table_name = 'fact_measurements' AND column_name = 'id'")
    print(f'Verification: {cur.fetchone()}')

    print('Done!')
    conn.close()


if __name__ == '__main__':
    main()
