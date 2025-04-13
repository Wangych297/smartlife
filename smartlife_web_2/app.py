# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from smartlife_core import SmartLifeApp # 导入核心逻辑类
import uuid
import datetime # 需要导入datetime

app = Flask(__name__)
app.secret_key = 'another_very_secret_key' # 更改一下

# 创建 SmartLifeApp 的单一实例
app_instance = SmartLifeApp()

@app.route('/', methods=['GET'])
def index():
    """主页，显示所有数据、目标、积分等"""
    # 获取过滤参数
    status_filter = request.args.get('status') # e.g., ?status=待办
    group_filter = request.args.get('group')
    tag_filter = request.args.get('tag')
    
    # 添加now变量
    now = datetime.datetime.now()

    # 获取数据
    health_data = app_instance.get_health_data()
    # 传递过滤参数给 get_tasks
    tasks = app_instance.get_tasks(status_filter=status_filter, group_filter=group_filter, tag_filter=tag_filter)
    goals = app_instance.get_health_goals()
    goal_progress = app_instance.calculate_goal_progress() # 计算当天的进度
    user_points = app_instance.get_user_points()
    all_groups = app_instance.get_all_groups() # 用于过滤下拉菜单
    all_tags = app_instance.get_all_tags()     # 用于过滤下拉菜单

    # 准备过滤信息给模板
    filters_active = {
        'status': status_filter,
        'group': group_filter,
        'tag': tag_filter
    }

    return render_template('index.html',
                           now=now,  # 传递now变量
                           health_data=health_data,
                           tasks=tasks,
                           goals=goals,
                           goal_progress=goal_progress,
                           user_points=user_points,
                           all_groups=all_groups,
                           all_tags=all_tags,
                           filters_active=filters_active
                           )

# --- 健康数据 Web 接口 (基本不变) ---
@app.route('/health/add', methods=['POST'])
def add_health():
    date_str = request.form.get('health_date')
    data_type = request.form.get('health_type')
    value_str = request.form.get('health_value')

    if not date_str or not data_type or not value_str:
        flash('健康数据所有字段均为必填项。', 'error')
        return redirect(url_for('index'))

    app_instance.add_health_data(date_str, data_type, value_str) # 后端会尝试转换类型
    flash('健康数据添加成功！', 'success')
    return redirect(url_for('index'))

@app.route('/health/delete/<uuid:record_id>', methods=['POST'])
def delete_health(record_id):
    deleted = app_instance.delete_health_data(record_id)
    if deleted:
        flash(f'健康数据删除成功。', 'success')
    else:
        flash(f'未能找到或删除健康数据。', 'error')
    return redirect(url_for('index'))

# --- 任务管理 Web 接口 (扩展) ---
@app.route('/task/add', methods=['POST'])
def add_task():
    description = request.form.get('task_description')
    priority = request.form.get('task_priority') or "中"
    due_date = request.form.get('task_due_date') # HTML date input 会是 YYYY-MM-DD 或空字符串
    group = request.form.get('task_group')
    tags_str = request.form.get('task_tags')

    if not description:
        flash('任务描述是必填项。', 'error')
        return redirect(url_for('index'))

    app_instance.add_task(description, priority, due_date if due_date else None, group, tags_str)
    flash('任务添加成功！', 'success')
    return redirect(url_for('index'))

@app.route('/task/delete/<uuid:task_id>', methods=['POST'])
def delete_task(task_id):
    deleted = app_instance.delete_task(task_id)
    if deleted:
        flash(f'任务删除成功。', 'success')
    else:
         flash(f'未能找到或删除任务。', 'error')
    # 保留当前的过滤条件
    args = request.referrer.split('?')[-1] if '?' in request.referrer else ''
    return redirect(url_for('index') + ('?' + args if args else ''))


@app.route('/task/update_status/<uuid:task_id>/<new_status>', methods=['POST'])
def update_task_status(task_id, new_status):
    if new_status not in ['待办', '已完成']:
         flash('无效的任务状态。', 'error')
    else:
        updated, points_awarded = app_instance.update_task(task_id, new_status=new_status)
        if updated:
            message = f'任务状态已更新为 {new_status}。'
            if points_awarded > 0:
                message += f' 恭喜获得 {points_awarded} 积分！'
            flash(message, 'success')
        else:
            flash(f'未能更新任务状态。', 'error')
    # 保留当前的过滤条件
    args = request.referrer.split('?')[-1] if '?' in request.referrer else ''
    return redirect(url_for('index') + ('?' + args if args else ''))


# --- (新增) 任务编辑页面路由 ---
@app.route('/task/edit/<uuid:task_id>', methods=['GET'])
def edit_task_page(task_id):
    task = app_instance.get_task_by_id(task_id)
    if not task:
        flash('未找到要编辑的任务。', 'error')
        return redirect(url_for('index'))
    # 将标签列表转回逗号分隔的字符串以便在输入框中显示
    task_edit_view = task.copy()
    task_edit_view['tags_str'] = ', '.join(task_edit_view.get('tags', []))
    return render_template('edit_task.html', task=task_edit_view)

@app.route('/task/update/<uuid:task_id>', methods=['POST'])
def update_task_details(task_id):
    description = request.form.get('task_description')
    priority = request.form.get('task_priority')
    due_date = request.form.get('task_due_date') # 可以为空
    group = request.form.get('task_group')
    tags_str = request.form.get('task_tags')

    if not description:
         flash('任务描述不能为空。', 'error')
         # 如果需要返回编辑页，需要重新获取任务并渲染 edit_task.html
         task = app_instance.get_task_by_id(task_id)
         if task:
            task_edit_view = task.copy()
            task_edit_view['tags_str'] = ', '.join(task_edit_view.get('tags', []))
            return render_template('edit_task.html', task=task_edit_view)
         else:
            return redirect(url_for('index')) # 如果任务找不到了，回主页


    updated, _ = app_instance.update_task(
        task_id,
        new_description=description,
        new_priority=priority,
        new_due_date=due_date if due_date else None, # 传递 None 如果为空
        new_group=group,
        new_tags_str=tags_str
        # 注意：这里不通过此接口修改状态，状态修改有单独的接口
    )

    if updated:
        flash('任务详细信息更新成功！', 'success')
    else:
        # 可能是没找到任务，或者提交的数据和原来一样
        flash('任务信息未发生变化或更新失败。', 'warning') # 使用 warning 更合适

    return redirect(url_for('index'))


# --- 健康目标 Web 接口 ---
@app.route('/goal/set', methods=['POST'])
def set_goal():
    goal_type = request.form.get('goal_type')
    target = request.form.get('goal_target')
    period = request.form.get('goal_period')

    if not goal_type or not target or not period:
        flash('设置健康目标时，类型、目标值和周期都不能为空。', 'error')
        return redirect(url_for('index'))

    goal_id = app_instance.set_health_goal(goal_type, target, period)

    if goal_id:
        flash(f'{goal_type} ({period}) 目标设置/更新成功！', 'success')
    else:
        flash('设置健康目标失败，请检查输入值。', 'error')

    return redirect(url_for('index'))

@app.route('/goal/delete/<uuid:goal_id>', methods=['POST'])
def delete_goal(goal_id):
    deleted = app_instance.delete_health_goal(goal_id)
    if deleted:
        flash('健康目标删除成功。', 'success')
    else:
        flash('未能找到或删除健康目标。', 'error')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)