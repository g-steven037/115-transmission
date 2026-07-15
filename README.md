# MoviePilot 115 秒传重试

适用于 MoviePilot V2.14.2。插件只调用 115 上传初始化接口判断秒传，不包含完整上传代码。

## 安全处理流程

1. PT 下载目录是必填的受保护目录：仅用于验证隔离关系，绝不扫描、移动或删除。
2. 使用单工作线程和有界队列递归实时监控硬链接目录。
3. 只处理普通硬链接；拒绝单链接文件、符号链接、Junction 和其他重解析点。
4. 秒传成功前后核对设备号、文件 ID/inode、大小、修改时间和链接数，身份一致才删除。
5. 秒传失败后仅允许同文件系统 `os.replace()` 原子移动到临时目录，不进行跨盘复制。
6. 临时目录按 Cron 重试，每轮默认最多 10 个文件；使用最高 24 小时的指数退避和随机抖动。
7. 认证失败立即熔断；限流响应全局暂停一小时。
8. 历史只保存匿名任务 ID 和内部安全码，不保存路径、文件名、Cookie、响应体或原始异常。

## 加密 Cookie

插件拒绝明文 Cookie。配置中只保存 AES-256-GCM 密文，32 字节主密钥必须由只读 Docker Secret 文件（推荐）或环境变量注入，不能写入 MoviePilot 数据库或仓库。

在可信终端执行交互式工具（Cookie 输入不会回显，也不会进入命令行历史）：

```bash
python tools/encrypt_cookie.py
```

工具会要求一个不存在的绝对路径，并以仅所有者可读写权限创建主密钥文件。它不会把主密钥打印到终端。输出内容只有：

- Secret 文件路径：挂载到 MoviePilot 容器并填入“主密钥 Secret 文件绝对路径”。
- `v1.` 开头的密文：填入“加密后的115 Cookie”。

Docker Compose Secret 示例：

```yaml
services:
  moviepilot:
    secrets:
      - p115rapidretry_key
secrets:
  p115rapidretry_key:
    file: /宿主机/安全目录/p115rapidretry.key
```

## 目录要求

- PT、硬链接、临时目录必须是三个互不包含的绝对路径。
- 三个目录必须位于同一文件系统；否则插件拒绝启动。
- 硬链接目录中的文件必须保持至少两个硬链接，避免误删唯一文件。
- 不要把 MoviePilot 配置目录、系统根目录或其他敏感目录配置为监控目录。

## 配置

- `AES-256-GCM 加密后的115 Cookie`：仅接受 `v1.` 密文。
- `主密钥 Secret 文件绝对路径`：推荐 `/run/secrets/p115rapidretry_key`。
- `主密钥环境变量名`：未使用 Secret 文件时默认读取 `P115RAPIDRETRY_KEY`。
- `受保护的PT下载目录`：只校验，不扫描。
- `硬链接实时监控目录`：实时事件来源。
- `失败临时目录`：失败文件的原子移动目标。
- `115目标目录ID`：根目录为 `0`。
- `Cron`：临时目录重试计划。
- `文件稳定等待秒数`：范围 1～3600。
- `每轮最大重试文件数`：范围 1～100。

## 本地一键发布到 GitHub

最简单的方式是直接双击仓库根目录的：

```text
publish-to-github.cmd
```

首次运行会完成 GitHub 登录、Git 提交身份和仓库名设置；以后每次双击都会自动验证、提交并推送。非敏感发布设置保存在本地 `.publish-settings.json`，已被 Git 忽略。Token 不写入仓库。

首次使用先安装 GitHub CLI：

```powershell
winget install --id GitHub.cli
```

首次双击发布脚本时会隐藏提示输入 GitHub Personal Access Token，不再使用浏览器登录。建议使用具有过期时间的 classic Token，并授予 `repo`、`read:org`、`gist`、`workflow` 权限；后续已登录时会直接复用 GitHub CLI 凭据。

如果 `winget` 的 `msstore` 源无法连接，先明确指定社区源：

```powershell
winget install --id GitHub.cli --source winget --accept-source-agreements --accept-package-agreements
```

如果 winget 源仍不可用，可使用仓库内的无管理员权限便携安装器。它只从 GitHub CLI 官方 Release 下载，并使用官方 checksums 文件校验 SHA-256：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-gh-portable.ps1
```

在仓库根目录执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish-github.ps1 `
  -RepoName moviepilot-115-rapid-retry `
  -Visibility public
```

脚本会依次执行秘密扫描、创建隔离虚拟环境、安装锁定依赖、运行 11 项测试、校验版本、初始化 Git、提交、创建或复用 GitHub 仓库，并推送 `main`。如果已有 `origin` 指向其他仓库，脚本会拒绝覆盖。

只检查而不发布：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish-github.ps1 -DryRun
```

发布成功后，终端显示的 GitHub 地址就是 MoviePilot 插件市场地址。仓库中的 GitHub Actions 会在每次推送和拉取请求时重复执行安全扫描与测试。
