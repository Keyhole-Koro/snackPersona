terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.region
}

module "db" {
  source     = "../../terraform/service/db"
  table_name = var.table_name
}

module "simulation" {
  source     = "../../terraform/service/simulation"
  env        = var.env
  table_name = module.db.table_name
  table_arn  = module.db.table_arn
}

output "table_name" {
  value = module.db.table_name
}

output "table_arn" {
  value = module.db.table_arn
}
