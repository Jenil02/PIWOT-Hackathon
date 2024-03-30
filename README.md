# PIWOT-Hackathon

The repository contains the code we wrote for PIWOT Hackathon where we achieved 2nd place. 
Team - Abhishek Gupta(abhishek-cmd13), Jenil Sheth (Jenil02).
We built an AI SaaS tool that can intelligently decide the reimbursible amount after analyzing the policy and the bill pdf. This tool automises the medical claim processing and drastically reduces the processing time.

Problem - Insurance companies currently have operationally heavy claim examination process as of now, which manually examins thousands of claim and are bound to grow significantly over years. Despite having insurance, patients have to :-
- wait for 30 days for reimbursement.
- suffer through cash crunch.
- company has to go through hassle of managing thousands of claims and queries.
- company has to pay huge amount for processing every claim to outsourcing company.

Solution - An AI SaaS tool that can intelligently decide the reimbursible amount after analyzing the policy and the bill (In normal pdf format) and stating the appropriate clauses implemented.

Process:-
1) Customer will select their medical plan and upload their medical documents required for claim processing
2) OCR will read the document and feed the processed data and medical plan name into the GPT LLM
3) GPT has a prompt template and company’s medical plan details based on which the data is analyzed to provide which costs are eligible for claim and which not with their appropriate clause provided next to it

Tech Stack :-
Frontend - Flutter
Backend - NodeJS
Language - Python
