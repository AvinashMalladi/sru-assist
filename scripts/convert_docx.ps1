$docx = "C:\Users\GOPAL\Downloads\AURA_Capstone_Final_Report_45Pages.docx"
$pdf  = "C:\Users\GOPAL\Downloads\AURA_Capstone_Final_Report_45Pages.pdf"
$desktopPdf = "C:\Users\GOPAL\OneDrive\Desktop\AURA_Capstone_Final_Report_45Pages.pdf"

if (Test-Path $pdf) { Remove-Item $pdf -Force }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    $doc = $word.Documents.Open($docx, $false, $true)
    $doc.SaveAs([ref]$pdf, [ref]17)
    $doc.Close([ref]0)
    Write-Host "PDF Export Succeeded!"
}
catch {
    Write-Host "Error during conversion: $_"
}
finally {
    $word.Quit([ref]0)
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}

if (Test-Path $pdf) {
    Copy-Item -Path $pdf -Destination $desktopPdf -Force
    Write-Host "Copied PDF to Desktop successfully!"
}
