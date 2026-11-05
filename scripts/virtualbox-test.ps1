param(
    [Parameter(Mandatory = $true)]
    [string]$Iso,
    [string]$VmName = "Corte OS Test",
    [int]$MemoryMB = 2048,
    [int]$Cpus = 2,
    [int]$DiskMB = 20480,
    [switch]$Efi
)

$ErrorActionPreference = "Stop"

function Find-VBoxManage {
    $command = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $candidates = @(
        "$env:ProgramFiles\Oracle\VirtualBox\VBoxManage.exe",
        "${env:ProgramFiles(x86)}\Oracle\VirtualBox\VBoxManage.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    throw "No se encontró VBoxManage. Instala Oracle VirtualBox 7.x o añade VBoxManage al PATH."
}

if (-not (Test-Path -LiteralPath $Iso)) {
    throw "No existe la ISO: $Iso"
}

$isoPath = (Resolve-Path -LiteralPath $Iso).Path
$vbox = Find-VBoxManage
$vmDir = Join-Path $env:USERPROFILE "VirtualBox VMs\$VmName"
$diskPath = Join-Path $vmDir "CorteOS.vdi"

if (Test-Path -LiteralPath $vmDir) {
    throw "Ya existe la máquina virtual '$VmName' en $vmDir. Elimínala o usa otro -VmName."
}

New-Item -ItemType Directory -Force -Path $vmDir | Out-Null

& $vbox createvm --name $VmName --ostype Debian_64 --register --basefolder (Split-Path $vmDir -Parent)
& $vbox modifyvm $VmName --memory $MemoryMB --cpus $Cpus --vram 128 --graphicscontroller vmsvga --accelerate3d off
& $vbox modifyvm $VmName --nic1 nat --audio-enabled on --audio-controller hda --boot1 dvd --boot2 disk
if ($Efi) {
    & $vbox modifyvm $VmName --firmware efi
} else {
    & $vbox modifyvm $VmName --firmware bios
}

& $vbox createmedium disk --filename $diskPath --size $DiskMB --format VDI --variant Standard
& $vbox storagectl $VmName --name "SATA" --add sata --controller IntelAhci --portcount 2 --bootable on
& $vbox storageattach $VmName --storagectl "SATA" --port 0 --device 0 --type hdd --medium $diskPath
& $vbox storagectl $VmName --name "IDE" --add ide --controller PIIX4 --bootable on
& $vbox storageattach $VmName --storagectl "IDE" --port 0 --device 0 --type dvddrive --medium $isoPath

Write-Host "Máquina virtual creada: $VmName"
Write-Host "ISO: $isoPath"
Write-Host "Disco virtual: $diskPath"
Write-Host "Arrancando..."
& $vbox startvm $VmName --type gui
