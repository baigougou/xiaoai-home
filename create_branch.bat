@echo off
set PATH=C:\Program Files\Git\cmd;%PATH%
cd /d "C:\Users\seele\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4f73e8fdb0381cd9354698\xiaoai-home-assistant"

echo =====================================
echo 创建新分支并推送到 GitHub
echo =====================================
echo.

echo [1] 查看当前分支
git branch
echo.

echo [2] 创建并切换到新分支 fix/v0.2.4
git checkout -b fix/v0.2.4
echo.

echo [3] 查看当前分支
git branch
echo.

echo [4] 添加所有更改
git add -A
echo.

echo [5] 提交更改
git commit -m "fix: v0.2.4 - fix xiaomi_miot service name, URL backtick, extra config fields"
echo.

echo [6] 推送新分支到 GitHub
git push -u origin fix/v0.2.4
echo.

echo [7] 推送 main 分支
git checkout main
git push origin main
echo.

echo =====================================
echo 完成！新分支 fix/v0.2.4 已推送
echo =====================================
pause
