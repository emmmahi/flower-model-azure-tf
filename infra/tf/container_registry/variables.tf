variable "resource_group_location" {
  type        = string
  default     = "swedencentral"
  description = "Location of the resource group."
}

variable "identifier" {
  type        = string
  description = "Identifier. Makes sure multiple groups can work in same subscription."
  default = "emma"
}

variable "course_short_name" {
  type        = string
  default     = "olearn"
  description = "The short name of the course. This is used in the naming of the resources."

}

variable "default_tags" {
  type        = map(string)
  description = "Default tags that are applied to all resources."
  default = {
    Owner       = "KAMK"
    Environment = "student"
    CostCenter  = "1020"
    Course      = "TT00CC71-3001"
  }
}