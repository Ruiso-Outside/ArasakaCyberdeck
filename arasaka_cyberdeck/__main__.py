"""
ARASAKA CYBERDECK // ponto de entrada.

  arasaka-cyberdeck            abre a barra de busca (de novo: fecha)
  arasaka-cyberdeck --toggle   o mesmo (usado pelo atalho de teclado)
"""
import sys

from .app import main

if __name__ == "__main__":
    sys.exit(main(sys.argv))
