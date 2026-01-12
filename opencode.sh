#!/bin/bash
# Superpowers for OpenCode - 完整安装脚本

echo "=== 安装 Superpowers for OpenCode ==="

# 第一步：克隆 Superpowers 仓库
echo "[1/4] 克隆 Superpowers 仓库..."
mkdir -p ~/.config/opencode/superpowers
git clone https://github.com/obra/superpowers.git ~/.config/opencode/superpowers

# 第二步：创建插件目录并注册插件
echo "[2/4] 注册插件..."
mkdir -p ~/.config/opencode/plugin
ln -sf ~/.config/opencode/superpowers/.opencode/plugin/superpowers.js \\
       ~/.config/opencode/plugin/superpowers.js

# 第三步：创建个人技能目录
echo "[3/4] 创建个人技能目录..."
mkdir -p ~/.config/opencode/skills

# 第四步：验证安装
echo "[4/4] 验证安装..."
if [ -f ~/.config/opencode/plugin/superpowers.js ]; then
    echo "✅ 插件链接创建成功"
else
    echo "❌ 插件链接创建失败"
    exit 1
fi

if [ -d ~/.config/opencode/superpowers/skills ]; then
    echo "✅ 技能目录存在"
    echo "   可用技能数量: $(ls ~/.config/opencode/superpowers/skills | wc -l)"
else
    echo "❌ 技能目录不存在"
    exit 1
fi

echo ""
echo "=== 安装完成！==="
echo ""
echo "下一步操作："
echo "1. 重启 OpenCode"
echo "2. 在对话中输入: do you have superpowers?"
echo "3. 使用 find_skills 工具查看可用技能"
echo "4. 使用 use_skill 工具加载技能"
echo ""
echo "示例命令："
echo "  use find_skills tool"
echo "  use use_skill tool with skill_name: \\"superpowers:brainstorming\\""
