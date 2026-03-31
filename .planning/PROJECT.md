# CNAB PIX Payment System

## What This Is

Aplicação desktop standalone para criação e transmissão de arquivos bancários CNAB 240 (SISPAG Itaú) para pagamentos PIX. O usuário importa uma planilha Excel com beneficiários, o sistema consulta a API VTEX para obter dados completos, gera o arquivo CNAB no formato exigido pelo Itaú, e transmite via API bancária. Destinado à equipe financeira da PrettyNew.

## Core Value

Gerar arquivos CNAB PIX válidos e transmiti-los ao Itaú sem erros — cada pagamento deve chegar ao beneficiário correto com o valor correto.

## Requirements

### Validated

- [x] Detecção automática do tipo de chave PIX (CPF/CNPJ, telefone, email, chave aleatória) — Validated in Phase 1: CNAB Engine
- [x] Geração de arquivo CNAB 240 SISPAG Itaú para PIX Transferência (Header Arquivo, Header Lote, Segmento A + Segmento B PIX, Trailer Lote, Trailer Arquivo) — Validated in Phase 1: CNAB Engine
- [x] Validação prévia dos dados do beneficiário e chave PIX antes de gerar o CNAB — Validated in Phase 1: CNAB Engine
- [x] Autenticação simples (login com usuário/senha, poucos usuários) — Validated in Phase 2: Foundation
- [x] Tela de configurações para dados da empresa pagadora (CNPJ, agência, conta, DAC Itaú) — Validated in Phase 2: Foundation
- [x] Upload de arquivo Excel com colunas: Nome do Beneficiário, Código (referenceId), Valor — Validated in Phase 3: Data Pipeline
- [x] Consulta à API VTEX (MasterData) para cada linha do Excel usando referenceId — Validated in Phase 3: Data Pipeline
- [x] Armazenamento de arquivos e metadados/status no banco de dados (status: Criado, Transmitido, Erro) — Validated in Phase 4: Desktop Application
- [x] Movimentação de status: Criado → Transmitido (sucesso) ou Erro (falha), com log de erro — Validated in Phase 4: Desktop Application
- [x] Dashboard de status com lista de arquivos gerados, filtros por data e status — Validated in Phase 4: Desktop Application
- [x] Log de auditoria (quem gerou, quando transmitiu, erros ocorridos) — Validated in Phase 4: Desktop Application

### Active

- [ ] Processamento de arquivo retorno do Itaú para confirmar pagamentos efetivados (v2)
- [ ] Transmissão real do arquivo para o Itaú via API bancária (v2 — sem credenciais ainda)

### Out of Scope

- Pagamento via boleto/DOC/TED — apenas PIX Transferência
- Geração de arquivo retorno (apenas leitura/processamento do retorno recebido do Itaú)
- Multi-empresa / multi-banco — apenas Itaú, uma empresa por instalação
- App mobile ou web — apenas desktop standalone

## Context

- **VTEX MasterData**: API em `prettynew.myvtex.com/api/dataentities/VV/search` retorna dados do beneficiário incluindo `pixKey`, `document`, `firstName`, `lastName`, `email`, `homePhone`. Autenticação via X-VTEX-API-AppKey + X-VTEX-API-AppToken.
- **CNAB 240 SISPAG Itaú v085**: Registros de 240 bytes. Para PIX, arquivo separado com: Header Arquivo (tipo 0), Header Lote (tipo 1, forma 45=PIX Transferência), Segmento A (detalhe obrigatório), Segmento B PIX (obrigatório para PIX com chave), Trailer Lote (tipo 5), Trailer Arquivo (tipo 9).
- **PIX via chave**: Segmento A posição 18-20 = "009" (câmara PIX/SPI), posição 113-114 = "04" (Chave Pix). Segmento B PIX: tipo chave (01=Tel, 02=Email, 03=CPF/CNPJ, 04=Aleatória) e chave PIX (até 100 chars).
- **API Itaú**: Credenciais ainda não disponíveis. Transmissão será implementada com mock/stub inicialmente, substituído por integração real quando houver acesso.
- **Documentação CNAB**: Disponível em `./Documents/sispag_cnab.md` (convertido do PDF original).

## Constraints

- **Stack**: Python + PySide6 (Qt) — aplicação desktop standalone
- **Banco**: SQLite local para metadados e status dos arquivos
- **Segurança**: Credenciais VTEX e Itaú em arquivo de configuração local criptografado ou protegido, nunca hardcoded
- **CNAB**: Cada registro exatamente 240 bytes, encoding conforme padrão FEBRABAN, campos numéricos com zeros à esquerda, alfanuméricos com espaços à direita
- **Usuários**: Equipe pequena (1-5 pessoas), autenticação local simples

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + PySide6 (Qt) desktop | Aplicação standalone, sem necessidade de servidor web, distribuição simples | — Pending |
| SQLite local | BD embarcado, zero configuração, suficiente para equipe pequena | — Pending |
| Chave PIX como modelo padrão | Campo `pixKey` da VTEX pode conter qualquer tipo de chave, detecção automática do tipo | — Pending |
| Banco de dados para controle de arquivos | Mais robusto que filesystem puro, facilita consultas, dashboard e auditoria | — Pending |
| API Itaú com mock inicial | Sem credenciais disponíveis, começar com stub para não bloquear desenvolvimento | — Pending |
| Arquivo CNAB separado para PIX | Obrigatório conforme documentação SISPAG — PIX não pode ser misturado com outras formas | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-31 — Phase 4 complete, all v1 milestone phases delivered*
