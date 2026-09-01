# Security and Privacy

CommerceIQ is a portfolio analytics project built from the public Olist dataset.
It must not contain credentials, private customer data, or proprietary business
information.

## Local configuration

- Store database credentials only in `.env`; the file is ignored by Git.
- Use `.env.example` as the credential-free configuration template.
- Keep downloaded source CSVs and generated processed datasets under `data/`;
  both locations are ignored except for their directory placeholders.
- Review Power BI data-source settings before sharing the PBIX because desktop
  reports can retain a local workbook location in their connection metadata.

## Reporting a problem

If a credential or private file is committed accidentally, remove it from the
repository, rotate the affected credential, and clean the Git history before
changing the repository visibility.
