@echo off
echo Git Pull Starting...

set REPO_URL=https://github.com/huangxianwu/tktool_byclaude.git

if exist ".git" (
    echo Force updating...
    git fetch origin main
    git reset --hard origin/main
) else (
    echo Initializing...
    git init
    git remote add origin "%REPO_URL%"
    git fetch origin main
    git reset --hard origin/main
)

echo Done.
pause