@echo off
set PATH=C:\Program Files\Git\cmd;%PATH%
cd /d "C:\Users\seele\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4f73e8fdb0381cd9354698\xiaoai-home-assistant"

echo =====================================
echo 推送 main 分支到 GitHub
echo =====================================
echo.

echo [1] 切换到 main 分支
git checkout main
echo.

echo [2] 拉取远程最新代码
git pull origin main
echo.

echo [3] 添加所有更改
git add -A
echo.

echo [4] 提交更改
git commit -m "fix: v0.2.4 - fix xiaomi_miot service name, URL backtick, extra config fields, web dir"
echo.

echo [5] 推送 main 分支
git push origin main
echo.

echo =====================================
echo 完成！main 分支已推送
echo =====================================
pause
