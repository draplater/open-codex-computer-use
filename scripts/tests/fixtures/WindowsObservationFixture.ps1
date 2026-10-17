param([Parameter(Mandatory = $true)][string]$StatePath)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName PresentationFramework
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class ObservationDwm {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hwnd, IntPtr after, int x, int y, int width, int height, uint flags);
    [DllImport("dwmapi.dll")]
    public static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);
    [DllImport("dwmapi.dll")]
    public static extern int DwmGetWindowAttribute(IntPtr hwnd, int attr, out int value, int size);
}
"@
$window = New-Object System.Windows.Window
$window.Title = "OCU Windows Observation Fixture"
$window.ShowInTaskbar = $true
$window.Left = 80
$window.Top = 80
$window.Width = 600
$window.Height = 280
$inputBox = New-Object System.Windows.Controls.TextBox
[System.Windows.Automation.AutomationProperties]::SetName($inputBox, "Observation input")
$inputBox.Margin = New-Object System.Windows.Thickness(20)
$inputBox.Height = 30
$inputBox.VerticalAlignment = "Center"
$inputBox.Text = "initial-value"
$window.Content = $inputBox
$state = @{ sequence = 0; text = ""; width = 0; height = 0; minimized = $false; cloakHResult = 0; cloaked = 0 }
$stateEncoding = New-Object System.Text.UTF8Encoding($false)
$commandPath = $StatePath + ".command"
$timer = New-Object System.Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromMilliseconds(50)
$timer.Add_Tick({
    $hwnd = (New-Object System.Windows.Interop.WindowInteropHelper($window)).Handle
    if (Test-Path -LiteralPath $commandPath) {
        try {
            $command = [System.IO.File]::ReadAllText($commandPath) | ConvertFrom-Json
            if ($command.sequence -gt $state.sequence) {
                switch ($command.kind) {
                    "tiny" {
                        $window.WindowStyle = "None"
                        $window.ResizeMode = "NoResize"
                        $window.MinWidth = 0
                        $window.MinHeight = 0
                        $window.Width = 1
                        $window.Height = 1
                        # WPF applies a system minimum even to a borderless
                        # window. Force the native boundary case explicitly.
                        $hwnd = (New-Object System.Windows.Interop.WindowInteropHelper($window)).Handle
                        [void][ObservationDwm]::SetWindowPos($hwnd, [IntPtr]::Zero, 0, 0, 1, 1, 0x16)
                    }
                    "minimize" { $window.WindowState = "Minimized" }
                    "cloak" {
                        $value = 1
                        $state.cloakHResult = [ObservationDwm]::DwmSetWindowAttribute($hwnd, 13, [ref]$value, 4)
                    }
                    "restore" {
                        $value = 0
                        [void][ObservationDwm]::DwmSetWindowAttribute($hwnd, 13, [ref]$value, 4)
                        $window.WindowState = "Normal"
                        $window.WindowStyle = "SingleBorderWindow"
                        $window.ResizeMode = "CanResize"
                        $window.Width = 600
                        $window.Height = 280
                    }
                }
                $state.sequence = $command.sequence
            }
        } catch { }
    }
    $cloaked = 0
    [void][ObservationDwm]::DwmGetWindowAttribute($hwnd, 14, [ref]$cloaked, 4)
    $state.cloaked = $cloaked
    $state.text = $inputBox.Text
    $rect = New-Object ObservationDwm+RECT
    [void][ObservationDwm]::GetWindowRect($hwnd, [ref]$rect)
    $state.width = $rect.Right - $rect.Left
    $state.height = $rect.Bottom - $rect.Top
    $state.minimized = $window.WindowState -eq "Minimized"
    $temporary = $StatePath + ".tmp"
    [System.IO.File]::WriteAllText($temporary, ($state | ConvertTo-Json -Compress), $stateEncoding)
    try {
        if (Test-Path -LiteralPath $StatePath) { [System.IO.File]::Replace($temporary, $StatePath, ($StatePath + ".bak")) }
        else { [System.IO.File]::Move($temporary, $StatePath) }
    } catch [System.IO.IOException] { }
})
$timer.Start()
$window.Add_Closed({ $timer.Stop() })
$application = New-Object System.Windows.Application
$application.ShutdownMode = "OnMainWindowClose"
[void]$application.Run($window)
