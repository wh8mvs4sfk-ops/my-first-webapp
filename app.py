import sqlite3
import json
import csv # 【新增】引入 Python 内置的 csv 库
from io import StringIO # 【新增】用于在内存中生成文本流
from flask import Flask, render_template, request, redirect, url_for, Response # 【新增】引入 Response
from datetime import datetime

app = Flask(__name__)

EXCHANGE_RATES = {
    'CNY': 1.0,
    'JPY': 0.047,
    'THB': 0.20,
    'KRW': 0.0053,
    'VND': 0.00028,
    'MYR': 1.52,
    'USD': 7.23
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

    total_cny = 0.0
    chart_dict = {}
    
    for row in records:
        amount = row[1]
        category = row[2]
        currency = row[5] if len(row) > 5 and row[5] else 'CNY'
        
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
    currency = request.form.get("currency")
    category = request.form.get("category")
    note = request.form.get("note")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
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

# 【新核心接口！】导出选定月份的 CSV
@app.route("/export_csv")
def export_csv():
    # 获取要导出的月份，默认当前月
    selected_month = request.args.get('month', datetime.now().strftime("%Y-%m"))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 获取该月份的所有数据
    c.execute("SELECT date, category, note, amount, currency FROM expenses WHERE date LIKE ? ORDER BY date DESC", (selected_month + '%',))
    records = c.fetchall()
    conn.close()

    # 在内存中创建一个文本流对象，代替实际的文件写入
    si = StringIO()
    # 添加 BOM 标识，防止用 Excel 打开含有中文的 CSV 时出现乱码
    si.write('\ufeff')
    cw = csv.writer(si)
    
    # 写入 CSV 的表头
    cw.writerow(['时间 (Date)', '分类 (Category)', '备注 (Note)', '金额 (Amount)', '币种 (Currency)', '折合人民币 (CNY)'])
    
    # 遍历数据，逐行写入
    for row in records:
        date, category, note, amount, currency = row
        # 兼容旧数据的币种为空情况
        currency = currency if currency else 'CNY'
        # 顺便计算一下折合人民币，方便用户在 Excel 里直接看
        rate = EXCHANGE_RATES.get(currency, 1.0)
        cny_amount = round(amount * rate, 2)
        
        cw.writerow([date, category, note, amount, currency, cny_amount])

    # 把生成的文本流转化为网页响应，告诉浏览器下载名为 "expenses_月份.csv" 的文件
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=expenses_{selected_month}.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)