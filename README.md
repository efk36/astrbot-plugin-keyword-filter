# AstrBot + SnowLuma QQ 机器人部署（Ubuntu 24.04 / Docker Compose）

架构：SnowLuma（OneBot v11 实现端，跑 QQ 客户端）→ 反向 WebSocket → AstrBot（WS 服务端）→ LLM

## 0. 环境自检（先把结果发我）

```bash
uname -m                 # 架构：x86_64 或 aarch64
nproc                    # CPU 核数
free -h                  # 内存（建议 ≥ 2G）
df -h /                  # 磁盘剩余（建议 ≥ 10G）
docker compose version   # 确认有 compose v2
docker info | grep -E "Server Version|Architecture|Cgroup"
sudo systemctl enable --now docker
```

## 1. 准备目录

```bash
sudo mkdir -p /opt/qqbot && cd /opt/qqbot
```

把同目录下的 `compose.yml` 放到 `/opt/qqbot/compose.yml`。

```bash
cd /opt/qqbot
ls -l compose.yml
docker compose config >/dev/null && echo "compose 语法 OK"
```

## 2. 启动

```bash
cd /opt/qqbot
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=50
```

国内拉取慢时，编辑 compose.yml 把镜像换成代理源：

- `motricseven7/snowluma:latest` → `m.daocloud.io/docker.io/motricseven7/snowluma:latest`
- `soulter/astrbot:latest` → `m.daocloud.io/docker.io/soulter/astrbot:latest`

## 3. QQ 登录

```bash
# 取 noVNC password
docker logs snowluma 2>&1 | grep -aE "远程桌面密码|remote desktop password" | tail -n 1

# 取 WebUI 临时密码
docker logs snowluma 2>&1 | grep -aE "临时密码|initial credentials" | tail -n 1

# 校验 ptrace 能力（应含 cap_sys_ptrace=ep）
docker exec snowluma getcap /usr/local/bin/node
```

浏览器打开 `http://<服务器IP>:6081/` → 输入 VNC 密码 → 进入远程桌面 → 扫码登录 QQ。

再打开 `http://<服务器IP>:5099/` → 输入 WebUI 密码 → 进入 SnowLuma 配置界面。

AstrBot WebUI：`http://<服务器IP>:6185/`，默认用户名 `astrbot`，密码 `astrbot`。

## 4. 配置 SnowLuma 反向 WebSocket

方式 A（推荐，WebUI）：SnowLuma WebUI → 网络配置 → 新建 → WebSockets 客户端：

| 字段 | 值 |
|---|---|
| name | `astrbot` |
| url | `ws://astrbot:6199/ws` |
| role | `Universal` |
| enabled | `true` |
| accessToken | 留空（与 AstrBot 一致） |

方式 B（文件）：编辑 `/app/data/config/onebot.json`（宿主机用 `docker exec` 或 volume 挂载目录）：

```json
{
  "wsClients": [
    {
      "name": "astrbot",
      "enabled": true,
      "url": "ws://astrbot:6199/ws",
      "role": "Universal",
      "reconnectIntervalMs": 5000,
      "messageFormat": "array",
      "reportSelfMessage": false
    }
  ]
}
```

改完 `docker restart snowluma`。

> 注意：url 里的 `astrbot` 是 compose 网络内的服务名，不要填 `127.0.0.1`。

## 5. 配置 AstrBot OneBot v11

AstrBot WebUI → 平台管理 → OneBot v11 (aiocqhttp)：

| 字段 | 值 |
|---|---|
| 启用 | ✅ |
| 反向 WebSocket 主机地址 | `0.0.0.0` |
| 反向 WebSocket 端口 | `6199` |
| 反向 WebSocket Token | 留空 |

保存后 AstrBot 日志应出现平台连接成功的日志。

## 6. 配置 LLM provider

AstrBot WebUI → 服务提供商 → 添加（如 OpenAI 兼容接口）：

- api_base：你的中转/官方地址
- api_key
- model：模型名

再到「功能配置」里开启对话功能，确认 wake prefix（默认 `/`）。

## 7. 验证

```bash
# 容器状态
docker compose -f /opt/qqbot/compose.yml ps

# SnowLuma 是否已连上 AstrBot
docker logs snowluma --tail=100 | grep -ai "astrbot\|ws"

# AstrBot 侧是否收到事件
docker logs astrbot --tail=100

# OneBot HTTP 连通性
curl -s http://127.0.0.1:3000/get_status_info
```

在 QQ 上对机器人发消息，应收到回复。

## 8. 日常运维

```bash
cd /opt/qqbot
docker compose logs -f astrbot      # 看 AstrBot 日志
docker compose logs -f snowluma     # 看 SnowLuma 日志
docker compose restart astrbot      # 重启
docker compose pull && docker compose up -d   # 升级（保留数据卷）
docker compose down                 # 停止（保留数据卷）
```

**切勿 `docker compose down -v`**，会删掉 QQ 登录态。

## 9. 防火墙

已按用户要求全部监听 0.0.0.0，若启用了 ufw：

```bash
sudo ufw allow 6185/tcp
sudo ufw allow 6081/tcp
sudo ufw allow 5099/tcp
# 3000/3001 是 OneBot 接口，无需公网暴露，可不对外开放
```

## 10. 排障

| 现象 | 原因 / 处理 |
|---|---|
| QQ 扫码后掉线 | 服务器在境外或 IP 被风控；给容器配代理后再试 |
| AstrBot 收不到消息 | 检查 SnowLuma 的 wsClients url 是否为 `ws://astrbot:6199/ws`；两端 token 是否一致 |
| `docker exec snowluma getcap` 无输出 | compose 里 `--cap-add=SYS_PTRACE` / `seccomp=unconfined` 缺失 |
| AstrBot WebUI 打不开 | `docker logs astrbot` 看是否启动异常；确认 6185 未被占用 |
| 修改 compose 后不生效 | `docker compose up -d --force-recreate` |
