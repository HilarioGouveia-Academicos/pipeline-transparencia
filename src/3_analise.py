"""Fase 3: agrega a Silver por mês de início e órgão solicitante."""
import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from banco import conectar
from config import PASTA_RAIZ
from gold import executar_gold


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repetir', action='store_true')
    parser.add_argument('--relatorio', type=Path, default=PASTA_RAIZ / 'data/relatorio_gold.json')
    args = parser.parse_args()
    try:
        conn = conectar()
        anterior = None
        try:
            for i in range(2 if args.repetir else 1):
                anterior = executar_gold(conn, esperado=anterior)
                logging.info('Carga Gold %d confirmada: %d grupos', i + 1, anterior['grupos'])
        finally:
            conn.close()
        resultado = {'executado_em': datetime.now(timezone.utc).isoformat(),
                     'cargas_verificadas': i + 1, **anterior}
        args.relatorio.parent.mkdir(parents=True, exist_ok=True)
        args.relatorio.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
        logging.info('Relatório: %s', args.relatorio)
        return 0
    except Exception:
        logging.exception('Falha na Gold; a transação de carga não foi confirmada em caso de erro no banco')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
