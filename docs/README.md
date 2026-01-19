# 🧬 TE Eval Tool - Transposable Elements Evaluation Framework

**Version:** 5.0.1 | **Date:** January 2026 | **Status:** Stable ✅

---

## 📋 Overview

**TE Eval Tool** is a comprehensive platform for **classification, evaluation, and comparison of transposable element (TE) prediction models**. Developed to standardize the execution of different classification tools and enable fair comparisons through robust and hierarchical metrics.

### 🎯 Main Objectives

- ✅ **Standardization**: Run different models in a uniform environment
- ✅ **Fair Comparison**: Apply the same evaluation rules for all models
- ✅ **Hierarchical Metrics**: Consider TE taxonomy in evaluations
- ✅ **Ease of Use**: Intuitive web interface + powerful CLI
- ✅ **Reproducibility**: Standardization of inputs, outputs, and metrics

### 🔬 Supported Models

| Model | Analysis Type | Datasets/Models |
|-------|---------------|-----------------|
| **ClassifyTE** | Fragments | 3 models (combined, pgsb, repbase) |
| **TERL** | CNN Fragments | 5 datasets (DS1-DS5) |
| **YORO** | Domains (deep learning) | 2 versions (V21, V25) |
| **Inpactor2** | Complete Elements | Structural detection + classification |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+
- Docker & Docker Compose (optional, recommended)
- Python venv module (usually included with Python 3.9+)

### Installation with Docker (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd te_eval_tool

# 2. Build and start containers
docker-compose up -d --build

# 3. Check container status
docker-compose ps

# 4. View logs (optional)
docker-compose logs -f

# 5. Access the web interface
# Frontend: http://localhost:3002
# API Docs (Swagger): http://localhost:3002/api-docs

# Stop containers
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Manual Installation

```bash
# 1. Backend (Node.js)
cd backend
npm install
npm start
# Server will run on http://localhost:3002

# 2. CLI (Python)
cd ../CLI
pip install -r requirements.txt

# 3. Test the installation
python src/main.py --version
# Should display: version 5.0.1

# 4. Open the frontend
# Simply open frontend/index.html in your browser
# Or serve with: python -m http.server 8080 (from frontend/)
```

---

## 📚 Complete Documentation

### Main Documentation

- **[DESCRIBE-TOOL.md](DESCRIBE-TOOL.md)** - Detailed tool description, architecture, and workflows
- **[README-CLI.md](README-CLI.md)** - Complete command-line interface documentation
- **[README-API.md](README-API.md)** - REST API reference (OpenAPI/Swagger)

### Technical Documentation

- **[METRICS-REFERENCE.md](METRICS-REFERENCE.md)** - Complete metrics reference (40+ metrics)
- **[TREE-STRUCTURE.md](TREE-STRUCTURE.md)** - Hierarchical structure of TE taxonomy
- **[DIAGRAMA-ARQUITETURA.md](DIAGRAMA-ARQUITETURA.md)** - Visual architecture and flow diagrams
- **[PROPOSTA-TECNICA-CIENTIFICA.md](PROPOSTA-TECNICA-CIENTIFICA.md)** - Complete technical-scientific document
- **[frontend/README-VISUALIZATION.md](../frontend/README-VISUALIZATION.md)** - Metrics visualization interface

---

## 💻 Quick Usage

### Web Interface - Step-by-Step Guide

#### Tab 1: Run Classification

1. **Access the tool**: Open `http://localhost:3002` in your browser
2. **Select the Run tab**: Click on the "Run" tab in the navigation
3. **Upload FASTA file**: 
   - Drag and drop your FASTA file into the upload area, OR
   - Click "Choose File" button and select your file
   - Supported format: `.fasta`, `.fa`, `.fna`
4. **Select a model**:
   - **ClassifyTE**: Fragment-based classification (3 models available)
   - **TERL**: CNN-based fragment analysis (5 datasets: DS1-DS5)
   - **YORO**: Domain-based deep learning (V21 or V25)
   - **Inpactor2**: Complete element detection and classification
5. **Configure parameters**:
   - Select specific model/dataset from dropdown
   - Enable "Auto Label" to automatically map predictions to hierarchy
   - Enable "Auto Evaluate" to generate metrics automatically
6. **Enter email**: Provide your email for result notifications
7. **Submit**: Click "Run Classification" button
8. **Monitor progress**: 
   - Job status will be displayed
   - You can track progress in real-time
9. **Receive results**: 
   - Email notification with download link
   - Results include: predictions CSV, evaluation reports, metrics JSON

#### Tab 2: Visualize Metrics

1. **Select Visualize tab**: Click on "Visualize Metrics" in navigation
2. **Upload results**:
   - Upload the `evaluation_report.txt` or `metrics_summary.json` from your results
   - Or use the `detailed_metrics.json` for complete visualization
3. **Explore metrics**:
   - **Summary Cards**: View key metrics (accuracy, F1-score, MCC)
   - **Confusion Matrix**: Interactive heatmap with class names
   - **Per-Class Metrics**: Detailed breakdown by superfamily
   - **Hierarchical Metrics**: Distance-based evaluation charts
4. **Export visualizations**: Download charts as PNG images

#### Tab 3: Compare Models

1. **Upload multiple results**: Add results from different models
2. **Side-by-side comparison**: Compare metrics across models
3. **Statistical analysis**: View performance differences
4. **Best model recommendation**: Automatic ranking based on metrics

**📊 Complete workflow illustrated in [DIAGRAMA-ARQUITETURA.md](DIAGRAMA-ARQUITETURA.md#exemplo-de-uso-completo)**

### CLI - Examples

#### Classify Sequences

```bash
cd CLI

# ClassifyTE
python src/main.py run \
  --input sequences.fasta \
  --model classifyte \
  --model-file ClassifyTE_combined.pkl \
  --output results/ \
  --auto-label -v

# TERL
python src/main.py run \
  --input sequences.fasta \
  --model terl \
  --model-file DS3 \
  --output results/ \
  --auto-label -v

# YORO
python src/main.py run \
  --input sequences.fasta \
  --model yoro \
  --model-file ./src/models/YORO/models/AAqqYOLOqqdomainqqV25.hdf5 \
  --output results/ \
  --auto-label -v
```

#### Map Hierarchical Labels

```bash
python src/main.py map-labels \
  --fasta-file sequences.fasta \
  --predictions-file predictions.csv \
  --tree-file src/nodes/tree.txt \
  --output-dir mapped/ \
  --validate-only false
```

#### Evaluate Performance

```bash
python src/main.py evaluate \
  --predictions predictions_mapped.csv \
  --output-dir evaluation/ \
  --format detailed
```

---

## 📊 Implemented Metrics

### Metric Categories

1. **Standard Metrics** (15 metrics)
   - Accuracy, Precision (macro/micro/weighted)
   - Recall, F1-Score, Specificity

2. **Robust Metrics** (8 metrics)
   - Cohen's Kappa, Matthews Correlation Coefficient
   - Youden's J Statistic, auROC, mAP

3. **Hierarchical Metrics** (6 metrics)
   - Hierarchical Precision/Recall/F1
   - Mean/Std/Max Hierarchical Distance

4. **Per-Class Metrics** (4 metrics per class)
   - Precision, Recall, F1-Score, Support

**Total:** 40+ implemented metrics

---

## 🏗️ System Architecture

### Layer Overview

```
┌─────────────────────────────────────────────────────────┐
│  👥 USERS (Scientists/Researchers/Students)            │
└──────────────────┬──────────────────────────────────────┘
                   │
       ┌───────────┴───────────┐
       │                       │
   💻 CLI                  🌐 Web Frontend
       │                       │
       │                       │
       └───────────┬───────────┘
                   │
        ⚙️ Backend API (Node.js)
                   │
                   │
        🧠 Core Engine (Python)
                   │
       ┌───────────┴────────────┐
       │                        │
   🤖 ML Models           📊 Data
   (ClassifyTE,           (FASTA, CSV,
    TERL, YORO,           tree.txt,
    Inpactor2)            Reports)
```

**📊 For detailed diagrams and complete flows, see [DIAGRAMA-ARQUITETURA.md](DIAGRAMA-ARQUITETURA.md)**

### Directory Structure

```
te_eval_tool/
├── CLI/                    # Command-Line Interface (Python)
│   ├── src/
│   │   ├── commands/      # Main commands (run, evaluate, map-labels)
│   │   ├── lib/           # Core libraries
│   │   │   ├── metrics_evaluator.py    # 40+ metrics
│   │   │   ├── fasta_label_mapper.py   # Taxonomic normalization
│   │   │   └── env_manager.py          # Virtual environment manager (venv)
│   │   ├── models/        # Wrappers for each model
│   │   │   ├── ClassifyTE/, TERL/, YORO/, Inpactor2/
│   │   └── nodes/         # tree.txt (taxonomic hierarchy)
│   └── requirements.txt
│
├── backend/               # Node.js + Express Server
│   ├── server.js          # Main server
│   ├── src/
│   │   ├── controllers/   # Business logic
│   │   ├── routes/        # REST API routes
│   │   ├── services/      # Services (CLI, email, jobs)
│   │   └── config/        # swagger.yaml (OpenAPI)
│   └── package.json
│
├── frontend/              # Web Interface (HTML/CSS/JS)
│   ├── index.html         # Main UI with tabs
│   ├── metrics_visualization.html  # Interactive visualization
│   ├── style.css          # Styles
│   └── app.js             # Frontend logic
│
├── data/                  # Data and results
│   ├── uploads/           # Uploaded FASTA files
│   ├── results/           # Execution outputs (run_*)
│   └── repbase_subsets/   # Test/benchmark datasets
│
├── docs/                  # Complete documentation
│   ├── README.md          # This file
│   ├── DIAGRAMA-ARQUITETURA.md     # Mermaid diagrams
│   ├── PROPOSTA-TECNICA-CIENTIFICA.md  # Scientific document
│   ├── METRICS-REFERENCE.md        # Metrics reference
│   └── README-CLI.md, README-API.md, etc.
│
├── docker-compose.yml     # Docker orchestration
└── Dockerfile            # Main container
```

---

## 🔬 Main Workflows

### Workflow 1: Simple Classification

```bash
# 1. Run model
python CLI/src/main.py run --input data.fasta --model classifyte --output results/

# 2. View results
cat results/predicted_results.csv
```

### Workflow 2: Complete Evaluation

```bash
# 1. Classify
python CLI/src/main.py run --input data.fasta --model classifyte --output results/

# 2. Map labels
python CLI/src/main.py map-labels \
  --fasta-file data.fasta \
  --predictions-file results/predicted*.csv \
  --output-dir mapped/

# 3. Evaluate
python CLI/src/main.py evaluate \
  --predictions mapped/predictions_mapped.csv \
  --output-dir evaluation/

# 4. Visualize
# Open frontend/metrics_visualization.html and upload evaluation_report.txt
```

### Workflow 3: Model Comparison

```bash
# Run multiple models on the same dataset
for model in classifyte terl yoro; do
  python CLI/src/main.py run \
    --input test.fasta \
    --model $model \
    --output results/$model/ \
    --auto-label -v
    
  python CLI/src/main.py evaluate \
    --predictions results/$model/predicted*.csv \
    --output-dir results/$model/eval/
done

# Compare metrics
cat results/*/eval/metrics_summary.json
```

---

## 📊 Generated Outputs

### Per Classification (`run`)

**Via CLI** (saved in `--output` directory):
```
results/
├── predicted_results.csv           # Model predictions
├── predicted_results_<timestamp>.csv
├── evaluation_report.txt           # (if --auto-label)
└── metrics_summary.json           # (if --auto-label)
```

**Via Web** (sent by email):
- 📧 Email with download link
- 📦 ZIP file containing all results
- 🌐 Link to interactive web visualization

### Per Mapping (`map-labels`)

```
mapped/
├── mapped_fasta.fasta             # FASTA with standardized headers
├── predictions_mapped.csv         # CSV with hierarchical codes
├── mapping_report.txt             # Validation report
└── debug_mapper.txt              # Debug logs
```

### Per Evaluation (`evaluate`)

```
evaluation/
├── evaluation_report.txt          # Complete readable report
├── detailed_metrics.json          # Detailed metrics
├── metrics_summary.json           # Executive summary
└── debug_fasta_mappings.csv      # Mapping debug
```

---

## 🌐 REST API

The REST API provides endpoints for:

- **POST /api/v1/run** - Execute classification
- **POST /api/v1/map-labels** - Map hierarchical labels
- **POST /api/v1/evaluate** - Evaluate predictions

**Complete documentation:** [README-API.md](README-API.md)

**Swagger UI:** http://localhost:3002/api-docs

---

## 🤝 Contributing

### How to Add a New Model

1. Create wrapper in `CLI/src/models/<model>_runner.py`
2. Implement `run()` method returning standardized CSV
3. Register in `CLI/src/commands/main.py`
4. Configure Python virtual environment (venv) with specific dependencies
5. Update documentation

See [DESCRIBE-TOOL.md](DESCRIBE-TOOL.md) for details.

### How to Add a New Metric

1. Implement in `CLI/src/lib/metrics_evaluator.py`
2. Add to `evaluate()` method
3. Update outputs (TXT, JSON)
4. Document in [METRICS-REFERENCE.md](METRICS-REFERENCE.md)
5. Add visualization in frontend (optional)

---

## 📄 License

[Specify project license]

---

## 👥 Project Team

### Researcher
**Gabriel Carneiro de Arruda**  
State University of Ponta Grossa (UEPG)  
Graduate Program in Applied Computing

### Advisors
**Prof. Dr. Adriano Ferrasa** (Advisor)  
**Prof. Dr. Alceu de Souza Britto Jr.** (Co-Advisor)

### Institution
**State University of Ponta Grossa**  
Graduate Program in Applied Computing

---

## 📞 Contact

- **GitHub Issues:** To report bugs or request features
- **Documentation:** Consult the MD files in the project root
- **Email:** [add contact email]

---

## 🙏 Acknowledgments

- Developers of base models (ClassifyTE, TERL, YORO, Inpactor2)
- RepBase community for reference data
- Project collaborators and testers

---

## 📖 How to Cite

```bibtex
@software{te_eval_tool,
  author = {Arruda, Gabriel Carneiro de and Ferrasa, Adriano and Britto Jr., Alceu de Souza},
  title = {TE Eval Tool: A Framework for Standardized Evaluation of Transposable Element Classification Models},
  year = {2026},
  version = {5.0.1},
  institution = {State University of Ponta Grossa},
  url = {[add repository URL]}
}
```

---

**🧬 TE Eval Tool** - Standardize, Execute, Compare, and Evaluate transposable element classification models with confidence!

**Last update:** January 2026 | **Version:** 5.0.1 | **Status:** Stable ✅
