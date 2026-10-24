### Integration Business

integracion de redes sociales

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app integration_business
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/integration_business
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit


##########
# WhatsApp
/api/method/integration_business.api.whatsapp.webhook

# WhatsApp
/api/method/integration_business.api.messenger.webhook

# crm
/api/method/integration_business.api.crm.create_lead

# landing pages
/api/method/integration_business.api.landing.capture


# Test Local
bench new-site miIntegracion.local
bench --site miIntegracion.local install-app integration_business

# run
bench start

CREATE USER 'frappe_admin'@'localhost' IDENTIFIED BY 'admin01';
GRANT ALL PRIVILEGES ON *.* TO 'frappe_admin'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EXIT;

# Configurar token meta
meta_verify_token "verify_seguro_123"

# local
bench --site miIntegracion.local set-config meta_verify_token 'verify_seguro_123'

# local probar

curl -i -G 'http://miIntegracion.local:8000/api/method/integration_business.api.whatsapp.webhook' \
  --data-urlencode 'hub.mode=subscribe' \
  --data-urlencode 'hub.verify_token=verify_seguro_123' \
  --data-urlencode 'hub.challenge=123456'

# usar en servidor
https://<tu-sitio>.frappe.cloud/api/method/integration_business.api.whatsapp.webhook
