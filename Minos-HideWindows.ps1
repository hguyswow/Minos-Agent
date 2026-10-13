# Minos-HideWindows.ps1
# Start-Minos.bat이 모듈을 실행한 후 이 스크립트를 호출합니다.
# 일정 시간 후 Dashboard / Bot 창을 자동으로 최소화합니다.

param(
    [int]$DelaySeconds = 6   # 몇 초 후 숨길지 (기본 6초)
)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinHelper {
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    
    public const int SW_MINIMIZE  = 6;
    public const int SW_HIDE      = 0;
    public const int SW_SHOWNA    = 8;
}
"@

Start-Sleep -Seconds $DelaySeconds

$titles = @("Minos Dashboard - http://localhost:5000", "Minos Telegram Bot")

foreach ($title in $titles) {
    $hwnd = [WinHelper]::FindWindow($null, $title)
    if ($hwnd -ne [IntPtr]::Zero) {
        [WinHelper]::ShowWindow($hwnd, [WinHelper]::SW_MINIMIZE)
    }
}

# 프로세스 이름으로도 추가 시도
Get-Process | Where-Object {
    $_.MainWindowTitle -like "*Minos*" -or $_.MainWindowTitle -like "*Dashboard*"
} | ForEach-Object {
    if ($_.MainWindowHandle -ne 0) {
        [WinHelper]::ShowWindow($_.MainWindowHandle, [WinHelper]::SW_MINIMIZE) | Out-Null
    }
}
