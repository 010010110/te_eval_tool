import os
import subprocess
import pandas as pd
from pathlib import Path


def setup_classifyte_env():
    env_path = Path("model_envs/classifyte_env")
    requirements_path = Path("ClassifyTE/requirements.txt")

    if not env_path.exists():
        print("🔧 Creating virtual environment for ClassifyTE...")
        subprocess.run(["python3.9", "-m", "venv", str(env_path)], check=True)

    python_path = env_path / "bin" / "python"
    if not python_path.exists():
        python_path = env_path / "bin" / "python3"

    if not python_path.exists():
        raise FileNotFoundError(f"❌ Could not find Python interpreter in {env_path}/bin")

    pip_path = python_path.parent / "pip"
    try:
        subprocess.run([pip_path, "show", "scikit-learn"], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("📦 Installing dependencies...")
        subprocess.run([pip_path, "install", "-r", str(requirements_path)], check=True)

    return str(python_path)


def run_classifyte(fasta_file, model_name="ClassifyTE_combined.pkl", node_file="node.txt", algorithm="lcpnb"):
    base_dir = Path("ClassifyTE")
    data_path = base_dir / "data" / fasta_file

    if not data_path.exists():
        raise FileNotFoundError(f"FASTA file not found at {data_path}")

    python_path = setup_classifyte_env()

    fasta_basename = os.path.splitext(fasta_file)[0]
    features_dir = f"features_{fasta_basename}"
    features_file = f"{fasta_basename}_features.csv"

    generate_script = base_dir / "generate_feature_file.py"
    evaluate_script = base_dir / "evaluate.py"

    # Step 1: Generate feature file
    print("⚙️ Generating feature file...")
    subprocess.run([
        python_path,
        str(generate_script),
        "-f", fasta_file,
        "-d", features_dir,
        "-o", features_file
    ], check=True)

    # Step 2: Run prediction
    print("🧠 Running ClassifyTE prediction...")
    subprocess.run([
        python_path,
        str(evaluate_script),
        "-f", features_file,
        "-d", features_dir,
        "-n", node_file,
        "-m", model_name,
        "-a", algorithm
    ], check=True)

    # Step 3: Load predictions
    predictions_path = Path("outputs") / f"predicted_out_{features_dir}.csv"
    if not predictions_path.exists():
        raise FileNotFoundError(f"Prediction file not found at {predictions_path}")

    df = pd.read_csv(predictions_path)

    # Step 3.1: Add actual labels if missing
    if "Actual_Label" not in df.columns:
        print("🧬 Adicionando rótulos verdadeiros automaticamente a partir do .fasta...")
        fasta_file_path = Path("ClassifyTE/data") / fasta_file

        fasta_sequences = []
        with open(fasta_file_path, 'r') as f:
            for line in f:
                if line.startswith(">"):
                    seq_id = line.strip()[1:]
                    fasta_sequences.append(seq_id)

        label_dict = {}
        for full_id in fasta_sequences:
            if "|" in full_id:
                _, label = full_id.split("|", 1)
                label_dict[full_id] = label
            else:
                label_dict[full_id] = ""

        df.columns = [col.strip() for col in df.columns]
        df["Actual_Label"] = df["Sequence ID"].map(label_dict)
        df.to_csv(predictions_path, index=False)
        print(f"✅ Rótulos adicionados e salvos em: {predictions_path}")

    print("🧩 Normalizando rótulos com base em tree.txt...")
    tree_path = Path("nodes") / "tree.txt"
    tree_df = pd.read_csv(tree_path, header=None, names=["Code", "Label"])

    label_to_code = dict(zip(tree_df["Label"], tree_df["Code"]))

    # Cuidado com nomes mal formatados
    df["Predicted label"] = df["Predicted label"].astype(str).str.strip()
    df["Actual_Label"] = df["Actual_Label"].astype(str).str.strip()

    # Mapeia os nomes para códigos hierárquicos
    df["Predicted_Code"] = df["Predicted label"].map(label_to_code)
    df["Actual_Code"] = df["Actual_Label"].map(lambda x: x if "." in x else label_to_code.get(x))

    # Diagnóstico
    for p, a in zip(df["Predicted_Code"], df["Actual_Code"]):
        print(f"📊 Predicted: {p} | Actual: {a}")

    predictions = df["Predicted_Code"].dropna().tolist()
    labels = df["Actual_Code"].dropna().tolist()

    return predictions, labels
