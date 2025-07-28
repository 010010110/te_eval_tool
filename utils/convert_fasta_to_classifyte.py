def convert_fasta_to_classifyte_format(input_fasta, output_fasta, tree_file="tree.txt"):
    import re

    # 1. Carregar árvore de mapeamento semântico -> hierárquico
    label_map = {}
    with open(tree_file, 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    code, name = parts
                    label_map[name.lower()] = code

    def map_label(components):
        # Tenta usar a última parte primeiro
        for part in reversed(components):
            label = part.strip().lower()
            if label in label_map:
                return label_map[label]
        return None  # Se nenhum mapeamento encontrado

    # 2. Reescrever FASTA
    with open(input_fasta, 'r') as fin, open(output_fasta, 'w') as fout:
        for line in fin:
            if line.startswith(">"):
                parts = line.strip()[1:].split("|")
                seq_id = parts[0]
                mapped_label = map_label(parts[1:])
                if mapped_label:
                    fout.write(f">{seq_id}|{mapped_label}\n")
                else:
                    print(f"⚠️ Rótulo não mapeado: {line.strip()}")
                    fout.write(f">{seq_id}|UNK\n")  # Pode usar 'UNK' ou pular
            else:
                fout.write(line)
