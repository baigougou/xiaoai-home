@echo off
set PATH=C:\Program Files\Git\cmd;%PATH%
cd /d "C:\Users\seele\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4f73e8fdb0381cd9354698\xiaoai-home-assistant"

echo === STEP 1: Remove old origin ===
git remote remove origin

echo === STEP 2: Add new origin ===
git remote add origin https://github.com/baigougou/xiaoai-home.git

echo === STEP 3: Verify remotes ===
git remote -v

echo === STEP 4: Add all files ===
git add -A

echo === STEP 5: Commit ===
git commit -m "feat: initial commit v0.2.4"

echo === STEP 6: Push to new repo ===
git push -u origin main

echo === DONE ===
pause