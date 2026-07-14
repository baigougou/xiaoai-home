@echo off
set PATH=C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;%PATH%
cd /d "C:\Users\seele\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4f73e8fdb0381cd9354698\xiaoai-home-assistant"

echo =====================================
echo 创建新的 GitHub 仓库
echo =====================================
echo.

echo [1] 使用 gh-cli 创建新仓库
gh repo create xiaoai-home-assistant-pro --public --description "XiaoAI Home Assistant Bridge - 小爱音箱语音控制 Home Assistant 智能家居" --license MIT
echo.

echo [2] 查看当前远程仓库
git remote -v
echo.

echo [3] 删除旧的远程仓库
git remote remove origin
echo.

echo [4] 添加新的远程仓库
git remote add origin https://github.com/baigougou/xiaoai-home-assistant-pro.git
echo.

echo [5] 查看新的远程仓库
git remote -v
echo.

echo [6] 添加所有文件
git add -A
echo.

echo [7] 提交代码
git commit -m "feat: initial commit - XiaoAI Home Assistant Bridge v0.2.4

Features:
- 支持多个小爱音箱监听
- 语音控制空调(climate)、扫地机器人(vacuum)、灯(light)、开关(switch)、风扇(fan)
- 支持冰箱、洗碗机、洗衣机、烘干机状态查询
- 扫地机器人指定区域清扫
- TTS 语音回复
- 手机通知推送(支持多选)
- Web 配置界面
- 配置热重载"
echo.

echo [8] 推送代码到新仓库
git push -u origin main
echo.

echo =====================================
echo 完成！新仓库已创建: https://github.com/baigougou/xiaoai-home-assistant-pro
echo =====================================
pause
