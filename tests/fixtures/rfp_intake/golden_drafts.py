"""Golden PHI-free draft fixtures for evaluator tests."""

US_REVENUE_DRAFT = """
## Revenue proposal section
Client: Meridian Manufacturing (US)
Program: occupational health

### Coverage of key aspects
- Fixed monthly retainer in USD for 12 months
- Payment net-30 via ACH

### Business Associate Agreement
This proposal includes a Business Associate Agreement (BAA) under HIPAA.

Pricing will be quoted in USD.
""".strip()

UK_COMPLIANCE_DRAFT = """
## Compliance proposal section
Client: Thames Valley University (UK)

### Data Processing Agreement
This proposal includes a Data Processing Agreement (DPA) referencing UK GDPR.

Pricing will be quoted in GBP (£).
""".strip()

US_MISSING_BAA = """
## Revenue section
Pricing in EUR (€1000/month) for Meridian.
No regulatory agreement language.
""".strip()
