# Pilotage du jeu de test : touches simulees seulement si la fenetre du jeu est au premier plan.
param([string[]]$Touches = @(), [string]$Png, [int]$Pause = 400, [int]$Tenue = 120, [string]$Rogne, [string]$JusquaChangement, [int]$Essais = 6)
Add-Type -AssemblyName System.Drawing
if (-not ('P4' -as [type])) {
Add-Type -ReferencedAssemblies System.Drawing @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Drawing;
public static class P4 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte sc, uint f, UIntPtr e);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint c, uint t);
  public struct RECT { public int L, T, R, B; }
  public static IntPtr Find(string cls) { IntPtr found = IntPtr.Zero;
    EnumWindows((h, l) => { var c = new StringBuilder(256); GetClassName(h, c, 256);
      if (c.ToString() == cls) { found = h; return false; } return true; }, IntPtr.Zero); return found; }
  public static void Shot(IntPtr h, string path) { RECT r; GetWindowRect(h, out r);
    using (var b = new Bitmap(r.R - r.L, r.B - r.T)) { using (var g = Graphics.FromImage(b)) g.CopyFromScreen(r.L, r.T, 0, 0, b.Size);
      using (var s = new Bitmap(b, b.Width / 2, b.Height / 2)) s.Save(path); } }
  public static long Sig(IntPtr h) { RECT r; GetWindowRect(h, out r); long s = 0;
    using (var b = new Bitmap(r.R - r.L, r.B - r.T)) { using (var g = Graphics.FromImage(b)) g.CopyFromScreen(r.L, r.T, 0, 0, b.Size);
      for (int y = 40; y < b.Height; y += 23) for (int x = 0; x < b.Width; x += 29) { var c = b.GetPixel(x, y); s += (c.R + 2 * c.G + c.B) * (x % 7 + 1); } }
    return s; }
  public static void Crop(IntPtr h, string path, int x, int y, int w, int hh) { RECT r; GetWindowRect(h, out r);
    using (var b = new Bitmap(w, hh)) { using (var g = Graphics.FromImage(b)) g.CopyFromScreen(r.L + x, r.T + y, 0, 0, b.Size); b.Save(path); } }
}
"@
}
$jeu = [P4]::Find('ps3recomp_d3d12')
if ($jeu -eq [IntPtr]::Zero) { "pas de fenetre de jeu"; return }
$codes = @{ 'haut'=0x57; 'bas'=0x53; 'gauche'=0x41; 'droite'=0x44; 'croix'=0x20; 'rond'=0x08; 'start'=0x0D; 'Q'=0x51; 'E'=0x45; 'select'=0x09 }
if ($JusquaChangement) {
  $t = $JusquaChangement; $vk = [byte]$codes[$t]; $sc = [byte][P4]::MapVirtualKey($vk, 0)
  for ($i = 1; $i -le $Essais; $i++) {
    if ([P4]::GetForegroundWindow() -ne $jeu) { [void][P4]::SetForegroundWindow($jeu); Start-Sleep -Milliseconds 300 }
    if ([P4]::GetForegroundWindow() -ne $jeu) { "ARRET : pas au premier plan"; return }
    $avant = [P4]::Sig($jeu)
    [P4]::keybd_event($vk, $sc, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds $Tenue
    [P4]::keybd_event($vk, $sc, 2, [UIntPtr]::Zero); Start-Sleep -Milliseconds $Pause
    $apres = [P4]::Sig($jeu)
    if ([math]::Abs($apres - $avant) -gt [math]::Abs($avant) / 200) { "touche $t prise a l'essai $i"; break }
    if ($i -eq $Essais) { "touche $t : aucun changement apres $Essais essais" }
  }
}
foreach ($t in $Touches) {
  if ([P4]::GetForegroundWindow() -ne $jeu) { [void][P4]::SetForegroundWindow($jeu); Start-Sleep -Milliseconds 300 }
  if ([P4]::GetForegroundWindow() -ne $jeu) { "ARRET : la fenetre du jeu n'est pas au premier plan (touche $t non envoyee)"; return }
  $vk = [byte]$codes[$t]; $sc = [byte][P4]::MapVirtualKey($vk, 0)
  [P4]::keybd_event($vk, $sc, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds $Tenue
  [P4]::keybd_event($vk, $sc, 2, [UIntPtr]::Zero); Start-Sleep -Milliseconds $Pause
  "touche $t"
}
if ($Rogne) { $z = [int[]]($Rogne -split ','); [P4]::Crop($jeu, $Png, $z[0], $z[1], $z[2], $z[3]); "rognage $Png"; return }
if ($Png) { if ([P4]::GetForegroundWindow() -ne $jeu) { [void][P4]::SetForegroundWindow($jeu); Start-Sleep -Milliseconds 300 }; [P4]::Shot($jeu, $Png); "capture $Png" }


