# Atualizar e salvar PC-MAO no GitHub (PowerShell)

O ZIP distribuído contém os arquivos do projeto, mas **não inclui `.git`**. Não rode comandos Git dentro da pasta extraída. Copie os arquivos atualizados para o clone original, que contém `.git`.

## 1. Confirmar a pasta clonada

```powershell
$repo = "$HOME\Downloads\PC-MAO"
Test-Path "$repo\.git"
```

O resultado precisa ser `True`. Se for `False`, localize a pasta onde executou `git clone`; não inicialize outro repositório sobre a pasta extraída.

## 2. Copiar a atualização extraída para o clone

Extraia o ZIP para uma pasta separada, por exemplo `PC-MAO-atualizado`. Troque esse caminho pela pasta real onde descompactou:

```powershell
$update = "$HOME\Downloads\PC-MAO-atualizado"
robocopy $update $repo /E /XD .git .venv __pycache__ .pytest_cache
```

Confirme a raiz antes de prosseguir:

```powershell
Set-Location $repo
Get-Location
Test-Path .\.git
```

## 3. Testar, salvar e enviar

```powershell
python -m pytest -q
git status --short
git add -A
git diff --cached
git commit -m "Finaliza gestos, calibração e perfis do PC-MAO"
git push -u origin main
```

`git commit` grava a versão no computador. `git push` envia os commits ao GitHub. Revise `git diff --cached` antes do commit. Os perfis pessoais ficam em `%USERPROFILE%\.pc-mao\profiles.json`, fora do repositório.

## Clonar pela primeira vez

```powershell
Set-Location "$HOME\Downloads"
git clone https://github.com/duartin/PC-MAO.git
Set-Location "$HOME\Downloads\PC-MAO"
```

## Se o push for recusado

Não use `git push --force`. Atualize com `git pull --rebase origin main`, resolva conflitos, rode os testes e tente novamente.
