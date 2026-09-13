import pytest
import datetime
from d10r import calcula_prioridades
import data
import d10r


class AtividadeFake:
    def __init__(self, saldo=2.0):
        self.nome = 'Teste'
        self.saldo = saldo

    def debitarh(self, horas):
        self.saldo -= horas

def test_calcula_prioridades():
    # Lista de atividades ordenadas da mais para a menos prioritária
    atividades_ordenadas = ["Trabalho", "Estudar", "Academia", "Lazer"]
    
    prioridades = calcula_prioridades(atividades_ordenadas)
    
    # A pontuação deve ser:
    # Trabalho (mais prioritário) -> 4 pontos
    # Estudar -> 3 pontos
    # Academia -> 2 pontos
    # Lazer (menos prioritário) -> 1 ponto
    
    assert prioridades["Trabalho"] == 4
    assert prioridades["Estudar"] == 3
    assert prioridades["Academia"] == 2
    assert prioridades["Lazer"] == 1
    assert len(prioridades) == 4


def test_init_credita_primeira_execucao_e_grava_data(monkeypatch):
    primeira_data = datetime.date(2024, 1, 8)
    segunda_data = datetime.date(2024, 1, 9)
    chamadas_data = []

    class DateProbe:
        @classmethod
        def today(cls):
            chamadas_data.append(None)
            return primeira_data if len(chamadas_data) == 1 else segunda_data

    creditos = []
    salvos = []
    monkeypatch.setattr(d10r.datetime, 'date', DateProbe)
    monkeypatch.setattr(d10r.gui, 'notificar', lambda *args: None)
    monkeypatch.setattr(d10r, 'ler_atividades', lambda: {'A', 'B'})
    monkeypatch.setattr(d10r.gui, 'prioridade_dialog',
                        lambda atividades: ['A', 'B'])
    monkeypatch.setattr(d10r.gui, 'entrar', lambda *args: 10)
    monkeypatch.setattr(d10r.gui, 'perguntar', lambda *args: False)
    monkeypatch.setattr(data, 'creditar_tudo',
                        lambda *args: creditos.append(args))
    monkeypatch.setattr(data, 'salvar_config',
                        lambda *args: salvos.append(args))

    d10r.init()

    assert len(chamadas_data) == 1
    assert creditos == [(10, primeira_data.isoweekday(), 0, False)]
    assert salvos == [(10, primeira_data.isoweekday(), primeira_data, False)]


def test_cancelar_escolha_encerra_e_salva(monkeypatch):
    atividade = AtividadeFake()
    monkeypatch.setattr(data, 'parse_config', lambda: (8, 1, 0, True))
    monkeypatch.setattr(data, 'creditar_tudo', lambda *args, **kwargs: False)
    monkeypatch.setattr(data.Atividade, 'all', classmethod(lambda cls: [atividade]))
    monkeypatch.setattr(d10r, 'escolher_ativ', lambda: None)
    salvo = []
    monkeypatch.setattr(data, 'salvar_config', lambda *args: salvo.append(args))
    d10r.main()
    assert atividade.saldo == 2.0
    assert salvo


def test_cancelar_entrada_manual_gera_debito_zero(monkeypatch):
    atividade = AtividadeFake()
    monkeypatch.setattr(d10r.gui, 'menu', lambda *args: 'Inserir')
    monkeypatch.setattr(d10r.gui, 'horaspin', lambda *args: None)
    assert d10r.debitar(atividade) == 0.0


def test_recusar_confirmacao_preserva_saldo(monkeypatch):
    atividade = AtividadeFake()
    escolhas = iter([atividade, None])
    perguntas = iter([False])
    salvo = []
    monkeypatch.setattr(data, 'parse_config', lambda: (8, 1, 0, True))
    monkeypatch.setattr(data, 'creditar_tudo', lambda *args, **kwargs: False)
    monkeypatch.setattr(d10r, 'escolher_ativ', lambda: next(escolhas))
    monkeypatch.setattr(d10r, 'debitar', lambda *args: 1.0)
    monkeypatch.setattr(d10r.gui, 'perguntar', lambda *args: next(perguntas))
    monkeypatch.setattr(data, 'salvar_config', lambda *args: salvo.append(args))
    d10r.main()
    assert atividade.saldo == 2.0
    assert salvo
