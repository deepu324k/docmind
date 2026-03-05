@echo off
title DocuMind - AI Document Intelligence
echo.
echo  ====================================
echo   DocuMind - Starting Server...
echo  ====================================
echo.

cd /d D:\documind

echo  Starting DocuMind on http://127.0.0.1:5000
echo  Press Ctrl+C to stop the server.
echo.

start "" http://127.0.0.1:5000

"C:\Users\ASUS\AppData\Local\Programs\Python\Python313\python.exe" app.py

pause
