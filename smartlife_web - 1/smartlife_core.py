# smartlife_core.py
import datetime
import uuid

class SmartLifeApp:
    def __init__(self):
        self.health_data = [] # 存储健康数据
        self.tasks = []       # 存储任务数据

    # --- 健康数据管理 ---
    def add_health_data(self, date_str, data_type, value):
        try:
            # 基本校验
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print(f"警告: 日期格式 '{date_str}' 不标准，建议使用 YYYY-MM-DD。")

        new_record = {
            'id': uuid.uuid4(),
            'date': date_str,
            'type': data_type,
            'value': value,
            'timestamp': datetime.datetime.now()
        }
        self.health_data.append(new_record)
        print(f"后台: 健康数据添加成功: [{date_str}] {data_type}: {value}") # 后台日志
        return new_record['id']

    def get_health_data(self, specific_date=None):
        filtered_data = []
        sorted_data = sorted(self.health_data, key=lambda x: (x.get('date', ''), x['timestamp']), reverse=True)
        for record in sorted_data:
             if specific_date is None or record.get('date') == specific_date:
                 filtered_data.append(record)
        return filtered_data

    def get_health_record_by_id(self, record_id):
        for record in self.health_data:
            if record['id'] == record_id:
                return record
        return None

    def update_health_data(self, record_id, new_value):
        record = self.get_health_record_by_id(record_id)
        if record:
            original_value = record['value']
            record['value'] = new_value
            record['timestamp'] = datetime.datetime.now()
            print(f"后台: 健康数据更新成功: ID {record_id} 的值从 {original_value} 修改为 {new_value}")
            return True
        print(f"后台错误：未找到ID为 {record_id} 的健康数据。")
        return False

    def delete_health_data(self, record_id):
        original_length = len(self.health_data)
        self.health_data = [record for record in self.health_data if record['id'] != record_id]
        deleted = len(self.health_data) < original_length
        if deleted:
            print(f"后台: 健康数据删除成功: ID {record_id}")
        else:
             print(f"后台错误：未找到ID为 {record_id} 的健康数据。")
        return deleted

    # --- 任务管理 ---
    def add_task(self, description, priority="中", due_date=None):
        new_task = {
            'id': uuid.uuid4(),
            'description': description,
            'priority': priority if priority else "中",
            'due_date': due_date if due_date else "无",
            'status': "待办",
            'timestamp': datetime.datetime.now()
        }
        self.tasks.append(new_task)
        print(f"后台: 任务添加成功: '{description}'")
        return new_task['id']

    def get_tasks(self, status_filter=None):
        filtered_tasks = []
        priority_map = {"高": 3, "中": 2, "低": 1, "无": 0}
        
        # 先按状态（待办在前），再按优先级，再按时间戳
        sorted_tasks = sorted(
            self.tasks,
            key=lambda x: (x['status'] != '待办', -priority_map.get(x['priority'], 0), x['timestamp']),
            reverse=False # 让待办优先显示
        )
        for task in sorted_tasks:
            if status_filter is None or task['status'] == status_filter:
                filtered_tasks.append(task)
        return filtered_tasks

    def get_task_by_id(self, task_id):
         for task in self.tasks:
             if task['id'] == task_id:
                 return task
         return None

    def update_task(self, task_id, new_description=None, new_priority=None, new_due_date=None, new_status=None):
        task = self.get_task_by_id(task_id)
        if not task:
            print(f"后台错误：未找到ID为 {task_id} 的任务。")
            return False

        updated = False
        if new_description is not None:
            task['description'] = new_description
            updated = True
        if new_priority is not None:
            task['priority'] = new_priority
            updated = True
        # 处理空字符串截止日期
        if new_due_date is not None:
            task['due_date'] = new_due_date if new_due_date else "无"
            updated = True
        if new_status is not None and new_status in ["待办", "已完成"]:
            task['status'] = new_status
            updated = True
        elif new_status is not None:
             print(f"后台警告：无效的状态 '{new_status}'。状态未修改。")


        if updated:
            task['timestamp'] = datetime.datetime.now()
            print(f"后台: 任务更新成功: ID {task_id}")
            return True
        else:
            print(f"后台: 任务 {task_id} 未发生变化。")
            return False # 或者 True，取决于是否认为无变化算成功

    def delete_task(self, task_id):
        original_length = len(self.tasks)
        self.tasks = [task for task in self.tasks if task['id'] != task_id]
        deleted = len(self.tasks) < original_length
        if deleted:
             print(f"后台: 任务删除成功: ID {task_id}")
        else:
             print(f"后台错误：未找到ID为 {task_id} 的任务。")
        return deleted
