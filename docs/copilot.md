# GitHub Copilot e autoria
O repositório contém `.github/copilot-instructions.md`, instruções para testes e um prompt de revisão. Abra a pasta no VS Code com sua conta/licença Copilot. No Chat, peça:

> Leia as instruções do repositório. Revise a atomicidade de Outbox e Inbox, rode os testes e proponha um PR com uma melhoria demonstrável, mantendo o escopo do desafio.

Depois:

> Execute o prompt review-cashflow. Mostre quais requisitos foram comprovados e quais dependem do ambiente de produção.

Verifique nas referências da resposta se as instruções foram carregadas. Revise o diff, rode CI e registre o PR. Nunca envie tokens ou dados financeiros reais ao assistente de programação.

**Proveniência:** solução preparada com assistência do ChatGPT/Codex. GitHub Copilot não foi executado nesta entrega. Os arquivos habilitam seu uso posterior; não constituem evidência de uso. Anthropic em runtime é outra integração, independente de Copilot.

Referência: https://docs.github.com/en/copilot/how-tos/copilot-in-your-ide/customize-copilot/configure-custom-instructions/add-repository-instructions-in-your-ide
