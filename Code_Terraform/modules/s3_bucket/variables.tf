variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket"
}

variable "force_destroy" {
  type    = bool
  default = false
}

variable "enable_versioning" {
  type    = bool
  default = false
}

variable "enable_encryption" {
  type    = bool
  default = true
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "lifecycle_rules" {
  type = list(object({
    id              = string
    status          = string
    prefix          = optional(string)
    expiration_days = optional(number)
    transitions = optional(list(object({
      days          = number
      storage_class = string
    })))
  }))
  default = []
}

variable "bucket_policy" {
  type    = string
  default = null
}

variable "tags" {
  type    = map(string)
  default = {}
}
