# RetireNest 开发命令：日常只需要 make dev。
SHELL := /bin/bash
.DEFAULT_GOAL := dev

PORTS := 8000 5173
RUN := uv run --project src python run.py

.PHONY: dev stop help

help:
	@echo "make dev             结束旧进程并启动开发模式（8000 + 5173）"
	@echo "make dev ARGS=...    透传给 run.py，例如 ARGS=--no-open"
	@echo "make stop            只结束监听 8000/5173 的进程"

# 先停掉旧进程，避免 run.py 的端口检查直接失败。
dev: stop
	$(RUN) $(ARGS)

stop:
	@for port in $(PORTS); do \
		pids=$$(lsof -ti tcp:$$port -sTCP:LISTEN || true); \
		if [ -n "$$pids" ]; then \
			echo "[make] 停止端口 $$port：$$pids"; \
			kill $$pids 2>/dev/null || true; \
		fi; \
	done; \
	for port in $(PORTS); do \
		for _ in 1 2 3 4 5 6 7 8 9 10; do \
			lsof -ti tcp:$$port -sTCP:LISTEN >/dev/null 2>&1 || break; \
			sleep 0.2; \
		done; \
		left=$$(lsof -ti tcp:$$port -sTCP:LISTEN || true); \
		if [ -n "$$left" ]; then \
			echo "[make] 强制结束端口 $$port：$$left"; \
			kill -9 $$left 2>/dev/null || true; \
		fi; \
	done
