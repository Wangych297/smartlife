# smartlife_core.py
import datetime
import uuid
from collections import defaultdict

class SmartLifeApp:
    """
    智能健康管理与任务追踪系统核心功能类 (扩展版)
    """
    def __init__(self):
        self.health_data = [] # 格式: {'id': uuid, 'date': str('YYYY-MM-DD'), 'type': str, 'value': any, 'timestamp': datetime}
        self.tasks = []       # 格式: {'id': uuid, 'description': str, 'priority': str, 'due_date': str('YYYY-MM-DD' or '无'), 'status': str('待办'/'已完成'), 'group': str or None, 'tags': list[str], 'timestamp': datetime}
        self.health_goals = [] # 格式: {'id': uuid, 'type': str, 'target': float, 'period': str('daily'/'weekly'), 'set_at': datetime}
        self.user_points = 0
        self.POINTS_PER_TASK = 10 # 完成一个任务得10分

    # --- 健康数据管理 (基本不变) ---
    def add_health_data(self, date_str, data_type, value):
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print(f"警告: 日期格式 '{date_str}' 不标准，建议使用 YYYY-MM-DD。")
            # return None # 可以选择更严格地拒绝

        # 尝试转换数值
        try:
            numeric_value = float(value) if '.' in str(value) else int(value)
        except ValueError:
            numeric_value = value # 保留原始输入如果不能转换

        new_record = {
            'id': uuid.uuid4(),
            'date': date_str,
            'type': data_type.strip(), # 去除类型两边空格
            'value': numeric_value,
            'timestamp': datetime.datetime.now()
        }
        self.health_data.append(new_record)
        print(f"后台: 健康数据添加成功: [{date_str}] {data_type}: {value}")
        return new_record['id']

    def get_health_data(self, specific_date=None):
        filtered_data = []
        # 按日期和时间戳降序排序
        sorted_data = sorted(self.health_data, key=lambda x: (x.get('date', ''), x['timestamp']), reverse=True)
        for record in sorted_data:
             if specific_date is None or record.get('date') == specific_date:
                 # 确保 value 存在
                 record['value'] = record.get('value', 'N/A') # 处理可能丢失的 value
                 filtered_data.append(record)
        return filtered_data

    def get_health_record_by_id(self, record_id):
        for record in self.health_data:
            if record['id'] == record_id:
                return record
        return None

    def delete_health_data(self, record_id):
        original_length = len(self.health_data)
        self.health_data = [record for record in self.health_data if record['id'] != record_id]
        deleted = len(self.health_data) < original_length
        if deleted:
            print(f"后台: 健康数据删除成功: ID {record_id}")
        else:
             print(f"后台错误：未找到ID为 {record_id} 的健康数据。")
        return deleted

    # --- 任务管理 (扩展) ---
    def add_task(self, description, priority="中", due_date=None, group=None, tags_str=""):
        """添加一个新任务, 包括分组和标签"""
        tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []

        new_task = {
            'id': uuid.uuid4(),
            'description': description,
            'priority': priority if priority else "中",
            'due_date': due_date if due_date else "无",
            'status': "待办",
            'group': group.strip() if group else None, # 去除分组两边空格
            'tags': tags_list,
            'timestamp': datetime.datetime.now()
        }
        self.tasks.append(new_task)
        print(f"后台: 任务添加成功: '{description}' (分组: {new_task['group']}, 标签: {new_task['tags']})")
        return new_task['id']

    def get_tasks(self, status_filter=None, group_filter=None, tag_filter=None):
        """获取任务列表，增加分组和标签过滤，并添加提醒状态"""
        filtered_tasks = []
        priority_map = {"高": 3, "中": 2, "低": 1, "无": 0}
        today = datetime.date.today()
        upcoming_limit = today + datetime.timedelta(days=3) # 定义“即将到来”为3天内

        # 排序逻辑：状态(待办优先)->优先级(高优先)->截止日期(早优先)->时间戳
        sorted_tasks = sorted(
            self.tasks,
            key=lambda x: (
                x['status'] != '待办', # False (待办) 排在 True (已完成) 前面
                -priority_map.get(x['priority'], 0), # 优先级高的在前 (取负数)
                datetime.datetime.strptime(x['due_date'], '%Y-%m-%d').date() if x['due_date'] != '无' else datetime.date.max, # 有效日期排序，无日期最后
                x['timestamp'] # 添加时间作为次要排序依据
            )
        )

        for task in sorted_tasks:
            # 状态过滤
            if status_filter and task['status'] != status_filter:
                continue
            # 分组过滤
            if group_filter and task['group'] != group_filter:
                continue
            # 标签过滤
            if tag_filter and tag_filter not in task['tags']:
                continue

            # 计算提醒状态
            reminder_status = 'none'
            if task['due_date'] != '无' and task['status'] == '待办':
                try:
                    due = datetime.datetime.strptime(task['due_date'], '%Y-%m-%d').date()
                    if due < today:
                        reminder_status = 'overdue' # 已过期
                    elif due <= upcoming_limit:
                        reminder_status = 'upcoming' # 即将到期
                except ValueError:
                    pass # 日期格式错误则忽略提醒

            task_copy = task.copy() # 避免直接修改原始数据
            task_copy['reminder_status'] = reminder_status
            filtered_tasks.append(task_copy)

        return filtered_tasks

    def get_task_by_id(self, task_id):
         for task in self.tasks:
             if task['id'] == task_id:
                 return task
         return None

    def update_task(self, task_id, new_description=None, new_priority=None, new_due_date=None, new_status=None, new_group=None, new_tags_str=None):
        """根据ID修改任务信息, 包括分组和标签, 并处理积分"""
        task = self.get_task_by_id(task_id)
        if not task:
            print(f"后台错误：未找到ID为 {task_id} 的任务。")
            return False

        updated = False
        awarded_points = 0
        original_status = task['status']

        if new_description is not None:
            task['description'] = new_description
            updated = True
        if new_priority is not None:
            task['priority'] = new_priority
            updated = True
        if new_due_date is not None: # 允许设置为空字符串，表示清除日期
            task['due_date'] = new_due_date if new_due_date else "无"
            updated = True
        if new_status is not None and new_status in ["待办", "已完成"]:
            task['status'] = new_status
            updated = True
            # --- 积分逻辑 ---
            if original_status == '待办' and new_status == '已完成':
                 self.user_points += self.POINTS_PER_TASK
                 awarded_points = self.POINTS_PER_TASK
                 print(f"后台: 任务 {task_id} 完成，获得 {self.POINTS_PER_TASK} 积分。当前总积分: {self.user_points}")
            # (可选) 如果从完成改回待办，是否扣分？这里不扣
            # elif original_status == '已完成' and new_status == '待办':
            #    self.user_points = max(0, self.user_points - self.POINTS_PER_TASK) # 避免负分
            #    print(f"后台: 任务 {task_id} 标记为待办，扣除 {self.POINTS_PER_TASK} 积分。当前总积分: {self.user_points}")

        elif new_status is not None:
             print(f"后台警告：无效的状态 '{new_status}'。状态未修改。")

        if new_group is not None:
             task['group'] = new_group.strip() if new_group else None
             updated = True
        if new_tags_str is not None:
             task['tags'] = [tag.strip() for tag in new_tags_str.split(',') if tag.strip()]
             updated = True

        if updated:
            task['timestamp'] = datetime.datetime.now() # 更新修改时间
            print(f"后台: 任务更新成功: ID {task_id}")
            return True, awarded_points # 返回是否成功和获得的积分
        else:
            print(f"后台: 任务 {task_id} 未发生变化。")
            return False, 0

    def delete_task(self, task_id):
        """根据ID删除任务"""
        original_length = len(self.tasks)
        task_to_delete = self.get_task_by_id(task_id)
        if not task_to_delete:
             print(f"后台错误：未找到ID为 {task_id} 的任务。")
             return False

        # (可选) 如果删除的是已完成任务，是否扣分？这里不扣
        # if task_to_delete['status'] == '已完成':
        #     self.user_points = max(0, self.user_points - self.POINTS_PER_TASK)

        self.tasks = [task for task in self.tasks if task['id'] != task_id]
        deleted = len(self.tasks) < original_length
        if deleted:
             print(f"后台: 任务删除成功: ID {task_id}")
        return deleted

    def get_all_groups(self):
        """获取所有不重复的任务分组"""
        groups = set(task['group'] for task in self.tasks if task['group'])
        return sorted(list(groups))

    def get_all_tags(self):
        """获取所有不重复的任务标签"""
        tags = set()
        for task in self.tasks:
            tags.update(task['tags'])
        return sorted(list(tags))

    # --- 健康目标管理 ---
    def set_health_goal(self, goal_type, target, period):
        """设置或更新健康目标"""
        goal_type = goal_type.strip()
        if not goal_type or not period in ['daily', 'weekly']:
            print(f"后台错误: 无效的目标类型或周期 ({goal_type}, {period})")
            return None
        try:
            target = float(target)
            if target <= 0:
                 raise ValueError("目标值必须为正数")
        except ValueError as e:
             print(f"后台错误: 无效的目标值 ({target}): {e}")
             return None

        # 检查是否已存在相同类型和周期的目标，存在则更新
        existing_goal = None
        for goal in self.health_goals:
            if goal['type'] == goal_type and goal['period'] == period:
                existing_goal = goal
                break

        if existing_goal:
            existing_goal['target'] = target
            existing_goal['set_at'] = datetime.datetime.now()
            print(f"后台: 健康目标更新成功: {goal_type} ({period}) -> {target}")
            return existing_goal['id']
        else:
            new_goal = {
                'id': uuid.uuid4(),
                'type': goal_type,
                'target': target,
                'period': period,
                'set_at': datetime.datetime.now()
            }
            self.health_goals.append(new_goal)
            print(f"后台: 健康目标设置成功: {goal_type} ({period}) = {target}")
            return new_goal['id']

    def get_health_goals(self):
        """获取所有健康目标"""
        return sorted(self.health_goals, key=lambda x: (x['period'], x['type']))

    def delete_health_goal(self, goal_id):
        """删除健康目标"""
        original_length = len(self.health_goals)
        self.health_goals = [goal for goal in self.health_goals if goal['id'] != goal_id]
        deleted = len(self.health_goals) < original_length
        if deleted:
            print(f"后台: 健康目标删除成功: ID {goal_id}")
        else:
            print(f"后台错误：未找到ID为 {goal_id} 的健康目标。")
        return deleted


    def calculate_goal_progress(self, target_date=None):
        """计算所有目标的当前进度"""
        if target_date is None:
            target_date = datetime.date.today()

        progress_data = {} # key: goal_id, value: {'current': float, 'target': float, 'percentage': float, 'period_str': str}

        # 按数据类型聚合当天的健康数据值
        daily_sums = defaultdict(float)
        # 按数据类型聚合本周的健康数据值
        weekly_sums = defaultdict(float)

        start_of_week = target_date - datetime.timedelta(days=target_date.weekday()) # 周一为一周开始
        end_of_week = start_of_week + datetime.timedelta(days=6)

        # print(f"计算日期范围: Daily={target_date}, Weekly={start_of_week} to {end_of_week}") # Debug

        for record in self.health_data:
            try:
                record_date = datetime.datetime.strptime(record['date'], '%Y-%m-%d').date()
                value = float(record['value']) # 确保是数值类型

                # 累加日数据
                if record_date == target_date:
                    daily_sums[record['type']] += value

                # 累加周数据
                if start_of_week <= record_date <= end_of_week:
                    weekly_sums[record['type']] += value

            except (ValueError, TypeError):
                 # 忽略无效日期或非数值数据
                 # print(f"Skipping record due to error: {record}") # Debug
                 continue

        # print(f"Daily Sums: {dict(daily_sums)}") # Debug
        # print(f"Weekly Sums: {dict(weekly_sums)}") # Debug

        for goal in self.health_goals:
            current_sum = 0
            period_str = ""
            if goal['period'] == 'daily':
                current_sum = daily_sums[goal['type']]
                period_str = target_date.strftime('%Y-%m-%d')
            elif goal['period'] == 'weekly':
                current_sum = weekly_sums[goal['type']]
                period_str = f"周 {start_of_week.strftime('%m-%d')} 到 {end_of_week.strftime('%m-%d')}"

            target = goal['target']
            percentage = (current_sum / target * 100) if target > 0 else 0

            progress_data[goal['id']] = {
                'current': round(current_sum, 2),
                'target': round(target, 2),
                'percentage': round(percentage, 1),
                'period_str': period_str,
                'type': goal['type'], # 把类型也放进去方便显示
                'period': goal['period'] # 把周期也放进去
            }
            # print(f"Progress for Goal {goal['id']} ({goal['type']}/{goal['period']}): {progress_data[goal['id']]}") # Debug


        return progress_data

    # --- 积分系统 ---
    def get_user_points(self):
        """获取当前用户积分"""
        return self.user_points