import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 1. 账单表
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            note TEXT,
            date TEXT NOT NULL
        )
    ''')
    # 2. 【新】分类表（保证分类名称不重复）
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    # 如果分类表是空的，自动填入一批初始默认分类
    c.execute('SELECT COUNT(*) FROM categories')
    if c.fetchone()[0] == 0:
        default_cats = ['日常三餐', '咖啡 (星巴克/瑞幸)', '无糖/低糖饮品', '宠物消费', '健身/运动', '学习/备考', '交通出行', '黄金/理财', '其他']
        for cat in default_cats:
            c.execute('INSERT INTO categories (name) VALUES (?)', (cat,))
            
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # 获取历史记录
    c.execute('SELECT * FROM expenses ORDER BY date DESC')
    records = c.fetchall()
    
    total = sum([row[1] for row in records]) if records else 0.0
    
    c.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category')
    chart_data_raw = c.fetchall()
    
    # 【新】获取所有动态分类，发给前端的下拉菜单
    c.execute('SELECT name FROM categories ORDER BY id')
    categories = [row[0] for row in c.fetchall()]
    
    conn.close()
    
    chart_labels = json.dumps([row[0] for row in chart_data_raw])
    chart_values = json.dumps([row[1] for row in chart_data_raw])
    
    return render_template("index.html", 
                           records=records, 
                           total=total,
                           chart_labels=chart_labels,
                           chart_values=chart_values,
                           categories=categories) # 把分类列表传给前端

@app.route("/add", methods=["POST"])
def add_record():
    amount = request.form.get("amount")
    category = request.form.get("category")
    note = request.form.get("note")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO expenses (amount, category, note, date) VALUES (?, ?, ?, ?)', 
              (amount, category, note, date))
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

# 【新接口！】接收前端发来的新分类并存入数据库
@app.route("/add_category", methods=["POST"])
def add_category():
    new_cat = request.form.get("new_category")
    if new_cat:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            # 存入新分类，如果遇到重复的会报错，这里用 try 忽略重复报错
            c.execute('INSERT INTO categories (name) VALUES (?)', (new_cat,))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)