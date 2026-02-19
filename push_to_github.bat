@echo off
echo Initializing Git repository...
git init
git add .
git commit -m "Initial commit of HLS YouTube Release Backend"
git branch -M main
echo Setting remote to https://github.com/wwwvasanth507-create/ok ...
git remote add origin https://github.com/wwwvasanth507-create/ok
echo pushing to repository...
git push -u origin main
echo Done! If asked for credentials, use your GitHub Token as password.
pause
