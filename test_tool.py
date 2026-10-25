from agents.tools import lookup_company

# Harbourside: should be found, active, about 12 years since incorporation
print(lookup_company.invoke({"company_number": "08123456"}))

# An unknown company number
print(lookup_company.invoke({"company_number": "99999999"}))