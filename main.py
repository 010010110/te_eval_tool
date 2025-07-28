import argparse
import os
import shutil
from pathlib import Path
from models.classifyte_runner import run_classifyte
from evaluation.metrics import evaluate_model
import csv


def load_tree_map(tree_file: str):
    tree_dict = {}
    with open(tree_file) as f:
        for line in f:
            code, label = line.strip().split(',')
            tree_dict[label.strip()] = code.strip()
    return tree_dict


def extract_actual_labels(fasta_path: str, tree_map: dict, output_csv: str):
    with open(fasta_path) as fasta, open(output_csv, 'w', newline='') as out_csv:
        writer = csv.writer(out_csv)
        writer.writerow(["Sequence ID", "Predicted label", "Actual_Label"])

        for line in fasta:
            if line.startswith(">"):
                parts = line.strip()[1:].split("|")
                if len(parts) != 4:
                    print(f"⚠️ Cabeçalho inválido: {line.strip()}")
                    continue

                seq_id, cls, order, superfamily = parts

                try:
                    cls_key = cls.replace("ClassI", "Retrotransposon").replace("ClassII", "DNA transposon")
                    cls_code = tree_map[cls_key]
                    order_code = tree_map[order]
                    sf_code = tree_map[superfamily]
                except KeyError as e:
                    print(f"⚠️ Rótulo não encontrado no tree.txt: {e}")
                    continue

                actual_label = sf_code
                writer.writerow([seq_id, "", actual_label])

    print(f"✅ Arquivo CSV gerado com rótulos normalizados: {output_csv}")


def prepare_fasta_for_classifyte(input_path: str) -> str:
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"❌ Arquivo .fasta não encontrado: {input_path}")

    target_dir = Path("ClassifyTE/data")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / input_path.name

    if input_path != target_path:
        shutil.copy(input_path, target_path)
        print(f"📁 FASTA copiado para {target_path}")
    else:
        print(f"📁 FASTA já está no local esperado: {target_path}")

    return input_path.name


def main():
    parser = argparse.ArgumentParser(description="Ferramenta de avaliação de classificadores de elementos transponíveis.")
    parser.add_argument('--model', required=True, choices=['classifyte'], help="Modelo a ser executado (atualmente: classifyte).")
    parser.add_argument('--outputs', required=True, help="Diretório onde os resultados e métricas serão salvos.")
    parser.add_argument('--model_file', default='ClassifyTE_combined.pkl', help="Nome do arquivo do modelo (.pkl).")
    parser.add_argument('--node_file', default='node.txt', help="Arquivo de definição de nós hierárquicos.")
    parser.add_argument('--algorithm', default='lcpnb', choices=['lcpnb', 'nllcpn'], help="Algoritmo de avaliação hierárquico.")
    parser.add_argument('--input', default='ClassifyTE/data/default_dataset.fasta',
                        help="Caminho para o arquivo .fasta (padrão: ClassifyTE/data/default_dataset.fasta)")
    parser.add_argument('--tree_file', default='tree.txt', help="Arquivo com hierarquia de rótulos.")

    args = parser.parse_args()

    os.makedirs(args.outputs, exist_ok=True)

    print(f"📦 Rodando modelo '{args.model}' com entrada '{args.input}'...")

    if args.input == 'ClassifyTE/data/default_dataset.fasta':
        print("⚠️ Nenhum .fasta fornecido. Usando dataset padrão: default_dataset.fasta")
        fasta_file = 'default_dataset.fasta'
    else:
        fasta_file = prepare_fasta_for_classifyte(args.input)

    tree_map = load_tree_map(args.tree_file)
    extract_actual_labels(f"ClassifyTE/data/{fasta_file}", tree_map, "output/predicted_out_features_default.csv")

    if args.model == 'classifyte':
        predictions, labels = run_classifyte(
            fasta_file=fasta_file,
            model_name=args.model_file,
            node_file=args.node_file,
            algorithm=args.algorithm
        )
    else:
        raise ValueError("❌ Modelo não suportado.")

    if labels:
        evaluate_model(predictions, labels, args.outputs)
        print(f"\n✅ Resultados e métricas salvos em: {args.outputs}")
    else:
        print("\n⚠️ Nenhum rótulo de verdade encontrado. Apenas previsões foram geradas.")


if __name__ == '__main__':
    main()
