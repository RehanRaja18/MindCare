# Splits the circular mark out of assets/images/mindcare_logo.png into the
# layers the splash animates: mark_figure.png (orange figure), mark_ring.png
# (teal/tan ring) and mark_full.png (untouched), at 2x.
# Run from the repo: powershell -File tool/split_logo.ps1
Add-Type -AssemblyName System.Drawing
$root = Join-Path $PSScriptRoot "..\assets\images"
$outDir = Join-Path $root "splash"
New-Item -ItemType Directory -Force $outDir | Out-Null

$src = [System.Drawing.Bitmap]::new((Join-Path $root "mindcare_logo.png"))
# Mark sits in columns 102-332, rows 18-258; crop with a little margin.
$cx = 87; $cy = 0; $cw = 261; $ch = 269
$crop = $src.Clone([System.Drawing.Rectangle]::new($cx, $cy, $cw, $ch), [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$src.Dispose()

function Smooth([double]$e0, [double]$e1, [double]$x) {
  $t = [Math]::Min(1, [Math]::Max(0, ($x - $e0) / ($e1 - $e0)))
  return $t * $t * (3 - 2 * $t)
}

$fig = [System.Drawing.Bitmap]::new($cw, $ch, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$ring = [System.Drawing.Bitmap]::new($cw, $ch, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
for ($y = 0; $y -lt $ch; $y++) {
  for ($x = 0; $x -lt $cw; $x++) {
    $p = $crop.GetPixel($x, $y)
    if ($p.A -eq 0) { continue }
    $c = [System.Drawing.Color]::FromArgb($p.R, $p.G, $p.B)
    $h = $c.GetHue(); $s = $c.GetSaturation(); $l = $c.GetBrightness()
    # Saturated orange = the figure; teal/charcoal/dull tan = the ring.
    # The figure only lives in the middle of the mark; outside that box
    # everything belongs to the ring. Inside it, catch its soft edges too.
    $inFig = ($x -ge 65) -and ($x -le 195) -and ($y -ge 60) -and ($y -le 245) -and -not (($x -gt 150) -and ($y -lt 100))
    if (-not $inFig) { $w = 0 } else {
    $w = (Smooth 0.22 0.4 $s) * (Smooth 12 20 $h) * (1 - (Smooth 42 50 $h)) * (Smooth 0.25 0.35 $l) }
    $fa = [int][Math]::Round($p.A * $w)
    $ra = [int]$p.A - $fa
    if ($fa -gt 0) { $fig.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($fa, $p.R, $p.G, $p.B)) }
    if ($ra -gt 0) { $ring.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($ra, $p.R, $p.G, $p.B)) }
  }
}

function Save2x($bmp, $name) {
  $big = [System.Drawing.Bitmap]::new($bmp.Width * 2, $bmp.Height * 2, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [System.Drawing.Graphics]::FromImage($big)
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
  $g.DrawImage($bmp, 0, 0, $big.Width, $big.Height)
  $g.Dispose()
  $big.Save((Join-Path $outDir $name), [System.Drawing.Imaging.ImageFormat]::Png)
  $big.Dispose()
}

Save2x $crop "mark_full.png"
Save2x $fig "mark_figure.png"
Save2x $ring "mark_ring.png"
$crop.Dispose(); $fig.Dispose(); $ring.Dispose()
Get-ChildItem $outDir | Select-Object Name, Length
