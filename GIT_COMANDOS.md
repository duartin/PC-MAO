# Comandos Git — PC-MAO

Repositório remoto: `https://github.com/duartin/PC-MAO.git`
Branch de trabalho: `main`

## Baixar o repositório pela primeira vez

```bash
git clone https://github.com/duartin/PC-MAO.git
cd PC-MAO
```

Se o repositório for privado, autentique-se pelo método configurado no seu Git antes de clonar.

## Atualizar sua cópia com a versão mais recente

Execute dentro da pasta `PC-MAO`:

```bash
git switch main
git pull --rebase origin main
```

## Salvar e enviar suas próprias alterações

Depois de copiar/editar os arquivos e revisar as mudanças:

```bash
git status
git add -A
git diff --cached
git commit -m "Descreva a atualização"
git push origin main
```

O `git commit` salva a versão no seu computador. O `git push` envia os commits para o GitHub.

## Verificar versão e histórico

```bash
git log --oneline --decorate -10
git status --short --branch
```

## Criar uma versão marcada (opcional)

Depois de fazer commit e antes/depois do push:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Use uma tag nova a cada versão (por exemplo `v0.1.1`, `v0.2.0`). Não reutilize uma tag já publicada.

## Se o push for recusado

Não use `git push --force`. Primeiro atualize com `git pull --rebase origin main`, resolva conflitos, rode os testes e então tente `git push origin main` novamente.
