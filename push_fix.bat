@echo off
set PATH=C:\Program Files\Git\cmd;%PATH%
cd /d "C:\Users\seele\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4f73e8fdb0381cd9354698\xiaoai-home-assistant"

echo === Git status ===
git status
echo.

echo === Add files ===
git add -A
echo.

echo === Commit ===
git commit -m "fix: v0.2.4 - fix xiaomi_miot service name, URL backtick, extra config fields, web dir in Dockerfile

- HomeAssistantClient.execute_text/play_text now support custom service name
- XiaomiSpeakerConfig execute_text_service and play_text_service are now used
- ConfigManager auto-cleans URL backticks and extra config fields
- Dockerfile now copies web/ directory
- routes.py discover_entities improved error handling
- interceptor.py all play_text calls use configured service name"
echo.

echo === Push ===
git push origin main
echo.

echo === Done ===
pause
