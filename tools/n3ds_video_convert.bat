@echo off
set inputFile=%~1
set ffmpegPath=ffmpeg.exe
echo %inputFile%
echo %ffmpegPath%
Set COUNTER=0
FOR %%i IN ("%inputFile%") DO (
set filename=%%~ni
)
del temp.txt
:loop
set startf=0000%COUNTER%
set startf=%startf:~-2%
set /A COUNTER=COUNTER+1
echo Making %filename%_%COUNTER%.mp4
echo from %startf%:00:00
%ffmpegPath% -y -ss %startf%:00:00 -t 00:59:59 -i "%inputFile%" -filter:v "scale=-1:360:flags=lanczos, fps=24" -c:v libx264 -c:a aac -b:a 128k %filename%_%COUNTER%.mp4 > temp.txt 2>&1
>nul find "video:0kB audio:0kB " temp.txt && (
  del temp.txt
  del %filename%_%COUNTER%.mp4
) || (
  del temp.txt
  echo %filename%_%COUNTER%.mp4>> %filename%.txt
  goto loop
)
echo Done