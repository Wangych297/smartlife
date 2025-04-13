const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const jwt = require('jsonwebtoken');
const Database = require('better-sqlite3');
const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
// 在中间件部分添加 CORS 支持
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
    
    // 处理 OPTIONS 请求
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    next();
});

// 中间件
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname)));

// JWT 密钥
const JWT_SECRET = 'smartlife-secret-key';

// 数据存储路径
const DATA_DIR = path.join(__dirname, 'data');
const USERS_FILE = path.join(DATA_DIR, 'users.json');
const TASKS_FILE = path.join(DATA_DIR, 'tasks.json');
const DB_FILE = path.join(DATA_DIR, 'smartlife.db');

// 确保数据目录存在
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR);
}

// 初始化数据文件
function initDataFile(filePath, initialData = []) {
    if (!fs.existsSync(filePath)) {
        fs.writeFileSync(filePath, JSON.stringify(initialData, null, 2));
    }
}

// 初始化用户数据
initDataFile(USERS_FILE, [
    { id: 1, username: 'user', password: 'password', points: 100 }
]);
initDataFile(TASKS_FILE, []);

// 初始化数据库
const db = new Database(DB_FILE);
db.pragma('journal_mode = WAL');

// 创建健康数据表
db.exec(`
CREATE TABLE IF NOT EXISTS health_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    steps INTEGER NOT NULL,
    sleep REAL NOT NULL,
    water INTEGER NOT NULL,
    date TEXT NOT NULL,
    created_at TEXT NOT NULL
);
`);

// 创建健康与医疗信息表
db.exec(`
CREATE TABLE IF NOT EXISTS health_medical_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    height REAL,
    weight REAL,
    blood_sugar REAL,
    systolic_pressure INTEGER,
    diastolic_pressure INTEGER,
    heart_rate INTEGER,
    medical_history TEXT,
    medication_history TEXT,
    allergies TEXT,
    blood_type TEXT,
    updated_at TEXT NOT NULL
);
`);

// 读取数据
function readData(filePath) {
    try {
        const data = fs.readFileSync(filePath, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error(`Error reading ${filePath}:`, error);
        return [];
    }
}

// 写入数据
function writeData(filePath, data) {
    try {
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
        return true;
    } catch (error) {
        console.error(`Error writing to ${filePath}:`, error);
        return false;
    }
}

// 验证 JWT 中间件
function authenticateToken(req, res, next) {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    
    if (!token) {
        return res.status(401).json({ error: '未授权访问' });
    }
    
    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) {
            return res.status(403).json({ error: '令牌无效或已过期' });
        }
        req.user = user;
        next();
    });
}

// 注册路由
app.post('/api/auth/register', (req, res) => {
    const { username, password } = req.body;
    
    if (!username || !password) {
        return res.status(400).json({ error: '用户名和密码都是必需的' });
    }
    
    const users = readData(USERS_FILE);
    
    // 检查用户名是否已存在
    if (users.some(u => u.username === username)) {
        return res.status(409).json({ error: '用户名已存在' });
    }
    
    // 创建新用户
    const newUser = {
        id: users.length > 0 ? Math.max(...users.map(u => u.id)) + 1 : 1,
        username,
        password,
        points: 50 // 新用户初始积分
    };
    
    users.push(newUser);
    
    if (writeData(USERS_FILE, users)) {
        // 生成 JWT 令牌
        const token = jwt.sign({ id: newUser.id, username: newUser.username }, JWT_SECRET, { expiresIn: '24h' });
        res.status(201).json({ token, points: newUser.points });
    } else {
        res.status(500).json({ error: '注册用户时出错' });
    }
});

// 登录路由
app.post('/api/auth/login', (req, res) => {
    const { username, password } = req.body;
    const users = readData(USERS_FILE);
    const user = users.find(u => u.username === username && u.password === password);
    
    if (!user) {
        return res.status(401).json({ error: '用户名或密码错误' });
    }
    
    const token = jwt.sign({ id: user.id, username: user.username }, JWT_SECRET, { expiresIn: '24h' });
    res.json({ token, points: user.points });
});

// 健康数据路由 - 使用数据库
app.post('/api/health', authenticateToken, (req, res) => {
    const { steps, sleep, water, date } = req.body;
    const userId = req.user.id;
    
    if (!steps || !sleep || !water || !date) {
        return res.status(400).json({ error: '所有字段都是必需的' });
    }
    
    try {
        // 插入健康数据到数据库
        const stmt = db.prepare(`
            INSERT INTO health_data (user_id, steps, sleep, water, date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        `);
        
        const now = new Date().toISOString();
        const result = stmt.run(userId, parseInt(steps), parseFloat(sleep), parseInt(water), date, now);
        
        // 更新用户积分
        const users = readData(USERS_FILE);
        const userIndex = users.findIndex(u => u.id === userId);
        if (userIndex !== -1) {
            users[userIndex].points += 5; // 添加健康数据奖励5积分
            writeData(USERS_FILE, users);
        }
        
        res.status(201).json({
            id: result.lastInsertRowid,
            userId,
            steps: parseInt(steps),
            sleep: parseFloat(sleep),
            water: parseInt(water),
            date,
            createdAt: now
        });
    } catch (error) {
        console.error('保存健康数据时出错:', error);
        res.status(500).json({ error: '保存数据时出错' });
    }
});

// 获取健康数据 - 使用数据库
app.get('/api/health', authenticateToken, (req, res) => {
    const userId = req.user.id;
    const { period = 'month' } = req.query; // 默认使用 month
    
    try {
        let query = `SELECT * FROM health_data WHERE user_id = ?`;
        const params = [userId];
        
        // 根据时间段筛选数据
        if (period === 'day') {
            const today = new Date().toISOString().split('T')[0];
            query += ` AND date = ?`;
            params.push(today);
        } else if (period === 'week') {
            const oneWeekAgo = new Date();
            oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
            const oneWeekAgoStr = oneWeekAgo.toISOString().split('T')[0];
            query += ` AND date >= ?`;
            params.push(oneWeekAgoStr);
        } else if (period === 'month') {
            const oneMonthAgo = new Date();
            oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
            const oneMonthAgoStr = oneMonthAgo.toISOString().split('T')[0];
            query += ` AND date >= ?`;
            params.push(oneMonthAgoStr);
        }
        
        query += ` ORDER BY date DESC`;
        
        const stmt = db.prepare(query);
        const data = stmt.all(...params);
        
        // 转换数据格式以匹配之前的API
        const formattedData = data.map(item => ({
            id: item.id,
            userId: item.user_id,
            steps: item.steps,
            sleep: item.sleep,
            water: item.water,
            date: item.date,
            createdAt: item.created_at
        }));
        
        res.json(formattedData);
    } catch (error) {
        console.error('获取健康数据时出错:', error);
        res.status(500).json({ error: '获取数据时出错' });
    }
});

// 获取健康数据统计
app.get('/api/health/stats', authenticateToken, (req, res) => {
    const userId = req.user.id;
    
    try {
        // 获取总计数据
        const totalStmt = db.prepare(`
            SELECT 
                SUM(steps) as total_steps,
                AVG(sleep) as avg_sleep,
                SUM(water) as total_water,
                COUNT(*) as days_recorded
            FROM health_data
            WHERE user_id = ?
        `);
        
        const totalStats = totalStmt.get(userId);
        
        // 获取最近7天的数据
        const recentStmt = db.prepare(`
            SELECT date, steps, sleep, water
            FROM health_data
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 7
        `);
        
        const recentData = recentStmt.all(userId);
        
        res.json({
            totalStats: {
                totalSteps: totalStats.total_steps || 0,
                avgSleep: totalStats.avg_sleep || 0,
                totalWater: totalStats.total_water || 0,
                daysRecorded: totalStats.days_recorded || 0
            },
            recentData: recentData.reverse() // 反转以便按日期升序排列
        });
    } catch (error) {
        console.error('获取健康数据统计时出错:', error);
        res.status(500).json({ error: '获取统计数据时出错' });
    }
});

// 任务相关路由
app.get('/api/tasks', authenticateToken, (req, res) => {
    const userId = req.user.id;
    const tasks = readData(TASKS_FILE).filter(task => task.userId === userId);
    res.json(tasks);
});

app.post('/api/tasks', authenticateToken, (req, res) => {
    const userId = req.user.id;
    const { title, description, priority, category, dueDate, reminder } = req.body;
    
    if (!title) {
        return res.status(400).json({ error: '任务标题是必需的' });
    }
    
    const tasks = readData(TASKS_FILE);
    
    const newTask = {
        id: Date.now().toString(), // 使用时间戳作为ID
        userId,
        title,
        description: description || '',
        priority: priority || 'medium',
        category: category || 'life',
        dueDate: dueDate || null,
        reminder: reminder || false,
        completed: false,
        createdAt: new Date().toISOString()
    };
    
    tasks.push(newTask);
    
    if (writeData(TASKS_FILE, tasks)) {
        res.status(201).json(newTask);
    } else {
        res.status(500).json({ error: '保存任务时出错' });
    }
});

app.patch('/api/tasks/:id', authenticateToken, (req, res) => {
    const userId = req.user.id;
    const taskId = req.params.id;
    const { completed } = req.body;
    
    const tasks = readData(TASKS_FILE);
    const taskIndex = tasks.findIndex(task => task.id === taskId && task.userId === userId);
    
    if (taskIndex === -1) {
        return res.status(404).json({ error: '任务未找到' });
    }
    
    tasks[taskIndex].completed = completed;
    
    if (writeData(TASKS_FILE, tasks)) {
        res.json(tasks[taskIndex]);
    } else {
        res.status(500).json({ error: '更新任务时出错' });
    }
});

app.delete('/api/tasks/:id', authenticateToken, (req, res) => {
    const userId = req.user.id;
    const taskId = req.params.id;
    
    const tasks = readData(TASKS_FILE);
    const filteredTasks = tasks.filter(task => !(task.id === taskId && task.userId === userId));
    
    if (tasks.length === filteredTasks.length) {
        return res.status(404).json({ error: '任务未找到' });
    }
    
    if (writeData(TASKS_FILE, filteredTasks)) {
        res.status(204).end();
    } else {
        res.status(500).json({ error: '删除任务时出错' });
    }
});

// 获取用户积分
app.get('/api/user/points', authenticateToken, (req, res) => {
    const userId = req.user.id;
    const users = readData(USERS_FILE);
    const user = users.find(u => u.id === userId);
    
    if (!user) {
        return res.status(404).json({ error: '用户未找到' });
    }
    
    res.json({ points: user.points });
});

// 主页路由
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'login.html'));
});

// 添加一个路由来访问主应用页面
app.get('/smartlife.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'smartlife.html'));
});

// 添加健康数据记录页面路由
app.get('/health-records.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'health-records.html'));
});

// 添加健康与医疗数据页面路由
app.get('/health-medical-info.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'health-medical-info.html'));
});

// 添加一个路由来检查登录状态
app.get('/check-auth', authenticateToken, (req, res) => {
    res.json({ authenticated: true });
});

// 启动服务器
app.listen(PORT, () => {
    console.log(`服务器运行在 http://localhost:${PORT}`);
});

// 验证令牌路由
app.get('/api/auth/verify', authenticateToken, (req, res) => {
    // 如果能通过 authenticateToken 中间件，说明令牌有效
    res.status(200).json({ valid: true });
});

// 关闭应用时关闭数据库连接
process.on('exit', () => {
    db.close();
});

// 健康与医疗数据API
app.get('/api/health-medical-info', authenticateToken, (req, res) => {
    const userId = req.user.id;
    
    try {
        const stmt = db.prepare(`
            SELECT * FROM health_medical_info
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
        `);
        
        const data = stmt.get(userId);
        
        if (!data) {
            return res.json(null);
        }
        
        res.json({
            height: data.height,
            weight: data.weight,
            bloodSugar: data.blood_sugar,
            systolicPressure: data.systolic_pressure,
            diastolicPressure: data.diastolic_pressure,
            heartRate: data.heart_rate,
            medicalHistory: data.medical_history,
            medicationHistory: data.medication_history,
            allergies: data.allergies,
            bloodType: data.blood_type,
            updatedAt: data.updated_at
        });
    } catch (error) {
        console.error('获取健康与医疗数据时出错:', error);
        res.status(500).json({ error: '获取数据时出错' });
    }
});

app.post('/api/health-medical-info', authenticateToken, (req, res) => {
    const userId = req.user.id;
    const {
        height,
        weight,
        bloodSugar,
        systolicPressure,
        diastolicPressure,
        heartRate,
        medicalHistory,
        medicationHistory,
        allergies,
        bloodType
    } = req.body;
    
    try {
        const stmt = db.prepare(`
            INSERT INTO health_medical_info (
                user_id, height, weight, blood_sugar, 
                systolic_pressure, diastolic_pressure, heart_rate,
                medical_history, medication_history, allergies, blood_type, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `);
        
        const now = new Date().toISOString();
        const result = stmt.run(
            userId, 
            height || null, 
            weight || null, 
            bloodSugar || null,
            systolicPressure || null, 
            diastolicPressure || null, 
            heartRate || null,
            medicalHistory || null, 
            medicationHistory || null, 
            allergies || null, 
            bloodType || null,
            now
        );
        
        // 更新用户积分
        const users = readData(USERS_FILE);
        const userIndex = users.findIndex(u => u.id === userId);
        if (userIndex !== -1) {
            users[userIndex].points += 10; // 添加健康与医疗数据奖励10积分
            writeData(USERS_FILE, users);
        }
        
        res.status(201).json({
            id: result.lastInsertRowid,
            userId,
            height,
            weight,
            bloodSugar,
            systolicPressure,
            diastolicPressure,
            heartRate,
            medicalHistory,
            medicationHistory,
            allergies,
            bloodType,
            updatedAt: now
        });
    } catch (error) {
        console.error('保存健康与医疗数据时出错:', error);
        res.status(500).json({ error: '保存数据时出错' });
    }
});