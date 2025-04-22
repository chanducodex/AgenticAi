import os
import json
import time
import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.conf import settings
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import pdb

# --- Constants ---
media_root = settings.MEDIA_ROOT
pdf_image_dir = os.path.join(media_root, "pdf_images")
os.makedirs(pdf_image_dir, exist_ok=True)
# Specify the path to Poppler (ONLY for Windows users)
# POPPLER_PATH = r"C:\Program Files\poppler-24.08.0\Library\bin" # Uncomment this line if using Windows and Poppler is installed

OLLAMA_URL = "http://localhost:11434/api/generate"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY)
OPENAI_URL = 'https://api.openai.com/v1/chat/completions'

# Initialize PaddleOCR
ocr_model = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True)

# --- Utility Functions ---
def pdf_to_images(pdf_path: str, dpi: int = 300):
    # images = convert_from_path(pdf_path, dpi=dpi, poppler_path=POPPLER_PATH) # Uncomment this line if using Windows and Poppler is installed
    images = convert_from_path(pdf_path, dpi=dpi) # For Linux or MacOS, Poppler is not needed
    image_paths = []
    for i, image in enumerate(images):
        image_path = os.path.join(pdf_image_dir, f"{os.path.basename(pdf_path)}_page_{i+1}.jpg")
        image.save(image_path, 'JPEG')
        image_paths.append(image_path)
    return image_paths

def extract_text_from_images(images):
    result_text = ""
    for image in images:
        result = ocr_model.ocr(image)
        for line in result[0]:
            result_text += line[1][0] + "\n"
    return result_text

def build_prompt(extracted_text):
    # Replace this with the actual JSON schema you want in the prompt
    prompt_template = """You are an intelligent invoice parser. Your task is to extract structured invoice data from the following invoice text.

<INVOICE_TEXT>
{invoice_text}
</INVOICE_TEXT>

Extract the information and format into the following JSON structure (only output JSON):

{
  "invoiceList": [
    {
      "currencyCode": "<Extract the standard 3-letter ISO currency code (e.g., USD, EUR, INR) if explicitly mentioned in the invoice. If not available, leave this field blank. Do not infer from symbols like $, ₹, or context.>",
      "currencyName": "<Extract the full currency name (e.g., US Dollar, Euro, Indian Rupee) if clearly stated in the invoice. If not mentioned, leave this field blank. Do not guess or derive from currency code or symbols.>",
      "companyGstin": "<Seller's 15-16 alphanumeric GSTIN>",
      "date": "<Invoice date in YYYY-MM-DD format>",
      "dueDate": "<If available; otherwise, leave empty>",
      "contactName": "<Customer name from the 'Bill to' section . If not available, use the shipping company name(Ship to) don't use reference name>",
      "customerGstin": "<Buyer’s 15 or 16 alphanumeric GSTIN if available; otherwise, leave empty>",
      "number": "<Invoice number>",
      "placeSupplyName": "<Extract the Place of Supply as the state only (e.g., Karnataka)>",
      "billAddress": {
        "city": "<City from billing address>",
        "state": "<State>",
        "zip": "<Postal code>",
        "country": "<Country>",
        "pan": "<PAN if available; otherwise, leave empty>",
        "gstin": "<Billing address GSTIN if present (15-16 alphanumeric)>"
      },
      "lineItems": [
        {
          "itemCode": "<Alphanumeric unique item code; if unavailable and not sure , return blank>",
          "hsnCode": "<If available, provide the HSN (Harmonized System of Nomenclature) code. If not available, return blank. Do not infer from itemCode or itemName.>",
          "itemName": "<Item name>",
          "quantity": <Quantity as a number(UOC); otherwise, leave empty as null>,
          "unitPrice": <Unit price or rate as a number, including decimal values for eg '1234.56'>,
          "description": "<Optional description which looks like that; otherwise, leave empty>",
          "discount": <Discount if any; otherwise, 0>,
          "total": "<Total line item amount as a numeric value, including decimal values for eg '1234.56'>",
          "unitName": "<Unit of Measure(UOM). If not available in invoice, return blank (e.g., Numbers,Boxes, Kilograms etc)>",
          "taxDetails": [
            {
              "regimeName": "<Tax regime name (e.g., GST, IGST, SGST, CGST) extracted from the line item header; default to 'GST'>",
              "taxRate": <Tax rate percentage>
            }
          ]
        }
      ]
    }
"""
    return prompt_template.replace("{invoice_text}", extracted_text)

def query_ollama(prompt, model="deepseek-r1:14b"):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False}
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        raise RuntimeError(f"Ollama failed: {e}")

def query_openai(prompt):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}',
    }
    data = {
        'model': 'gpt-4o-mini',
        'messages': [{"role": "user", "content": prompt}],
        'temperature': 0
    }
    response = requests.post(OPENAI_URL, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# --- API View ---
@api_view(['POST'])
@parser_classes([MultiPartParser])
def invoiceParserAPIView(request):
    if request.method != 'POST':
        return JsonResponse({'message': "Method not allowed."}, status=400)
    
    uploaded_file = request.FILES.get('invoice_file')
    if not uploaded_file:
        return Response({"error": "No PDF file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

    # Save uploaded file to media/uploads
    pdf_path = default_storage.save(f"uploads/{uploaded_file.name}", uploaded_file)
    full_pdf_path = os.path.join(default_storage.location, pdf_path)

    try:
        # Step 1: Convert PDF to images
        image_paths = pdf_to_images(full_pdf_path)

        # Step 2: OCR text
        extracted_text = extract_text_from_images(image_paths)

        # Step 3: Build prompt
        prompt = build_prompt(extracted_text)

        # Step 4: Query model
        start = time.time()
        model_response = query_ollama(prompt)
        # model_response = query_openai(prompt)
        end = time.time()

        return JsonResponse({
            "response": model_response,
            "inference_time_seconds": round(end - start, 2)
        })

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        try:
            # Clean up: delete uploaded PDF and generated images
            if os.path.exists(full_pdf_path):
                os.remove(full_pdf_path)
            for image_path in image_paths:
                if os.path.exists(image_path):
                    os.remove(image_path)
        except Exception as e:
            print(f"Error cleaning up files: {e}")
