# 📊 Análise Completa do Projeto d10r

## 🎯 Visão Geral

d10r = "determinador" - Um gerenciador de tempo e prioridades para pessoas ocupadas/enroladas.

---

## 🏗️ Arquitetura do Sistema

### 1. d10r.py - Módulo Principal
**Propósito:** Lógica de negócio e fluxo principal da aplicação

**Funções principais:**
- main() - Loop principal do programa
- init() - Configuração inicial (primeira execução)
- calcula_prioridades(atividades) - Converte ordem de prioridade em pontos
- escolher_ativ() - Exibe atividades com saldo e permite escolha
- ler_atividades() - Interface para cadastrar atividades
- debitar(atividade) - Registra tempo gasto (cronômetro ou manual)
- menu_cfg() - Menu para criar/escolher arquivo de configuração

**Fluxo de funcionamento:**
1. Carrega configurações (ou cria novas)
2. Credita horas semanalmente baseado no dia configurado
3. Usuário escolhe atividade para trabalhar
4. Cronometra ou insere tempo manualmente
5. Debita tempo do saldo da atividade
6. Salva estado

---

### 2. data.py - Camada de Dados
**Propósito:** Persistência e modelo de dados

**Classes:**
- Collection (metaclass) - Registra automaticamente todas as instâncias de uma classe
- Atividade - Modelo de atividade com:
  - nome - Nome da atividade
  - pts - Percentual de prioridade (0.0 a 1.0)
  - saldo - Horas pendentes (positivo = precisa trabalhar)
  - creditarh(toth, nvezes) - Adiciona horas ao saldo
  - debitarh(horas) - Remove horas do saldo

**Funções:**
- parse_config() - Lê arquivo ~/.d10r e recria atividades
- salvar_config() - Persiste estado em arquivo
- creditar_tudo() - Credita horas em todas as atividades

**Formato de armazenamento:** Arquivo INI em ~/.d10r (UTF-8)

---

### 3. gui.py - Interface Gráfica
**Propósito:** Diálogos e widgets Tkinter customizados

**Classes principais:**

#### CronometroDialog
- Janela de cronômetro em tempo real
- Exibe: tempo decorrido vs saldo
- Botões: Pausar, Finalizar
- Atualização automática a cada 200ms
- Thread assíncrona (Cronometro)

#### HoraSpinDialog
- Interface para entrada manual de tempo
- 3 Spinboxes: horas, minutos, segundos

#### PrioridadeDialog
- Lista ordenável de atividades
- Botões "Subir/Descer" para reordenar
- Define prioridades por ordem

**Funções wrapper (simplificam uso):**
- cronometro_dialog() - Cria cronômetro
- horaspin() - Entrada de tempo
- prioridade_dialog() - Ordenação de prioridades
- notificar(), perguntar(), entrar(), escolher(), menu() - Delegam para easygui

---

### 4. easygui.py - Biblioteca de Diálogos
**Propósito:** Diálogos Tkinter simplificados (biblioteca de terceiros adaptada)

**Funções disponíveis:**
- msgbox() - Mensagem simples
- ynbox() / ccbox() / boolbox() - Perguntas Sim/Não
- buttonbox() - Múltiplos botões
- enterbox() / passwordbox() - Entrada de texto
- integerbox() - Entrada de número
- choicebox() / multchoicebox() - Seleção de lista
- fileopenbox() / filesavebox() / diropenbox() - Seleção de arquivos
- textbox() / codebox() - Exibição de texto
- multenterbox() / multpasswordbox() - Múltiplos campos

---

### 5. utils.py - Utilitários
**Propósito:** Funções auxiliares reutilizáveis

**Funções:**
- plataforma() - Detecta SO (Windows/Linux/Mac)
- formatah(horas) - Converte float → "±HH:MM[:SS]"
- dias_ate_prox_dia(dia, x) - Calcula dias até próximo dia da semana
- dias_x_entre(dia, antes, depois) - Conta ocorrências de um dia da semana entre duas datas

---

## 🔄 Fluxo de Uso

### Primeira Execução
- Não encontra ~/.d10r → chama init()
- Usuário cadastra atividades (mínimo 2)
- Ordena por prioridade (arrastar e soltar)
- Define horas semanais disponíveis
- Sistema calcula percentual de cada atividade
- Salva configuração

### Uso Regular
- Carrega configurações
- Crédito automático: Se passou semana desde último uso, credita horas
- Exibe lista de atividades com saldo
- Usuário escolhe atividade
- Cronometra ou insere tempo manualmente
- Debita tempo do saldo
- Salva estado

---

## 💡 Lógica de Cálculo

### Prioridades
- Ordem de prioridade → pontos → percentual

### Distribuição de Horas
- Horas semanais são distribuídas proporcionalmente entre as atividades

### Saldo
- Positivo: Você deve trabalhar essas horas
- Negativo: Você trabalhou além do esperado
- Zero: Em dia!

---

## 🛠️ Tecnologias
- Python 2.6 (versão antiga - projeto de ~2010)
- Tkinter - GUI nativa
- ConfigParser - Persistência em INI
- Threading - Cronômetro assíncrono
- Pickle - Classe EgStore (não usada atualmente)

---

## ⚠️ Observações

### Pontos Positivos
- Arquitetura bem separada (dados/GUI/lógica)
- Uso de metaclass para gerenciar instâncias
- Persistência simples e legível (INI)
- Interface amigável com diálogos
- Cálculo automático de prioridades

### Pontos de Atenção
- Python 2.6 - MUITO desatualizado (EOL desde 2013)
- Não compatível com Python 3
- Sem testes automatizados
- Arquivo de configuração hardcoded em ~/.d10r
- Sem tratamento de erros robusto
- Código mistura lógica com apresentação em alguns pontos

---

## 🚀 Possíveis Melhorias

1. Migrar para Python 3 (urgente)
2. Modernizar GUI (usar ttk ou PyQt/Kivy)
3. Adicionar testes (unittest/pytest)
4. Banco de dados (SQLite ao invés de INI)
5. Múltiplos perfis de atividades
6. Relatórios e gráficos de produtividade
7. Sincronização cloud
8. App mobile
