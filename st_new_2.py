import streamlit as st
import json
from datetime import datetime, timedelta
import pandas as pd
import boto3
import streamlit as st
import io
from PyPDF2 import PdfReader, PdfWriter
import openai
from datetime import date


# Initialize the boto3 client for AWS Textract
textract_client = boto3.client('textract',
    region_name='us-east-1',
    aws_access_key_id="AKIAYUAZFQNZVZGPQQPW",
    aws_secret_access_key="sQTsadEhCaU8XN5I4lDm6nfrmmpH/sdbI++CWB9y"
)

# Utility Functions

def replacer(value):
    if value == '' or None:
        return float(0.00)
    if type(value) == float or type(value) == int:
        return value
    else:
        return float(value.replace(',', ''))


def split_pdf(pdf_file):
    """Split a PDF file into individual pages and return them as byte streams."""
    reader = PdfReader(pdf_file)
    pages = []
    for page in range(len(reader.pages)):
        writer = PdfWriter()
        writer.add_page(reader.pages[page])
        page_stream = io.BytesIO()
        writer.write(page_stream)
        page_stream.seek(0)
        pages.append(page_stream)
    return pages
def process_page(page_stream):
    """Process a single page using AWS Textract."""
    response = textract_client.detect_document_text(Document={'Bytes': page_stream.read()})
    extracted_text = []
    for item in response['Blocks']:
        if item['BlockType'] == 'LINE':
            extracted_text.append(item['Text'])
    return '\n'.join(extracted_text)

def generate_structure_data_wo_cons(extracted_text):
    client = openai.OpenAI(api_key='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')
    
    prompt = """You are a text extractor who extracts relevant patient information in a specified format from a hospital medical bill.

      1) Extract patient information and unique diagnostic services and their charges from the provided text
      2) Ensure that the unique diagnostic services encompasses a variety of tests, including but not limited to blood tests, imaging studies, and other medical procedures.  The goal is to compile a comprehensive list that may include services like "Sodium", "Complete Blood Count (CBC)", "X-Ray" and other commonly performed diagnostic tests.
      3) 'professionalServices' includes all the doctor consultation charges
      4) Ensure that the values for 'totalCharge' and 'amount' in various sections are represented as floating-point numbers and 0.00 if the value is not present.
      5) Ensure that the contents of 'otherCharges' are not repeated in any other section.
      6) Do no give me code


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
    client = openai.OpenAI(api_key='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')
    
    prompt = """You are a text extractor who extracts relevant patient information in a specified format from a hospital medical bill.

    1) "unique_medicine" includes tablets and injections only and not consumables like cotton, syringe, wipes, etc.
    2) Consumables are items used by doctors and nurses to treat patients. The goal is to compile a unique list of consumables that may include items like "Sodium Chloride", "Syringe", "Cotton" and other commonly used consumables.
    2) It is very critical that the list of unique consumables and list of unique pharmacy do not overlap.
    3) Ensure that the values for 'totalCharge' in various sections are represented as floating-point numbers and 0.00 if the value is not present.
    4) Ignore repetitions
    5) Do no give me code

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
    # print(python_code)
    return python_code


def load_json(uploaded_file):
    """Load a JSON file uploaded in Streamlit and return the data."""
    try:
        return json.load(uploaded_file)
    except Exception as e:
        st.error(f"Error loading JSON file: {e}")
        return None
def parse_date(date_str, format='%d-%m-%Y'):
    """Parse a date string into a datetime object."""
    try:
        return datetime.strptime(date_str, format)
    except ValueError as e:
        st.error(f"Error parsing date: {e}")
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
    waiting_period_end = policy_start_date + timedelta(days=365 * waiting_period)
    
    if submission_date < waiting_period_end:
        return disease in policy_data['policyDetails']['waitingPeriodCoverage']['coveredItems']
    
    st.success("Waiting period is over")
    return True

def check_grace_period(claim_data):
    if claim_data['documentDetails']['gracePeriodComparison'] == "False":
        return False
    return True 

def claimable_check_table(pharmacy, cons_data, bill_data):
    # create a dataframe for displaying cons_data in table format
    c = [True]*len(cons_data)
    cons_df = pd.DataFrame(cons_data, columns=['name_of_unique_consumable', 'totalCharge', 'claimable'])
    cons_df['claimable'] = c
    cons_df['totalCharge'] = [replacer(x) for x in cons_df['totalCharge']]
    # cons_edited_df = st.data_editor(cons_df)

    # create a dataframe for displaying pharmacy in table format
    p = [True]*len(pharmacy)
    ph_df = pd.DataFrame(pharmacy, columns=['name_of_unique_medicine', 'totalCharge', 'claimable'])
    ph_df['claimable'] = p
    ph_df['totalCharge'] = [replacer(x) for x in ph_df['totalCharge']]
    # ph_edited_df = st.data_editor(ph_df)

    d = [True]*len(bill_data['unique_diagnostic_services'])
    diag_df = pd.DataFrame(bill_data['unique_diagnostic_services'], columns=['name_of_unique_diagnostic_service', 'totalCharge', 'claimable'])
    diag_df['claimable'] = d
    diag_df['totalCharge'] = [replacer(x) for x in diag_df['totalCharge']]
    # diag_edited_df = st.data_editor(diag_df)

    # diag_c_amount = diag_edited_df[diag_edited_df['claimable']]['total_charge'].sum()
    # ph_c_amount = ph_edited_df[ph_edited_df['claimable']]['total_charge'].sum()
    # cons_c_amount = cons_edited_df[cons_edited_df['claimable']]['total_charge'].sum()
    
    return cons_df, ph_df, diag_df


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
    st.data_editor(charges_df)


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
    st.success(f"The accomodation charges per day that will be covered is {coverage_amount}")
    total_coverage_amount = coverage_amount * int(replacer(bill_data['accommodation']['daysStayed']))
    return total_coverage_amount,coverage_amount

def include_nursing_charges(bill_data, accommodation_coverage):
    return accommodation_coverage * (replacer(bill_data['nursingCharges']["totalCharge"]) / replacer(bill_data['accommodation']['totalCharge'])) if replacer(bill_data['accommodation']['totalCharge']) != 0 else 0

# Main Calculation Function
def calculate_claimable_amount(claimSubmissionDate, policyStartDate, disease, waiting_period, policy_data, bill_data):
    print('check1')
    if not check_waiting_period_clash(claimSubmissionDate, policyStartDate, disease, waiting_period, policy_data):
        return "Waiting period clash"

    (accommodation_coverage, single_day_accomodation) = calculate_accommodation_coverage(bill_data, policy_data)
    final_accomodable_amount = hospitalization_day(single_day_accomodation, accommodation_coverage)
    print(final_accomodable_amount)
    
    nursing_coverage = include_nursing_charges(bill_data, accommodation_coverage)
    # st.success(f"Nursing Charges that will be covered {nursing_coverage}")
    
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

    other_charges = 0
    for i in bill_data['otherCharges']:
        other_charges += replacer(i['amount'])
    print(other_charges)

    # Summing up all the claimable amounts
    total_claimable = final_accomodable_amount + nursing_coverage + pharmacy_amount + hospital_service_amount + diagnostic_amount + operating_service_amount + equipment_amount + professional_service_amount
    
    final_claimable_amount = total_amount_check(policy_data, total_claimable)
    print(final_claimable_amount)

    # Return the calculated amounts along with the final claimable amount
    # return total_claimable, final_accomodable_amount, nursing_coverage, pharmacy_amount, hospital_service_amount, diagnostic_amount, operating_service_amount, equipment_amount, professional_service_amount
    return final_claimable_amount, final_accomodable_amount, nursing_coverage, pharmacy_amount, hospital_service_amount, diagnostic_amount, operating_service_amount, equipment_amount, professional_service_amount, other_charges


# Streamlit Web Interface
def main():
    st.title("Insurance Claim Processing")
    
    with st.form(key='claim_form'):
        disease_type = st.selectbox('Type of Disease', ['Cancer', 'Heart Attack', 'Stroke', 'COVID-19'])
        claim_s_date = st.date_input('Claim Submission Date')
        claim_submission_date = claim_s_date.strftime('%d-%m-%Y')
        policy_s_date = st.date_input('Policy Start Date')
        policy_start_date = policy_s_date.strftime('%d-%m-%Y')
        waiting_period = st.number_input('Waiting Period (in years)', min_value=0, max_value=10, value=2)
        # grace_period_comparison = st.selectbox('Grace Period Comparison', ['True', 'False'])

        policy_type = st.selectbox('Policy Type', ['Individual', 'Family Floater'])

        uploaded_bill_file = st.file_uploader("Upload Bill File(PDF)", type="pdf")
        # wo_cons = st.file_uploader("Upload JSON File for structure data without consumables", type="json")
        # cons = st.file_uploader("Upload JSON File for structure data with consumables", type="json")

        if 'cons_df' not in st.session_state:
            st.session_state.cons_df = pd.DataFrame(columns = ['name_of_unique_consumable', 'totalCharge', 'claimable'])
        if 'ph_df' not in st.session_state:
            st.session_state.ph_df = pd.DataFrame(columns = ['name_of_unique_medicine', 'totalCharge', 'claimable'])
        if 'diag_df' not in st.session_state:
            st.session_state.diag_df = pd.DataFrame(columns = ['name_of_unique_diagnostic_service', 'totalCharge', 'claimable'])

        # Submit button
        submit = st.form_submit_button(label='Process Claim')

        # Process button
        if submit:

            if uploaded_bill_file is not None:
                pages = split_pdf(uploaded_bill_file)
                combined_text = []
                for i, page in enumerate(pages, start=1):
                    st.write(f"Processing page {i}...")
                    page_text = process_page(page)
                    combined_text.append(page_text)
                    combined_text_str = '\n\n'.join(combined_text)
                print('hello')
                print(combined_text_str)
                cons =  generate_structure_data_cons(combined_text_str)
                bill = generate_structure_data_wo_cons(combined_text_str)
                b_ind = bill.find('{')
                c_ind = cons.find('{')
                bill = bill[b_ind:]
                cons = cons[c_ind:]
                print(bill)
                print(cons)
                bill_data = json.loads(bill)
                cons_phar = json.loads(cons)

                pharmacy = cons_phar['unique_medicine']
                cons_data = cons_phar['unique_consumables']

                # bill_data = load_json(wo_cons)
                # cons = load_json(cons)
                print(bill_data)
                # cons_data = cons['name_of_unique_consumables']
                # print(cons_data)

                if policy_type == 'Individual':
                    json_file_path = '/Users/jenil/Desktop/PIWOT_HACKATHON/simplified_insurance_policy.json'
                    print('hi')
                    # Read the JSON file
                    with open(json_file_path, 'r') as json_file:
                        # Load the JSON data from the file
                        policy_data = json.load(json_file)
                print(policy_data)

                bill_data['accommodation']['totalCharge'] = 100000
                bill_data['accommodation']['dailyRate'] = 20000
                bill_data['accommodation']['daysStayed'] = 5
            
                # Process claim
                print('jenil')
                claimable_amount, accommodation_amount, nursing_amount, pharmacy_amount, hospital_service_amount, diagnostic_amount, operating_service_amount, equipment_amount, professional_service_amount ,other_charges = calculate_claimable_amount(claim_submission_date, policy_start_date, disease_type, waiting_period, policy_data, bill_data)
                st.session_state['claimable_amount'] = claimable_amount
                st.session_state['accommodation_amount'] = accommodation_amount
                st.session_state['nursing_amount'] = nursing_amount
                st.session_state['pharmacy_amount'] = pharmacy_amount
                st.session_state['hospital_service_amount'] = hospital_service_amount
                st.session_state['diagnostic_amount'] = diagnostic_amount
                st.session_state['operating_service_amount'] = operating_service_amount
                st.session_state['equipment_amount'] = equipment_amount
                st.session_state['professional_service_amount'] = professional_service_amount
                st.session_state['other_charges'] = other_charges
                st.session_state['policy_data'] = policy_data
                st.session_state['bill_data'] = bill_data

                cons_df, ph_df, diag_df = claimable_check_table(pharmacy, cons_data, bill_data)
                
                st.session_state['consumables'] = cons_df[cons_df['claimable']]['totalCharge'].sum()
                st.session_state['cons_df'] = cons_df
                st.session_state['ph_df'] = ph_df
                st.session_state['diag_df'] = diag_df


    with st.form(key='confirm_form'):
        cons_edit_df = st.data_editor(st.session_state['cons_df'], key='cons')
        pharmacy_edit_df = st.data_editor(st.session_state['ph_df'], key='pharma')
        diag_edit_df = st.data_editor(st.session_state['diag_df'], key='diagnos')
        
        confirm_details = st.form_submit_button(label='Confirm Details')
        if confirm_details:
            cons_edit = cons_edit_df[cons_edit_df['claimable']]['totalCharge'].sum()
            pharmacy_edit = pharmacy_edit_df[pharmacy_edit_df['claimable']]['totalCharge'].sum()
            diag_edit = diag_edit_df[diag_edit_df['claimable']]['totalCharge'].sum()

            # Display the detailed claimable amounts in a table
            print(type(pharmacy_edit), type(cons_edit), type(st.session_state['consumables']), type(st.session_state['accommodation_amount']), type(st.session_state['nursing_amount']), type(st.session_state['hospital_service_amount']), type(diag_edit), type(st.session_state['operating_service_amount']), type(st.session_state['equipment_amount']), type(st.session_state['professional_service_amount']), type(st.session_state['other_charges']))
            final_claim = float(pharmacy_edit) + float(cons_edit) + replacer(st.session_state['accommodation_amount']) + replacer(st.session_state['nursing_amount']) + replacer(st.session_state['hospital_service_amount']) + float(diag_edit) + replacer(st.session_state['operating_service_amount']) + replacer(st.session_state['equipment_amount']) + replacer(st.session_state['professional_service_amount']) + replacer(st.session_state['other_charges'])
            display_bill_details_in_table(pharmacy_edit, cons_edit, st.session_state['consumables'], st.session_state['bill_data'], st.session_state['accommodation_amount'], st.session_state['nursing_amount'], st.session_state['hospital_service_amount'], diag_edit, st.session_state['operating_service_amount'], st.session_state['equipment_amount'], st.session_state['professional_service_amount'], final_claim, st.session_state['other_charges'])
            st.write(f"The claimable amount is: {final_claim}")


if __name__ == "__main__":
    main()
