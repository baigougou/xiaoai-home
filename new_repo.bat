@echo off
set PATH=C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;%PATH%
cd /d "C:\Users\seele\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4f73e8fdb0381cd9354698\xiaoai-home-assistant"

echo === STEP 1: Create new repo ===
gh repo create xiaoai-home-assistant-pro --public --description "XiaoAI HA Bridge" --license MIT

echo === STEP 2: Remove old remote ===
git remote remove origin

echo === STEP 3: Add new remote ===
git remote add origin https://github.com/baigougou/xiaoai-home-assistant-pro.git

echo === STEP 4: Show remotes ===
git remote -v

echo === STEP 5: Add and commit ===
git add -A
git commit -m "feat: initial commit v0.2.4"

echo === STEP 6: Push to new repo ===
git push -u origin main

echo === DONE ===
pause