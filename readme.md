# 🧾 AgenticAI Invoice Processor

AgenticAI is an intelligent invoice parsing API built with Django. It leverages OCR and layout-aware parsing to convert scanned or digital invoices into structured JSON output.

## 🚀 Features

- OCR using PaddleOCR
- Invoice text to structured JSON via LLM
- REST API to submit PDF invoices and receive parsed results
- Deployment-ready with Gunicorn + Screen

---

## 🧰 Tech Stack

- Python 3.10+
- Django 5.x
- Gunicorn (for WSGI serving)
- Screen (for background process management)
- PaddleOCR, local LLM (e.g., DeepSeek/Mistral)

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/chanducodex/AgenticAi.git
cd AgenticAi
```

### 2. Set Up Python Environment

Create a virtual environment (recommended):

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

### 3. Install Requirements

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🛠️ Django Setup

### 4. Run Server for Testing (Development)

```bash
python manage.py runserver
```

#### Access locally at: http://localhost:8000/parse-invoice/

---

## 🧪 Testing the API

Send a POST request with a PDF file:

```bash
curl -X POST http://localhost:8000/parse-invoice/ \
  -F "invoice_file=@path_to_invoice.pdf"
```

The response will be a structured JSON object containing invoice fields.

---

## 🖥️ Deployment on Linux Server

### 6. Run with Gunicorn inside screen

```bash
screen -S invoiceapi
gunicorn --workers 3 invoice_processor.wsgi:application
```

Gunicorn will start listening on http://127.0.0.1:8000.

You can detach from screen with Ctrl+A+D and resume with screen -r invoiceapi.
