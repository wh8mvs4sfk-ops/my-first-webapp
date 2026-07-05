import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

# 预设的近似汇率（折合人民币），你可以随时在这里修改最新汇率
EXCHANGE_RATES = {
    'CNY': 1.0,      # 人民币
    'JPY': 0.047,    # 日元
    'THB': 0.20,     # 泰铢
    'KRW': 0.0053,   # 韩元
    'VND': 0.00028,  # 越南盾
    'MYR': 1.52,     # 马来西亚林吉特
    'USD': 7.23      # 美元
}

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            note TEXT,
            date TEXT NOT NULL
        )
    ''')
    
    # 【黑科技】无损升级数据库：尝试给旧表增加 currency 列，如果已经存在就忽略报错
    try:
        c.execute('ALTER TABLE expenses ADD COLUMN currency TEXT DEFAULT "CNY"')
    except sqlite3.OperationalError:
        pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    c.execute('SELECT COUNT(*) FROM categories')
    if c.fetchone()[0] == 0:
        default_cats = ['日常三餐', '咖啡 (星巴克/瑞幸)', '无糖/低糖饮品', '宠物消费', '健身/运动', '交通出行', '其他']
        for cat in default_cats:
            c.execute('INSERT INTO categories (name) VALUES (?)', (cat,))
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    selected_month = request.args.get('month', datetime.now().strftime("%Y-%m"))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM expenses WHERE date LIKE ? ORDER BY date DESC", (selected_month + '%',))
    records = c.fetchall()
    
    c.execute('SELECT name FROM categories ORDER BY id')
    categories = [row[0] for row in c.fetchall()]
    conn.close()

    # 【新逻辑】按汇率换算总金额并生成图表数据
    total_cny = 0.0
    chart_dict = {}
    
    for row in records:
        # row[1] 是金额，row[5] 是币种 (旧数据如果没有币种，默认为 CNY)
        amount = row[1]
        category = row[2]
        currency = row[5] if len(row) > 5 and row[5] else 'CNY'
        
        # 换算成人民币
        rate = EXCHANGE_RATES.get(currency, 1.0)
        cny_amount = amount * rate
        
        total_cny += cny_amount
        chart_dict[category] = chart_dict.get(category, 0) + cny_amount
    
    chart_labels = json.dumps(list(chart_dict.keys()))
    chart_values = json.dumps(list(chart_dict.values()))
    
    return render_template("index.html", 
                           records=records, 
                           total=total_cny,
                           chart_labels=chart_labels,
                           chart_values=chart_values,
                           categories=categories,
                           selected_month=selected_month)

@app.route("/add", methods=["POST"])
def add_record():
    amount = request.form.get("amount")
    currency = request.form.get("currency") # 接收币种
    category = request.form.get("category")
    note = request.form.get("note")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 存入数据库时，把 currency 也存进去
    c.execute('INSERT INTO expenses (amount, category, note, date, currency) VALUES (?, ?, ?, ?, ?)', 
              (amount, category, note, date, currency))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route("/delete/<int:record_id>")
def delete_record(record_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM expenses WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route("/add_category", methods=["POST"])
def add_category():
    new_cat = request.form.get("new_category")
    if new_cat:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO categories (name) VALUES (?)', (new_cat,))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)