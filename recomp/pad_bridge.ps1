# UN4Decomp: ponte do controle (Windows -> jogo no WSL).
# Le o controle de Xbox 360 (ou qualquer controle XInput) no Windows e manda o estado para o jogo por TCP.
# O recomp/run.sh abre este script sozinho; ele fecha quando o jogo fecha.
param([int]$Port = 28862)

$src = @"
using System;
using System.Runtime.InteropServices;
public static class Un4XInput {
  [StructLayout(LayoutKind.Sequential)]
  public struct Gamepad { public ushort wButtons; public byte bLeftTrigger; public byte bRightTrigger; public short sThumbLX; public short sThumbLY; public short sThumbRX; public short sThumbRY; }
  [StructLayout(LayoutKind.Sequential)]
  public struct State { public uint dwPacketNumber; public Gamepad Gamepad; }
  [DllImport("xinput1_4.dll", EntryPoint="XInputGetState")] static extern uint Get14(uint idx, out State st);
  [DllImport("xinput9_1_0.dll", EntryPoint="XInputGetState")] static extern uint Get91(uint idx, out State st);
  static int which = 0;
  public static uint Get(uint idx, out State st) {
    if (which == 0) { try { uint r = Get14(idx, out st); which = 14; return r; } catch (Exception) { which = 91; } }
    if (which == 14) return Get14(idx, out st);
    return Get91(idx, out st);
  }
}
"@
Add-Type -TypeDefinition $src

# espera o jogo abrir a porta (ate 3 minutos)
$client = $null
for ($i = 0; $i -lt 360 -and $client -eq $null; $i++) {
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $c.NoDelay = $true
    $c.Connect("127.0.0.1", $Port)
    $client = $c
  } catch {
    Start-Sleep -Milliseconds 500
  }
}
if ($client -eq $null) { exit 1 }

$stream = $client.GetStream()
$enc = [System.Text.Encoding]::ASCII
$st = New-Object Un4XInput+State
try {
  while ($true) {
    $found = $false
    for ($p = 0; $p -lt 4 -and -not $found; $p++) {
      if ([Un4XInput]::Get([uint32]$p, [ref]$st) -eq 0) { $found = $true }
    }
    if ($found) {
      $g = $st.Gamepad
      $line = "{0} {1} {2} {3} {4} {5} {6}`n" -f $g.wButtons, $g.bLeftTrigger, $g.bRightTrigger, $g.sThumbLX, $g.sThumbLY, $g.sThumbRX, $g.sThumbRY
      $bytes = $enc.GetBytes($line)
      $stream.Write($bytes, 0, $bytes.Length)
      Start-Sleep -Milliseconds 6
    } else {
      # sem controle ligado: so confere se o jogo ainda esta aberto
      if ($client.Client.Poll(0, [System.Net.Sockets.SelectMode]::SelectRead) -and $client.Client.Available -eq 0) { break }
      Start-Sleep -Milliseconds 500
    }
  }
} catch {
} finally {
  $client.Close()
}
