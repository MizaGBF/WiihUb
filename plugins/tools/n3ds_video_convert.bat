@echo off
set inputFile=%~1
set ffmpegPath=ffmpeg.exe
echo %inputFile%
echo %ffmpegPath%
Set COUNTER=0
FOR %%i IN ("%inputFile%") DO (
set filename=%%~ni
)
:loop
set startf=0000%COUNTER%
set startf=%startf:~-2%
set /A COUNTER=COUNTER+1
echo Making %filename%_%COUNTER%.mp4
echo from %startf%:00:00
%ffmpegPath% -ss %startf%:00:00 -t 00:59:59 -i "%inputFile%" -filter:v "scale=-1:360:flags=lanczos, fps=24" -c:v libx264 -qscale:v 4 -c:a aac -b:a 128k %filename%_%COUNTER%.mp4
if exist %filename%_%COUNTER%.mp4 (
echo %filename%_%COUNTER%.mp4> %filename%.txt
goto loop
)
echo Done