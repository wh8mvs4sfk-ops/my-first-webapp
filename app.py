from flask import Flask

# 创建一个网站应用
app = Flask(__name__)

# 告诉网站，当有人访问首页("/")时，该显示什么
@app.route("/")
def home():
    return "<h1>Hello World! 欢迎来到我的记账本</h1><p>比如：今天喝无糖咖啡花了多少钱？</p>"

# 启动这个网站
if __name__ == "__main__":
    app.run(debug=True)