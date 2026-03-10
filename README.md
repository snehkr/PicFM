# PicFM (Photo Manager 2.0) 📸

PicFM is a blazing-fast, AI-powered desktop photo management application built with Python and PyQt6. It goes beyond simple file browsing by utilizing state-of-the-art machine learning models to analyze, cluster, and organize your gallery locally on your machine.

## ✨ Features

- **AI Face Recognition:** Uses **InsightFace (ArcFace via ONNX)** to accurately detect and cluster faces across thousands of photos, handling side profiles and occlusions effortlessly—all on the CPU.
- **Semantic Duplicate Detection:** Upgraded from basic hashing! Uses **OpenCLIP (ViT-B-32)** to generate semantic embeddings. It detects duplicates even if they are resized, heavily compressed (e.g., WhatsApp images), slightly cropped, or screenshotted.
- **Modern Fluent UI:** Built with `qfluentwidgets`, featuring a sleek Windows 11 design language, instant Dark/Light mode toggling, and non-blocking background tasks.
- **Massive Scalability:** Employs heavily optimized, virtualized UI lists (`QAbstractListModel`) to render folders with tens of thousands of images with zero lag.
- **EXIF & Map Integration:** Extracts camera metadata and embeds a one-click Google Maps integration for photos with GPS coordinates.

## 🚀 Installation & Setup

### Prerequisites

- **Python 3.12+**
- If on Windows, ensure you have the [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) installed for the ML libraries.

### Quick Start

1. Clone the repository:

   ```bash
   git clone [https://github.com/SnehKr/PicFM.git](https://github.com/SnehKr/PicFM.git)
   cd PicFM
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt

   ```

3. Run the application:

   ```bash
   python main.py

   ```

_Note: Upon your first scan, the application will download the required AI models (InsightFace `buffalo_l` and OpenCLIP `ViT-B-32`) to your local machine (~1GB total)._

## 🛠️ Tech Stack

- **Frontend:** PyQt6, QFluentWidgets
- **Database:** SQLite3 (WAL mode optimized) + NumPy binary arrays
- **Face Recognition:** InsightFace (ONNX Runtime, CPU Execution) + DBSCAN Clustering
- **Image Semantics:** PyTorch, OpenCLIP, Scikit-Learn (NearestNeighbors)
- **Concurrency:** `ProcessPoolExecutor` for multi-core background scanning

## 📦 Building for Production

To package PicFM into a standalone `.exe` file without bloating the installer with CUDA/GPU dependencies:

```bash
pyinstaller --clean build.spec

```

The compiled executable will be located in the `dist/` folder.

## 👤 Author

Developed by **Sneh Kr.**
