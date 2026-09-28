"""Fase 2: carga tipada, relacional e auditável da Silver."""
import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

from banco import conectar
from config import PASTA_RAIZ, TAMANHO_BLOCO
from silver import executar_silver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repetir', action='store_true')
    parser.add_argument('--relatorio', type=Path, default=PASTA_RAIZ/'data/relatorio_silver.json')
    args = parser.parse_args()
    try:
        conn = conectar()
        anterior = None
        try:
            for i in range(2 if args.repetir else 1):
                resumo = executar_silver(conn, TAMANHO_BLOCO, esperado=anterior)
                if anterior is not None and resumo != anterior:
                    raise ValueError('A reexecução apresentou resultados diferentes; confira se a Raw mudou entre as cargas')
                anterior = resumo
                logging.info('Carga Silver %d confirmada',i+1)
        finally:
            conn.close()
        args.relatorio.parent.mkdir(parents=True,exist_ok=True)
        resultado = {'executado_em':datetime.now(timezone.utc).isoformat(),'cargas_verificadas':i+1,'tabelas':resumo}
        args.relatorio.write_text(json.dumps(resultado,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
        logging.info('Relatório: %s',args.relatorio)
        return 0
    except Exception:
        logging.exception('Falha na Fase 2')
        return 1


if __name__=='__main__':
    sys.exit(main())
