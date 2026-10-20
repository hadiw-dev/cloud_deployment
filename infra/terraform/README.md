# Local infrastructure (Phase 6)

This directory is reserved for an optional Terraform-managed Docker network.
There are no Terraform resources yet. Do not run apply until Phase 6 is implemented.

The default deployment will use Compose-managed networking without Terraform or
AWS credentials. A separate Compose override will reference the Terraform network
as external, allowing the same application to demonstrate local Infrastructure as Code.

Terraform is currently missing. Install the Linux CLI inside Ubuntu WSL using the
[official HashiCorp Ubuntu/Debian instructions](https://developer.hashicorp.com/terraform/install).
Select Linux and follow the repository/key setup before `sudo apt install terraform`.
Verify with `terraform version`. Installing tools is separate from creating infrastructure.

Planned verification: `terraform fmt -check`, `terraform init -backend=false`, and
`terraform validate`; then inspect `terraform plan` before any approved apply.
Commit the generated `.terraform.lock.hcl`; never commit state, plans, or secrets.
Local state can contain sensitive values and must be protected. A future shared
deployment needs a remote backend with encryption, access control, and locking.

Destroying this network must not remove the PostgreSQL named volume. Stop Compose
services first without `-v`, then destroy only resources declared here.
AWS is a future proposal only; this project must not create cloud resources automatically.
