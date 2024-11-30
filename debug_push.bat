@echo off
:retry
git add .
git commit -m "debug"
git push
if %errorlevel% neq 0 (
    echo FAILED TO PUSH
    timeout /t 10
    goto retry
) else (
    echo SUCCESSFULLY PUSHED
)
