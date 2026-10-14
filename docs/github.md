# Publicação pública no GitHub

O desafio exige URL pública. O pacote não foi publicado nesta sessão: o conector disponível consulta/edita repositórios existentes, mas não oferece criação de repositório. A conta consultada foi `ncamaraljrai`; confirmar o proprietário ao publicar. Nenhum repositório existente foi alterado.

## Opção com GitHub CLI no seu computador

Na raiz extraída, com git e gh instalados e autenticados:

```bash
git init -b main
git add .
git diff --cached --stat
# Revise os arquivos: nunca adicionar .env, bancos ou dados reais.
git commit -m "Implement cashflow challenge with clean architecture and optional RAG"
gh auth login
# Cria um repositório público e envia o conteúdo revisado.
gh repo create cashflow-clean-architecture --public --source=. --remote=origin --push
```

Se o nome já existir, escolha outro ou use repositório vazio explicitamente autorizado. Não force push em histórico existente. Alternativa: crie repositório público vazio pelo GitHub e use `git remote add origin <URL>` + `git push -u origin main`.

## Após publicar

1. Confirmar que README/diagramas renderizam e o repositório é público.
2. Aguardar os jobs de testes e containers. Corrigir falhas reais antes de enviar o link ao avaliador.
3. Ativar proteção de branch e exigir checks, revisão e bloqueio de secrets conforme recursos da conta.
4. Usar as instruções e prompt Copilot, registrando o PR se quiser demonstrar uso real.
5. Escolher licença com o autor; visibilidade pública não implica automaticamente licença de redistribuição.
6. Enviar ao avaliador a URL pública, o commit avaliado e as instruções de execução.

Se preferir que o assistente publique via conector, forneça a URL de um repositório público vazio com acesso de escrita; não é necessário compartilhar token no chat.
