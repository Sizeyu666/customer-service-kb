#!/usr/bin/env bash
# =============================================================
# 企业客服知识库系统 · 云服务器一键部署脚本（Ubuntu 22.04）
# 用法：chmod +x deploy/deploy.sh && sudo bash deploy/deploy.sh
# 说明：脚本在服务器上执行；先手动完成 git clone（见 README 部署章节）
# =============================================================
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/customer-service-kb}

echo "==> 1/4 初始化系统依赖（Docker）"
if ! command -v docker >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
if ! docker compose version >/dev/null 2>&1; then
  apt-get install -y docker-compose-plugin
fi

echo "==> 2/4 准备 .env（SECRET_KEY 自动生成）"
cd "$APP_DIR"
if [ ! -f .env ]; then
  cp .env.example .env
  NEW_KEY=$(openssl rand -hex 32)
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${NEW_KEY}|" .env
  echo "已生成 .env，请手动补充：DEEPSEEK_API_KEY、MYSQL_PASSWORD 等配置"
  echo "    nano ${APP_DIR}/.env"
fi

echo "==> 3/4 创建数据目录并启动"
mkdir -p data/uploads data/vector_store hf_cache
docker compose up -d --build

echo "==> 4/4 完成"
echo "查看日志：  docker compose logs -f app"
echo "停止：      docker compose down"
echo "更新发布：  cd ${APP_DIR} && git pull && docker compose up -d --build"
echo "访问：      http://服务器公网IP/"
