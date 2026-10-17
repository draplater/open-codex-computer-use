param([Parameter(Mandatory = $true)][string]$StatePath)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class ObservationDwm {
    [DllImport("dwmapi.dll")]
    public static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);
    [DllImport("dwmapi.dll")]
    public static extern int DwmGetWindowAttribute(IntPtr hwnd, int attr, out int value, int size);
}
"@
$form = New-Object System.Windows.Forms.Form
$form.Text = "OCU Windows Observation Fixture"
$form.StartPosition = "Manual"
$form.Location = New-Object System.Drawing.Point(80, 80)
$form.ClientSize = New-Object System.Drawing.Size(600, 280)
$inputBox = New-Object System.Windows.Forms.TextBox
$inputBox.AccessibleName = "Observation input"
$inputBox.Location = New-Object System.Drawing.Point(20, 50)
$inputBox.Size = New-Object System.Drawing.Size(400, 30)
$inputBox.Text = "initial-value"
$form.Controls.Add($inputBox)
$state = @{ sequence = 0; text = ""; width = 0; height = 0; minimized = $false; cloakHResult = 0; cloaked = 0 }
$stateEncoding = New-Object System.Text.UTF8Encoding($false)
$commandPath = $StatePath + ".command"
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 50
$timer.Add_Tick({
    if (Test-Path -LiteralPath $commandPath) {
        try {
            $command = [System.IO.File]::ReadAllText($commandPath) | ConvertFrom-Json
            if ($command.sequence -gt $state.sequence) {
                switch ($command.kind) {
                    "tiny" {
                        $form.FormBorderStyle = "None"
                        $form.MinimumSize = New-Object System.Drawing.Size(0, 0)
                        $form.Size = New-Object System.Drawing.Size(1, 1)
                    }
                    "minimize" { $form.WindowState = "Minimized" }
                    "cloak" {
                        $value = 1
                        $state.cloakHResult = [ObservationDwm]::DwmSetWindowAttribute($form.Handle, 13, [ref]$value, 4)
                    }
                    "restore" {
                        $value = 0
                        [void][ObservationDwm]::DwmSetWindowAttribute($form.Handle, 13, [ref]$value, 4)
                        $form.WindowState = "Normal"
                        $form.FormBorderStyle = "Sizable"
                        $form.ClientSize = New-Object System.Drawing.Size(600, 280)
                        $form.Location = New-Object System.Drawing.Point(80, 80)
                    }
                }
                $state.sequence = $command.sequence
            }
        } catch { }
    }
    $cloaked = 0
    [void][ObservationDwm]::DwmGetWindowAttribute($form.Handle, 14, [ref]$cloaked, 4)
    $state.cloaked = $cloaked
    $state.text = $inputBox.Text
    $state.width = $form.Width
    $state.height = $form.Height
    $state.minimized = $form.WindowState -eq "Minimized"
    $temporary = $StatePath + ".tmp"
    [System.IO.File]::WriteAllText($temporary, ($state | ConvertTo-Json -Compress), $stateEncoding)
    try {
        if (Test-Path -LiteralPath $StatePath) { [System.IO.File]::Replace($temporary, $StatePath, $null) }
        else { [System.IO.File]::Move($temporary, $StatePath) }
    } catch [System.IO.IOException] { }
})
$timer.Start()
$form.Add_FormClosed({ $timer.Stop() })
[System.Windows.Forms.Application]::Run($form)
