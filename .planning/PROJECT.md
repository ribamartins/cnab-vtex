# CNAB PIX Payment System

## What This Is

Aplicacao desktop standalone para criacao de arquivos bancarios CNAB 240 (SISPAG Itau) para pagamentos PIX. O usuario importa uma planilha Excel com beneficiarios, o sistema consulta a API VTEX para obter dados completos, gera o arquivo CNAB no formato exigido pelo Itau, e disponibiliza para download manual no Itau Empresas. Destinado a equipe financeira da PrettyNew.

## Core Value

Gerar arquivos CNAB PIX validos sem erros — cada pagamento deve chegar ao beneficiario correto com o valor correto.

## Current State

**Shipped: v1.0 MVP (2026-03-31)**

Aplicacao desktop funcional com fluxo completo: login, importacao Excel, enriquecimento VTEX, validacao, geracao CNAB, download .txt, dashboard com filtros, detalhes de arquivo, log de auditoria, exclusao de arquivos. 4.887 linhas Python, 167 testes automatizados, 8/8 UAT aprovados.

## Requirements

### Validated

- [x] Deteccao automatica do tipo de chave PIX (CPF/CNPJ, telefone, email, chave aleatoria) — v1.0
- [x] Geracao de arquivo CNAB 240 SISPAG Itau para PIX Transferencia — v1.0
- [x] Validacao previa dos dados do beneficiario e chave PIX antes de gerar o CNAB — v1.0
- [x] Autenticacao simples (login com usuario/senha, poucos usuarios) — v1.0
- [x] Tela de configuracoes para dados da empresa pagadora (CNPJ, agencia, conta, DAC Itau) — v1.0
- [x] Upload de arquivo Excel com colunas: Nome do Beneficiario, Codigo (referenceId), Valor — v1.0
- [x] Consulta a API VTEX (MasterData) para cada linha do Excel usando referenceId — v1.0
- [x] Armazenamento de arquivos e metadados/status no banco de dados — v1.0
- [x] Dashboard de status com lista de arquivos gerados, filtros por data e status — v1.0
- [x] Log de auditoria (quem gerou, erros ocorridos) — v1.0
- [x] Exclusao de arquivos CNAB com status Criado ou Erro — v1.0

### Active

- [ ] Processamento de arquivo retorno do Itau para confirmar pagamentos efetivados (v2)

### Out of Scope

- Pagamento via boleto/DOC/TED — apenas PIX Transferencia
- Geracao de arquivo retorno (apenas leitura/processamento do retorno recebido do Itau)
- Multi-empresa / multi-banco — apenas Itau, uma empresa por instalacao
- App mobile ou web — apenas desktop standalone
- Transmissao via API bancaria — Itau nao oferece API para envio de CNAB; upload manual via Itau Empresas

## Context

- **VTEX MasterData**: API em `prettynew.myvtex.com/api/dataentities/VV/search` retorna dados do beneficiario incluindo `pixKey`, `document`, `firstName`, `lastName`, `email`, `homePhone`. Autenticacao via X-VTEX-API-AppKey + X-VTEX-API-AppToken.
- **CNAB 240 SISPAG Itau v085**: Registros de 240 bytes. Para PIX, arquivo separado com: Header Arquivo (tipo 0), Header Lote (tipo 1, forma 45=PIX Transferencia), Segmento A (detalhe obrigatorio), Segmento B PIX (obrigatorio para PIX com chave), Trailer Lote (tipo 5), Trailer Arquivo (tipo 9).
- **PIX via chave**: Segmento A posicao 18-20 = "009" (camara PIX/SPI), posicao 113-114 = "04" (Chave Pix). Segmento B PIX: tipo chave (01=Tel, 02=Email, 03=CPF/CNPJ, 04=Aleatoria) e chave PIX (ate 100 chars).
- **Envio CNAB**: Upload manual do arquivo .txt no Itau Empresas (nao via API).
- **Documentacao CNAB**: Disponivel em `./Documents/sispag_cnab.md` (convertido do PDF original).
- **Tech stack**: Python 3.12+, PySide6 6.10.1, SQLAlchemy 2.0.48, SQLite, openpyxl, httpx. DB em `~/.cnab-pix/data.db`.

## Constraints

- **Stack**: Python + PySide6 (Qt) — aplicacao desktop standalone
- **Banco**: SQLite local para metadados e status dos arquivos
- **Seguranca**: Credenciais VTEX criptografadas via Fernet, nunca hardcoded
- **CNAB**: Cada registro exatamente 240 bytes, encoding LATIN-1, campos numericos com zeros a esquerda, alfanumericos com espacos a direita
- **Usuarios**: Equipe pequena (1-5 pessoas), autenticacao local simples

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + PySide6 (Qt) desktop | Aplicacao standalone, sem necessidade de servidor web, distribuicao simples | Validated v1.0 |
| SQLite local | BD embarcado, zero configuracao, suficiente para equipe pequena | Validated v1.0 |
| Chave PIX como modelo padrao | Campo `pixKey` da VTEX pode conter qualquer tipo de chave, deteccao automatica do tipo | Validated v1.0 |
| Banco de dados para controle de arquivos | Mais robusto que filesystem puro, facilita consultas, dashboard e auditoria | Validated v1.0 |
| Arquivo CNAB separado para PIX | Obrigatorio conforme documentacao SISPAG — PIX nao pode ser misturado com outras formas | Validated v1.0 |
| Upload manual no Itau Empresas | Itau nao oferece API para envio CNAB; sistema gera .txt para upload manual | Validated v1.0 |
| Service layer sem commit | cnab_service functions fazem flush mas nunca commit — caller controla transacao | Validated v1.0 |
| Fernet para credenciais VTEX | Criptografia simetrica com chave derivada — protege AppKey/AppToken em repouso | Validated v1.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-31 after v1.0 milestone*
