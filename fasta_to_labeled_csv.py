import csv
from pathlib import Path

def fasta_to_eval_csv(fasta_path, outputs_csv):
    fasta_path = Path(fasta_path)
    outputs_csv = Path(outputs_csv)

    if not fasta_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {fasta_path}")

    records = []
    with open(fasta_path, 'r') as f:
        seq_id = None
        label = None
        sequence = ''
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if seq_id:
                    records.append((seq_id, label, sequence))
                    sequence = ''
                header = line[1:]
                if "|" in header:
                    seq_id, label = header.split("|", 1)
                else:
                    seq_id = header
                    label = ''
            else:
                sequence += line
        if seq_id:
            records.append((seq_id, label, sequence))

    with open(outputs_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Sequence ID', 'Actual_Label'])  # required for step 3
        for seq_id, label, _ in records:
            writer.writerow([seq_id, label])

    print(f"✅ CSV de avaliação salvo em: {outputs_csv} com {len(records)} entradas.")


if __name__ == "__main__":
    # Exemplo:
    fasta_to_eval_csv("data/demo.fasta", "ClassifyTE/outputs/predicted_result.csv")
