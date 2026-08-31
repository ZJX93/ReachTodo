# ============================================
# Reach-Todo · 单体单镜像多阶段构建
# 前端(React/Vite)在阶段 1 构建，产物拷入 server/public，
# 由阶段 2 的 FastAPI 在单端口(8000)同源托管。
# 参照 XIN-Wallet 的“单镜像单体”思路，保留 Python(FastAPI)+React 技术栈。
# 由 .github/workflows/publish.yml 在推送 v*.*.* tag 时触发。
# ============================================

# ---- 阶段 1：构建前端 ----
FROM node:22-alpine AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
# 使用 npmmirror 镜像源加速；用 npm install 而非 npm ci：
# 在 package.json 与 lock 短暂不同步时（如新增依赖）也能正常安装，
# 与 CI 的 frontend job 保持一致，避免 CI 因 lock 漂移直接失败。
RUN npm config set registry https://registry.npmmirror.com && npm install
COPY web ./
# 版本号由 publish.yml 通过 build-arg 传入（取 Android Release 的 X.Y.Z），
# 注入为 VITE_APP_VERSION 供前端“关于”页在构建时读取并展示。
ARG APP_VERSION=""
ENV VITE_APP_VERSION=${APP_VERSION}
RUN npm run build
# 构建产物位于 /web/dist

# ---- 阶段 2：Python 运行时 ----
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY server/requirements.lock ./requirements.lock
COPY server/requirements.txt ./requirements.txt
RUN sed -i '/mirrors.aliyun.com/d' requirements.lock requirements.txt 2>/dev/null; \
    pip install --no-cache-dir -r requirements.lock \
        || pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.lock \
        || pip install --no-cache-dir -r requirements.txt

COPY server/app ./app
COPY server/alembic ./alembic
COPY server/alembic.ini ./alembic.ini
COPY server/scripts ./scripts

# 前端构建产物 → server/public（与 app 同级，即 /app/public，由 main.py 托管）
COPY --from=web-build /web/dist ./public

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
