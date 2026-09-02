<#
.SINOPSIS
    Inicializa este proyecto como repositorio git, configura Git LFS
    para los rasters de resultados, y lo publica en un repositorio de
    GitHub ya creado.

.USO
    Desde PowerShell, parado en esta misma carpeta:

        .\configurar_repo.ps1 -RemoteUrl "https://github.com/tu-usuario/tu-repo.git"

.REQUISITOS PREVIOS
    - Git para Windows instalado: https://git-scm.com/download/win
    - Git LFS instalado: https://git-lfs.com/
    - Un repositorio VACIO ya creado en GitHub (sin README, .gitignore
      ni licencia, para no generar conflictos con lo que ya trae esta
      carpeta) -- ver README.md, seccion "Publicar el repositorio en
      GitHub (Windows)".

    Si PowerShell bloquea la ejecucion de este script, corre antes
    (una sola vez, solo para esta ventana):

        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$RemoteUrl
)

$ErrorActionPreference = "Stop"

Write-Host "== Verificando Git ==" -ForegroundColor Cyan
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git no esta instalado o no esta en el PATH. Instalalo desde https://git-scm.com/download/win y volve a correr este script."
    exit 1
}

Write-Host "== Verificando Git LFS ==" -ForegroundColor Cyan
if (-not (Get-Command git-lfs -ErrorAction SilentlyContinue)) {
    Write-Warning "Git LFS no parece estar instalado (https://git-lfs.com/). Los .tif que pongas en resultados\rasters\ no se van a versionar correctamente hasta que lo instales y corras 'git lfs install'."
}
else {
    git lfs install
}

if (Test-Path ".git") {
    Write-Warning "Esta carpeta ya es un repositorio git (existe .git\). Se omite 'git init'."
}
else {
    Write-Host "== Inicializando repositorio ==" -ForegroundColor Cyan
    git init
    git branch -M main
}

Write-Host "== Agregando archivos ==" -ForegroundColor Cyan
git add .
git status

$respuesta = Read-Host "Revisa la lista de arriba. Continuar con el commit y push? (s/n)"
if ($respuesta -notmatch "^[sS]") {
    Write-Host "Cancelado. No se hizo commit ni push." -ForegroundColor Yellow
    exit 0
}

git commit -m "Version inicial: procedimiento (Bloques 7-10) y estructura del proyecto"

if (-not (git remote | Select-String -Quiet "^origin$")) {
    git remote add origin $RemoteUrl
}
else {
    Write-Warning "Ya existe un remoto 'origin'; se usa el que ya estaba configurado en vez de $RemoteUrl."
}

git push -u origin main

Write-Host "`nListo. Repositorio inicial publicado." -ForegroundColor Green
Write-Host "Cuando tengas los .tif de resultados, copialos a resultados\rasters\ y corre:"
Write-Host "    git add resultados\rasters\*.tif"
Write-Host "    git commit -m `"Agregar rasters de resultados`""
Write-Host "    git push"
