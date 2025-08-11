#  Bunker 地堡

![Bunker ASCII Art](https://raw.githubusercontent.com/goxofy/bunker/main/bunker.png)

一个您可以自行托管的、个人的 IPFS 文件钉（Pinning）服务。Bunker 提供了一种简单且安全的方式，将您的重要文件钉在您自己的 IPFS 节点上，以确保它们在 IPFS 网络上持久可用。它由一个轻量级的 Python 后端和一个用户友好的命令行界面（CLI）组成。

## ✨ 功能特性

- **自行托管**: 完全控制您的文件和 IPFS 节点，数据掌握在自己手中。
- **简洁的 API**: 一个基于 FastAPI 的轻量级后端，用于处理所有核心钉选逻辑。
- **友好的 CLI**: 一个直观的命令行工具，用于上传、列出和移除已钉选的文件。
- **丰富的交互体验**: 精美的 ASCII 艺术字标题和清晰的文件分析，提供更佳的用户体验。
- **轻量化**: 使用最少的现代 Python 库构建，保持项目简洁高效。

## 🏗️ 项目架构

Bunker 由两个核心部分组成：

1.  **FastAPI 后端 (`main.py`)**: 一个简单的 Web 服务器，它暴露了用于与您的 IPFS 守护进程交互的 API 端点。它负责处理添加、钉选、取消钉选和列出文件的核心逻辑。
2.  **Click 命令行 (`cli.py`)**: 一个与 FastAPI 后端通信的命令行界面。这是您将直接在终端中用来管理文件的工具。

## ✅ 环境要求

- Python 3.8+
- 一个正在运行的 IPFS 节点（可以通过 [IPFS Desktop](https://ipfs.io/desktop/) 或 [IPFS Kubo 命令行守护进程](https://github.com/ipfs/kubo) 启动）。
- 您的 IPFS 守护进程必须处于运行状态且 API 端口可访问。

## 🚀 安装与设置

请按照以下步骤来安装并运行 Bunker。

**1. 克隆代码仓库**

```bash
git clone https://github.com/goxofy/bunker.git
cd bunker
```

**2. 创建并激活 Python 虚拟环境**

我们强烈建议您使用虚拟环境来管理项目的依赖。

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境 (在 macOS/Linux 上)
source venv/bin/activate

# 在 Windows 上, 请使用:
# venv\Scripts\activate
```

**3. 安装依赖**

```bash
pip install -r requirements.txt
```

## ⚙️ 使用方法

要使用 Bunker，您需要在一个终端中运行后端服务，然后在另一个终端中使用命令行工具。

**第一步：运行后端服务**

在您的第一个终端窗口中，启动 FastAPI 服务器。请确保您的 IPFS 守护进程已经启动。

```bash
# 在终端 1 (已激活虚拟环境)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

您应该能看到类似下面的输出，表明服务器已成功运行：
`Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)`

**请保持这个终端窗口持续运行。**

**第二步：使用命令行工具**

打开一个**新的终端窗口**，并同样激活虚拟环境。现在您就可以使用 `bunker` 的命令行了。

**上传一个文件：**

```bash
# 在终端 2
python cli.py upload <你的文件路径/file.txt>
```

**列出所有已钉选的文件：**

```bash
# 在终端 2
python cli.py list
```

**通过 CID 移除（取消钉选）一个文件：**

```bash
# 在终端 2
python cli.py remove <你的文件的_ipfs_hash_cid>
```

## 🔧 配置信息

为了保持项目简洁，当前的服务配置是硬编码在代码中的：

-   **后端 IPFS 守护进程地址**: 在 `main.py` 文件中, `IPFS_API_ADDR` 被设置为 `/ip4/127.0.0.1/tcp/5001`。
-   **CLI 后端服务 URL**: 在 `cli.py` 文件中, `BASE_URL` 当前被设置为一个生产环境的 URL。如果您在本地开发，应将其修改为 `http://127.0.0.1:8000/api/v2`。

## 🤝 如何贡献

欢迎各种贡献、问题反馈和功能建议！请随时在 [Issues 页面](https://github.com/goxofy/bunker/issues)提出。

## 📄 许可证

本项目采用 MIT 许可证。详情请见 `LICENSE` 文件。
