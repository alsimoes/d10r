import pytest
from utils import formatah, dias_x_entre
import datetime

def test_formatah():
    # Testa formatação padrão (sem segundos, com sinal)
    assert formatah(2.5) == '+02:30'
    assert formatah(-1.75) == '-01:45'
    assert formatah(0) == '00:00'

    # Testa com segundos
    assert formatah(1.255, segundos=True) == '+01:15:18'

    # Testa sem sinal
    assert formatah(3.0, sinal=False) == '03:00'
    assert formatah(-2.25, sinal=False) == '02:15'

def test_dias_x_entre():
    # Testa a contagem de dias da semana entre duas datas
    # Ex: Quantas segundas-feiras (1) entre 1 e 15 de janeiro de 2024
    d_inicio = datetime.date(2024, 1, 1)
    d_fim = datetime.date(2024, 1, 15)
    # Dias 1, 8, 15 são segundas-feiras
    assert dias_x_entre(1, d_inicio, d_fim) == 3

    # Ex: Quantas sextas-feiras (5) no mesmo período
    # Dias 5, 12 são sextas-feiras
    assert dias_x_entre(5, d_inicio, d_fim) == 2


def test_cronometro_sem_fim():
    from utils import Cronometro
    assert Cronometro(None).fim is None
    assert Cronometro(None, True).fim is None


def test_cronometro_marca_fim_alcancado():
    from utils import Cronometro
    c = Cronometro(0, True)
    c.run()  # síncrono: o fim já foi atingido na primeira verificação
    assert c.isparado
    assert c.fim_alcancado
