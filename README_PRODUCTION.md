# LLM标签筛选系统 - 生产环境部署指南

## 概述

本系统已针对生产环境进行了优化，包括：
- ✅ 文件锁机制：防止多用户并发操作时的文件损坏
- ✅ 单进程Flask部署：稳定的生产环境服务器
- ✅ 跨平台兼容：支持Linux和Windows部署

## 环境要求

- Python 3.8+
- pip包管理器

## 安装依赖

```bash
pip install -r requirements.txt
```

## 生产环境启动

### Linux/macOS

```bash
chmod +x start_production.sh
./start_production.sh
```

### Windows

双击运行 `start_production.bat` 文件，或在命令行中执行：

```cmd
start_production.bat
```

## 服务配置

- **绑定地址**: `0.0.0.0:8000`
- **工作进程**: 1个（单进程模式，避免文件锁冲突）
- **线程模式**: 启用（threaded=True）
- **调试模式**: 关闭（debug=False）
- **文件锁**: portalocker文件锁定机制

## 安全特性

### 文件锁机制

系统使用 `portalocker` 库实现跨平台文件锁定：

- **读取操作**: 使用共享锁（LOCK_SH），允许多个进程同时读取
- **写入操作**: 使用独占锁（LOCK_EX），确保只有一个进程可以写入
- **锁失败重试**: 如果获取锁失败，自动等待后重试

### 单进程部署

采用单进程模式确保：
- 文件操作的原子性
- 避免多进程间的文件锁竞争
- 简化部署和调试

## 监控和维护

### 查看服务状态

```bash
# 检查Flask进程是否运行
ps aux | grep python

# Windows下检查进程
tasklist | findstr python
```

### 重启服务

```bash
# 停止服务 (Ctrl+C 或查找进程ID后kill)
# 重启服务
./start_production.sh
```

## 故障排除

### 常见问题

1. **端口占用**
   ```bash
   # 检查端口使用情况
   netstat -tlnp | grep 8000
   # 修改gunicorn.conf.py中的bind配置
   ```

2. **权限问题**
   ```bash
   # 确保日志目录权限
   chmod 755 logs/
   ```

3. **依赖问题**
   ```bash
   # 重新安装依赖
   pip install --upgrade -r requirements.txt
   ```

## 开发环境

如需在开发环境中运行：

```bash
python app.py
```

开发服务器将在 `http://127.0.0.1:5000` 启动，包含调试功能。

## 文件结构

```
LLM_tag/
├── app.py                    # 主应用文件
├── gunicorn.conf.py          # Gunicorn配置
├── start_production.sh       # Linux启动脚本
├── start_production.bat      # Windows启动脚本
├── requirements.txt          # 依赖列表
├── data/                     # 数据存储目录
├── static/                   # 静态文件
├── templates/                # HTML模板
└── logs/                     # 日志文件（自动创建）
```
