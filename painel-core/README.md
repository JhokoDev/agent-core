# Interface do Harvey

Código editável da interface atual, compartilhado para reutilização em outro agente.

## Conteúdo

React 18, TypeScript, Vite, Lucide e componentes de voz LiveKit. Inclui tema, navegação, conversa, histórico, notas, personalização, áudio, habilidades, autorizações e painéis de computador/navegador.

Este pacote contém somente o frontend. Não contém backend, credenciais, arquivos .env, banco, notas pessoais, conversas, logs, sessões autenticadas, node_modules ou arquivos de teste do navegador.

## Executar

Instale Node.js com npm. O projeto original foi verificado com Node.js 24.

No terminal, dentro desta pasta:

```powershell
npm ci
npm run dev
```

Abra http://localhost:3000. Para compilar:

```powershell
npm run build
```

## Integrar com seu agente

A interface não inclui um agente funcional independente. Sem uma API compatível, as telas dependentes de dados exibem indisponibilidade e a conversa por voz não conecta.

- `src/services/api.ts`: contrato HTTP e operações de sessões, notas, perfil e capacidades.
- `src/contracts.ts`: contratos da interface e da conversa.
- `src/composition.ts`: seleção de implementações e componente de conversa.
- `src/voice/LiveKitConversation.tsx`: integração atual com LiveKit. Substitua o componente respeitando `ConversationProps` caso use outro transporte.
- `src/services/desktop.ts`: comunicação autenticada com o componente local de computador.
- `src/services/clientEvents.ts`: envio de eventos do cliente ao backend.
- `src/ui/`: telas e painéis; alguns chamam `/api/automation`, `/api/desktop` e outras rotas diretamente. Adaptar apenas `services/api.ts` não cobre todos esses acessos.
- `src/styles/index.css`: cores, tipografia, espaçamento e estilos.
- `public/favicon.svg`, `index.html` e textos nos componentes: identidade visual e nome Harvey.

`vite.config.ts` encaminha `/api` para http://localhost:8080 durante o desenvolvimento. Ajuste o destino para sua API. Em produção, configure o encaminhamento correspondente no servidor que hospedar a interface.

Para voz, o backend deve emitir o token de curta duração esperado pela interface. Não coloque chaves do modelo nem segredos LiveKit no frontend. Controle nativo de computador e navegador requer componentes adicionais; eles não fazem parte deste ZIP.

Você pode reutilizar o design e remover os painéis que não correspondem às capacidades do seu agente. Preserve os avisos e condições de licença das bibliotecas de terceiros utilizadas.

## Integridade

`MANIFEST.sha256` registra os hashes dos arquivos entregues. O ZIP foi verificado por CRC e comparado com o código original. A compilação do frontend original passou antes da exportação; não foram feitas alterações no projeto para criar este pacote.
