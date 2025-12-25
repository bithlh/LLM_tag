# Gunicorn配置文件 - 单进程模式
import multiprocessing

# 服务器配置
bind = "127.0.0.1:5000"
backlog = 2048

# 工作进程配置
workers = 1  # 单进程模式，避免文件锁冲突
worker_class = "sync"  # 同步工作类
worker_connections = 1000
timeout = 30
keepalive = 2

# 重启配置
max_requests = 1000
max_requests_jitter = 50

# 日志配置
loglevel = "info"
accesslog = "logs/access.log"
errorlog = "logs/error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = 'llm_tag_system'

# 服务器机制
preload_app = True  # 预加载应用
pidfile = "logs/gunicorn.pid"

# 应用配置
pythonpath = "."  # 当前目录
wsgi_module = "app:app"
