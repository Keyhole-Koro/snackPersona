variable "env" {
  description = "Environment (local, stage, prod)"
  type        = string
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "snack"
}

variable "region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "table_name" {
  description = "DynamoDB Table Name"
  type        = string
  default     = "SnackTable"
}
