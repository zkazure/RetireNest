# RetireNest 开发命令：日常只需要 make dev。Windows 需先安装 GNU make，见 README。
.DEFAULT_GOAL := dev

PORTS := 8000 5173
RUN := uv run --project src python run.py

.PHONY: dev stop help

help:
	@echo RetireNest 开发命令
	@echo make dev — 结束旧进程并启动开发模式（8000 + 5173）
	@echo make dev ARGS=--no-open — 启动时不打开浏览器
	@echo make dev ARGS=--prod — 构建前端后由 8000 单端口演示
	@echo make stop — 只结束监听 8000/5173 的进程
	@echo make stop PORTS=18000 — 只结束指定端口
	@echo 更多参数：uv run --project src python run.py --help

# 先停掉旧进程，避免 run.py 的端口检查直接失败。
dev: stop
	$(RUN) $(ARGS)

stop:
	@$(RUN) --stop --ports $(PORTS)
