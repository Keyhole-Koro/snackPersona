bucket         = "terraform-state-stage-snack-12345"
key            = "snackPersona/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "terraform-lock"
