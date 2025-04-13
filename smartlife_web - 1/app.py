# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from smartlife_core import SmartLifeApp # 导入核心逻辑类
import uuid # 需要导入uuid以转换ID

app = Flask(__name__)
app.secret_key = 'a_very_secret_key_for_flashing' # 用于flash消息，随便设置一个

# 创建 SmartLifeApp 的单一实例 (内存存储的关键)
# 在生产环境中，这里会连接数据库
app_instance = SmartLifeApp()

@app.route('/', methods=['GET'])
def index():
    """主页，显示数据和添加表单"""
    health_data = app_instance.get_health_data()
    tasks = app_instance.get_tasks()
    return render_template('index.html', health_data=health_data, tasks=tasks)

# --- 健康数据 Web 接口 ---

@app.route('/health/add', methods=['POST'])
def add_health():
    """处理添加健康数据的表单提交"""
    date_str = request.form.get('health_date')
    data_type = request.form.get('health_type')
    value_str = request.form.get('health_value')

    if not date_str or not data_type or not value_str:
        flash('健康数据所有字段均为必填项。', 'error')
        return redirect(url_for('index'))

    # 尝试转换数值类型
    try:
        value = float(value_str) if '.' in value_str else int(value_str)
    except ValueError:
        value = value_str # 保持字符串

    app_instance.add_health_data(date_str, data_type, value)
    flash('健康数据添加成功！', 'success')
    return redirect(url_for('index')) # 重定向回主页，避免刷新重复提交

@app.route('/health/delete/<uuid:record_id>', methods=['POST']) # 使用POST更安全
def delete_health(record_id):
    """处理删除健康数据的请求"""
    # record_id 由 Flask 的 uuid 转换器自动验证格式并转为 UUID 对象
    deleted = app_instance.delete_health_data(record_id)
    if deleted:
        flash(f'健康数据 ID {record_id} 删除成功。', 'success')
    else:
        flash(f'未能找到或删除健康数据 ID {record_id}。', 'error')
    return redirect(url_for('index'))

# 注意：Web 修改通常需要一个单独的编辑页面，这里为了简化省略了健康数据的修改功能。

# --- 任务管理 Web 接口 ---

@app.route('/task/add', methods=['POST'])
def add_task():
    """处理添加任务的表单提交"""
    description = request.form.get('task_description')
    priority = request.form.get('task_priority') or "中" # 默认为中
    due_date = request.form.get('task_due_date') # HTML date input 会是 YYYY-MM-DD 或空字符串

    if not description:
        flash('任务描述是必填项。', 'error')
        return redirect(url_for('index'))

    app_instance.add_task(description, priority, due_date if due_date else None) # 传递 None 如果为空
    flash('任务添加成功！', 'success')
    return redirect(url_for('index'))

@app.route('/task/delete/<uuid:task_id>', methods=['POST']) # 使用POST更安全
def delete_task(task_id):
    """处理删除任务的请求"""
    deleted = app_instance.delete_task(task_id)
    if deleted:
        flash(f'任务 ID {task_id} 删除成功。', 'success')
    else:
         flash(f'未能找到或删除任务 ID {task_id}。', 'error')
    return redirect(url_for('index'))

@app.route('/task/update_status/<uuid:task_id>/<new_status>', methods=['POST']) # 使用POST
def update_task_status(task_id, new_status):
    """处理更新任务状态的请求"""
    if new_status not in ['待办', '已完成']:
         flash('无效的任务状态。', 'error')
         return redirect(url_for('index'))

    updated = app_instance.update_task(task_id, new_status=new_status)
    if updated:
        flash(f'任务 ID {task_id} 状态已更新为 {new_status}。', 'success')
    else:
        flash(f'未能更新任务 ID {task_id} 的状态。', 'error')
    return redirect(url_for('index'))

# 注意：Web 修改任务的其他字段（描述、优先级、日期）通常需要一个编辑页面，这里简化了。

if __name__ == '__main__':
    # debug=True 会在代码更改时自动重启服务器，并提供更详细的错误信息
    # host='0.0.0.0' 让局域网内其他设备也能访问 (如果防火墙允许)
    app.run(debug=True, host='0.0.0.0', port=5001) # 使用一个不常用的端口，如5001