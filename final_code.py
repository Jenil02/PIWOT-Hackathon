import io
import json
from fastapi import FastAPI, HTTPException
import pandas as pd
import requests
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import boto3
import openai
from datetime import datetime, timedelta

app = FastAPI()

textract_client = boto3.client('textract',
    region_name='us-east-1',
    aws_access_key_id="",
    aws_secret_access_key=""
)
def replacer(value):
    if value == '' or None:
        return float(0.00)
    if type(value) == float or type(value) == int:
        return value
    else:
        return float(value.replace(',', ''))

def split_pdf(pdf):
    """Split a PDF file into individual pages and return them as byte streams."""
    pages = []
    for page in pdf.pages:
        writer = PdfWriter()
        writer.add_page(page)
        page_stream = io.BytesIO()
        writer.write(page_stream)
        page_stream.seek(0)
        pages.append(page_stream)
    return pages

def process_page(page_stream):
    """Process a single page using AWS Textract."""
    page_stream.seek(0)  # Reset stream position to the beginning
    response = textract_client.detect_document_text(Document={'Bytes': page_stream.read()})
    extracted_text = []
    for item in response['Blocks']:
        if item['BlockType'] == 'LINE':
            extracted_text.append(item['Text'])
    return '\n'.join(extracted_text)


def generate_structure_data_wo_cons(extracted_text):
    client = openai.OpenAI(api_key='')
    
    prompt = """You are a text extractor who extracts relevant patient information in a specified format from a hospital medical bill.

      1) Extract patient information and unique diagnostic services and their charges from the provided text
      2) Ensure that the unique diagnostic services encompasses a variety of tests, including but not limited to blood tests, imaging studies, and other medical procedures.  The goal is to compile a comprehensive list that may include services like "Sodium", "Complete Blood Count (CBC)", "X-Ray" and other commonly performed diagnostic tests.
      3) Ensure that the values for 'totalCharge' in various sections are represented as floating-point numbers and 0.00 if the value is not present.
      4) Do not give me code


      The output should be formatted as a JSON instance that conforms to the JSON schema below.
      Here is the output schema:
      ``` 
      {"": {
        "personaldetail": {
          "name": "",
          "age": "",
          "gender": "",
          "UHID": "",
          "address": "",
          "contactNumber": "",
          "primaryDoctor": "",
          "admissionDate": "",
          "dischargeDate": "",
          "wardBedType": ""
        },
        "unique_diagnostic_services": [
            {
                "name_of_unique_diagnostic_service": "",
                "totalCharge": ""
            }
        ],
        "billingDetails": {
          "billNo": "",
          "billDate": "",
          "totalBillAmount": ""
        },
        "accommodation": {
          "totalCharge": "",
          "dailyRate": "",
          "daysStayed": ""
        },
        "professionalServices": {
          "totalCharge": ""
        },
        "diagnosticServices": {
          "totalCharge": ""
        },
        "operativeServices": {
          "totalCharge": ""   
        },  
        "pharmacyAndConsumables": {
          "totalCharge": ""
          },
        "hospitalServices": {
          "totalCharge": ""
        },
        "equipmentUsed": {
          "totalCharge": ""
        },
        "nursingCharges": {
            "totalCharge": ""
        },
        "otherCharges": [
          {
            "chargeType": "",
            "description": "",
            "amount": ""
          } 
        ],
      }
      ```
      """


    response = client.chat.completions.create(
        
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": extracted_text},
        ],
        response_format={ "type": "json_object" },
        model="gpt-3.5-turbo-1106",
        max_tokens=4000
    )

    raw_response = response.choices[0].message.content
    start_index = raw_response.find("```python") + len("```python")
    end_index = raw_response.rfind("```")

    python_code = raw_response[start_index:end_index].strip()
    return python_code

def generate_structure_data_cons(extracted_text):
    client = openai.OpenAI(api_key='')
    
    prompt = """You are a text extractor who extracts relevant patient information in a specified format from a hospital medical bill.

    1) Unique medicine includes medications like tablets and injections only.
    2) Consumables are items used by doctors and nurses to treat patients. The goal is to compile a unique list of consumables that may include items like "Sodium Chloride", "Syringe", "Cotton" and other commonly used consumables.
    2) It is very critical that the list of unique consumables and list of unique pharmacy do not overlap.
    3) Ensure that the values for 'totalCharge' in various sections are represented as floating-point numbers and 0.00 if the value is not present.
    4) Ignore repetitions
    5) Do not give me code

    The output should be formatted as a JSON instance that conforms to the JSON schema below.
      Here is the output schema:
      ``` 
      {"": {
        "unique_medicine": [
            {
                "name_of_unique_medicine": "",
                "totalCharge": ""
            }
        ],
        "unique_consumables" : [
            {
                "name_of_unique_consumable": "",
                "totalCharge": ""
            }
        ],
      }
      ```
      """



    response = client.chat.completions.create(
        
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": extracted_text},
        ],
        response_format={ "type": "json_object" },
        model="gpt-3.5-turbo-1106",
        max_tokens=4000
    )

    raw_response = response.choices[0].message.content
    start_index = raw_response.find("```python") + len("```python")
    end_index = raw_response.rfind("```")

    python_code = raw_response[start_index:end_index].strip()
    print(python_code)
    return python_code

def fetch_json(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        
        # Assuming the response content is a JSON file
        data = response.json()
        return data
    except requests.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
def load_json(uploaded_file):
    """Load a JSON file uploaded in Streamlit and return the data."""
    try:
        return json.load(uploaded_file)
    except Exception as e:
        print(e)
        return None
def parse_date(date_str, format='%d-%m-%Y'):
    """Parse a date string into a datetime object."""
    try:
        return datetime.strptime(date_str, format)
    except ValueError as e:
        print(e)
        return None
    
def claimable_pharmacy(bill_data):
    total_ph_bill = bill_data.get("pharmacyAndConsumables", {'totalCharge' : 0.00}).get("totalCharge", 0)
    return total_ph_bill

def claimable_hospital(bill_data):
    total_hs_bill = bill_data.get("hospitalServices", {'totalCharge' : 0.00}).get("totalCharge", 0)
    return total_hs_bill

def claimable_diagnostic(bill_data):
    total_dt_bill = bill_data.get("diagnosticServices", {'totalCharge' : 0.00}).get("totalCharge", 0)
    return total_dt_bill

def claimable_operating_services(bill_data):
    total_os_bill = bill_data.get("operativeServices", {'totalCharge' : 0.00}).get("totalCharge", 0)
    return total_os_bill

def claimable_equipment(bill_data):
    total_eq_bill = bill_data.get("equipmentUsed", {'totalCharge' : 0.00}).get("totalCharge", 0)
    return total_eq_bill

def claimable_profession_service(bill_data):
    total_ps_bill = bill_data.get("professionalServices", {'totalCharge' : 0.00}).get("totalCharge", 0)
    return total_ps_bill
    
def total_amount_check(policy_data , total_claimable_amount):
    insurance_limit =  policy_data["policyDetails"]["insuredAmount"]   
    return(min(total_claimable_amount,insurance_limit))
# Check Functions
def check_waiting_period_clash(claimSubmissionDate, policyStartDate, disease, waiting_period, policy_data):
    submission_date = parse_date(claimSubmissionDate)
    policy_start_date = parse_date(policyStartDate)
    waiting_period_end = policy_start_date + timedelta(days= 365 * waiting_period)
    
    if submission_date < waiting_period_end:
        return disease in policy_data['policyDetails']['waitingPeriodCoverage']['coveredItems']
    
    return True

def check_grace_period(claim_data):
    if claim_data['documentDetails']['gracePeriodComparison'] == "False":
        return False
    return True 

# def claimable_check_table(pharmacy, cons_data, bill_data):
#     # create a dataframe for displaying cons_data in table format
#     c = [True]*len(cons_data)
#     cons_df = pd.DataFrame(cons_data, columns=['name_of_unique_consumable', 'totalCharge', 'claimable'])
#     cons_df['claimable'] = c
#     cons_df['totalCharge'] = [replacer(x) for x in cons_df['totalCharge']]

#     # create a dataframe for displaying pharmacy in table format
#     p = [True]*len(pharmacy)
#     ph_df = pd.DataFrame(pharmacy, columns=['name_of_unique_medicine', 'totalCharge', 'claimable'])
#     ph_df['claimable'] = p
#     ph_df['totalCharge'] = [replacer(x) for x in ph_df['totalCharge']]

#     d = [True]*len(bill_data['unique_diagnostic_services'])
#     diag_df = pd.DataFrame(bill_data['unique_diagnostic_services'], columns=['name_of_unique_diagnostic_service', 'totalCharge', 'claimable'])
#     diag_df['claimable'] = d
#     diag_df['totalCharge'] = [replacer(x) for x in diag_df['totalCharge']]

#     # diag_c_amount = diag_edited_df[diag_edited_df['claimable']]['total_charge'].sum()
#     # ph_c_amount = ph_edited_df[ph_edited_df['claimable']]['total_charge'].sum()
    
#     return cons_df, ph_df, diag_df


def display_bill_details_in_table(pharmacy_edit, cons_edit, consumables_amount, bill_data, accommodation_amount, nursing_amount, hospital_service_amount, diag_edit, operating_service_amount, equipment_amount, professional_service_amount,claimable_amount, other_charges):
    # Creating a DataFrame for displaying in table format
    # other_charges = bill_data['billingDetails']['totalBillAmount'],

    charges_df = pd.DataFrame({
        'Service Type': ['Accommodation', 'Nursing', 'Pharmacy', 'Hospital Services', 'Diagnostic', 'Operating Services', 'Equipment', 'Professional Services', 'Consumables', 'Other Charges', 'Total bill Amount'],
        'Billed Amount': [
            bill_data['accommodation']['totalCharge'],
            bill_data['nursingCharges']['totalCharge'],
            bill_data['pharmacyAndConsumables']['totalCharge'],
            bill_data['hospitalServices']['totalCharge'],
            bill_data['diagnosticServices']['totalCharge'],
            bill_data['operativeServices']['totalCharge'],
            bill_data['equipmentUsed']['totalCharge'],
            bill_data['professionalServices']['totalCharge'],
            consumables_amount,
            other_charges,
            bill_data['billingDetails']['totalBillAmount'],
        ],
        'Claimable Amount': [accommodation_amount, nursing_amount, pharmacy_edit, hospital_service_amount, diag_edit, operating_service_amount, equipment_amount, professional_service_amount, cons_edit, other_charges, claimable_amount]
    })

    # Displaying the table


def hospitalization_day(single_day_allowablecharge,total_accomodation_charge):
    final_amount=total_accomodation_charge-single_day_allowablecharge
    return final_amount

def calculate_accommodation_coverage(bill_data, policy_data):
    # Logic to calculate accommodation coverage
    insured_amount = policy_data['policyDetails']["insuredAmount"]
    percent_insured = insured_amount * policy_data['policyDetails']['accommodationAllowance']["percentageOfInsuredAmount"] / 100
    fixed_insured = policy_data['policyDetails']['accommodationAllowance']['alternativeMaximumAllowance']
    max_amount_per_day = int(max(percent_insured, fixed_insured))
    # billed_amount_str = bill_data['accommodation']['dailyRate'].replace(',', '')
    billed_amount = replacer(bill_data['accommodation']['dailyRate'])
    coverage_amount = min(max_amount_per_day, billed_amount)
    total_coverage_amount = coverage_amount * int(replacer(bill_data['accommodation']['daysStayed']))
    return total_coverage_amount,coverage_amount

def include_nursing_charges(bill_data, accommodation_coverage):
    return accommodation_coverage * (replacer(bill_data['nursingCharges']["totalCharge"]) / replacer(bill_data['accommodation']['totalCharge']))

# Main Calculation Function
def calculate_claimable_amount(claimSubmissionDate, policyStartDate, disease, waiting_period, policy_data, bill_data):
    print('check1')
    if not check_waiting_period_clash(claimSubmissionDate, policyStartDate, disease, waiting_period, policy_data):
        return "Waiting period clash"
    print('check2')

    (accommodation_coverage, single_day_accomodation) = calculate_accommodation_coverage(bill_data, policy_data)
    final_accomodable_amount = hospitalization_day(single_day_accomodation, accommodation_coverage)
    print(final_accomodable_amount)
    print('check 3')
    nursing_coverage = include_nursing_charges(bill_data, accommodation_coverage)
    
    # Corrected function calls to calculate other bill components
    pharmacy_amount = replacer(claimable_pharmacy(bill_data))
    hospital_service_amount = replacer(claimable_hospital(bill_data))
    diagnostic_amount = replacer(claimable_diagnostic(bill_data))
    operating_service_amount = replacer(claimable_operating_services(bill_data) if claimable_operating_services(bill_data) != '' else 0)
    equipment_amount = replacer(claimable_equipment(bill_data))
    professional_service_amount = replacer(claimable_profession_service(bill_data))
    print(professional_service_amount)
    
    total_billed_services = sum([replacer(bill_data['accommodation']['totalCharge']),
                                 replacer(bill_data['nursingCharges']['totalCharge']),
                                 replacer(bill_data['pharmacyAndConsumables']['totalCharge']),
                                 replacer(bill_data['hospitalServices']['totalCharge']),
                                 replacer(bill_data['diagnosticServices']['totalCharge']),
                                 replacer(bill_data['operativeServices']['totalCharge']),
                                 replacer(bill_data['equipmentUsed']['totalCharge']),
                                 replacer(bill_data['professionalServices']['totalCharge'])])

    other_charges = replacer(bill_data['billingDetails']['totalBillAmount']) - total_billed_services
    print(other_charges)

    # Summing up all the claimable amounts
    total_claimable = final_accomodable_amount + nursing_coverage + pharmacy_amount + hospital_service_amount + diagnostic_amount + operating_service_amount + equipment_amount + professional_service_amount
    
    final_claimable_amount = total_amount_check(policy_data, total_claimable)
    print(final_claimable_amount)

    # Return the calculated amounts along with the final claimable amount
    # return total_claimable, final_accomodable_amount, nursing_coverage, pharmacy_amount, hospital_service_amount, diagnostic_amount, operating_service_amount, equipment_amount, professional_service_amount
    return final_claimable_amount, final_accomodable_amount, nursing_coverage, pharmacy_amount, hospital_service_amount, diagnostic_amount, operating_service_amount, equipment_amount, professional_service_amount, other_charges

@app.get("/get-pdf-page-count/")
async def get_pdf_page_count(billurlpdf: str ,policyjson: str ,claimjson: str):
    try:
        # Download the PDF from the URL
        response = requests.get(billurlpdf)
        response.raise_for_status()  # Ensure the request was successful

        # Read the PDF
        pdf = PdfReader(BytesIO(response.content))

        if billurlpdf:
            pages = split_pdf(pdf)
            combined_text = []
            for page in pages:
                page_text = process_page(page)
                combined_text.append(page_text)
            combined_text_str = '\n\n'.join(combined_text)
            
            cons =  generate_structure_data_cons(combined_text_str)
            bill = generate_structure_data_wo_cons(combined_text_str)
            b_ind = bill.find('{')
            c_ind = cons.find('{')
            bill = bill[b_ind:]
            cons = cons[c_ind:]
            bill_data = json.loads(bill)
            cons_phar = json.loads(cons)

            
            pharmacy = cons_phar['unique_medicine']
            cons_data = cons_phar['unique_consumables']

            policy_data = fetch_json(policyjson)
            claim_data = fetch_json(claimjson)
            # json_file_path = policyjson
            # with open(json_file_path, 'r') as json_file:
            #             policy_data = json.load(json_file)
            # print(policy_data)
            # json_file_path = claimjson
            # with open(json_file_path, 'r') as json_file:
            #             claim_data = json.load(json_file)
            # print(claim_data)
            
            claim_submission_date= claim_data['claim_submission_date']
            policy_start_date= claim_data['policy_start_date']
            disease_type = claim_data['disease_type']
            print("Completed before disease")
            waiting_period = claim_data['waiting_period']
            print("waiting PEriod is done")
            claimable_amount, accommodation_amount, nursing_amount, pharmacy_amount, hospital_service_amount, diagnostic_amount, operating_service_amount, equipment_amount, professional_service_amount ,other_charges = calculate_claimable_amount(claim_submission_date, policy_start_date, disease_type, waiting_period, policy_data, bill_data)
            print(claimable_amount);
            # cons_df, ph_df, diag_df = claimable_check_table(pharmacy, cons_data, bill_data)

        return {"bill": bill_data , "consumable": cons_data ,"claimable_amount": claimable_amount,"unique_medicine":pharmacy ,"equipment_amount":equipment_amount ,"Accomodationamount":accommodation_amount ,"nursing_amount":nursing_amount,"operating_service_amount":operating_service_amount,"professional_service_amount":professional_service_amount,"pharmacy_amount":pharmacy_amount,"hospital_service_amount":hospital_service_amount,"diagnostic_amount":diagnostic_amount,"other_charges":other_charges,}
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error downloading PDF: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing : {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
