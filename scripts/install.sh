#!/bin/bash
# PAI-DSW CLI 安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/usr/local/bin"
CLI_NAME="dsw"

echo "🔧 安装 PAI-DSW CLI..."

# 检查 Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip3 install -q alibabacloud-pai-dsw20220101 requests 2>/dev/null || true

# 创建符号链接
echo "🔗 创建命令链接..."
ln -sf "${SCRIPT_DIR}/dsw.py" "${INSTALL_DIR}/${CLI_NAME}"
chmod +x "${SCRIPT_DIR}/dsw.py"

# 验证安装
if command -v dsw &> /dev/null; then
    echo "✅ 安装成功！"
    echo ""
    echo "使用方法:"
    echo "  dsw list              # 列出所有实例"
    echo "  dsw get <name|id>     # 查询实例详情"
    echo "  dsw search <keyword>  # 搜索实例"
    echo "  dsw specs             # 查看可用规格"
    echo "  dsw --help            # 查看帮助"
    echo ""
    echo "从任意目录运行 'dsw --help' 获取完整命令列表。"
else
    echo "⚠️ 安装完成，但 'dsw' 命令可能不在 PATH 中"
    echo "请确保 ${INSTALL_DIR} 在您的 PATH 中"
fi