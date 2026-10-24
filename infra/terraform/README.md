# Local infrastructure (Phase 6)

Terraform manages one optional bridge network for the API's frontend connection.
The default deployment remains Compose-only; no cloud provider or AWS credentials
are used. The provider version is pinned in `main.tf`.

The `compose.terraform.yaml` override replaces Compose's managed `frontend` network
with the external network Terraform creates. Docker Compose 2.24 or newer is needed
for the `!override` merge tag. The base `compose.yaml` behavior is unchanged.

If Terraform is not installed, install the Linux CLI inside Ubuntu WSL using the
[official HashiCorp Ubuntu/Debian instructions](https://developer.hashicorp.com/terraform/install).
Select Linux and follow the repository/key setup before `sudo apt install terraform`.
Verify with `terraform version`. Installing tools is separate from creating infrastructure.

From the project root, format, initialize, and validate the Terraform configuration:

```bash
cd infra/terraform
terraform fmt
terraform init -backend=false
terraform validate
terraform plan
```

Provider initialization requires access to the Terraform Registry. If the registry
returns a regional availability page, initialization and all provider-dependent checks
cannot run from that location. Follow [HashiCorp's trade controls guidance](https://www.hashicorp.com/trade-controls)
and use the default Compose-only deployment; do not disguise the connection location.

Initialization writes `.terraform.lock.hcl`; commit that file after reviewing it.
Inspect the plan before applying. Apply creates only the named Docker network:

```bash
terraform apply
```

Then start the app with the external network override from the project root:

```bash
docker compose -f compose.yaml -f compose.terraform.yaml \
  --env-file .env.example up -d --build
```

Commit `.terraform.lock.hcl`; never commit state, plans, or secrets. Local state can
contain sensitive values and must be protected. A future shared deployment needs a
remote backend with encryption, access control, and locking.
To remove the network, stop the override stack first without `-v`, then inspect and
approve `terraform destroy`. This does not remove the PostgreSQL named volume.
AWS is a future proposal only; this project must not create cloud resources automatically.
