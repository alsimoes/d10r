'''Configuração compartilhada do pytest.'''

import os

# Permite rodar os testes de interface sem servidor gráfico (CI, SSH, etc.)
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest


@pytest.fixture(scope='session')
def qapp():
    '''Instância única de QApplication para os testes de interface.'''
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
