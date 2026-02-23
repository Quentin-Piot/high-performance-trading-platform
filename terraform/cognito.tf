resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-${var.env}-user-pool"

  alias_attributes         = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }

  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = "0"
      max_length = "2048"
    }
  }

  schema {
    name                     = "name"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {}
  }

  schema {
    name                     = "google_sub"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = true

    string_attribute_constraints {
      min_length = "0"
      max_length = "256"
    }
  }

  schema {
    name                     = "provider"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = true

    string_attribute_constraints {
      min_length = "0"
      max_length = "64"
    }
  }

  tags = {
    Name        = "${var.project_name}-user-pool"
    Project     = var.project_name
    Environment = var.env
    ManagedBy   = "terraform"
  }
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${var.env}-${random_string.bucket_suffix.result}"
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_cognito_user_pool_client" "web_client" {
  name         = "${var.project_name}-web-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]

  callback_urls = [
    "http://localhost:5173/auth/callback",
    "http://localhost:8000/api/v1/auth/google/callback",
    "https://${var.frontend_alias_domain != "" ? var.frontend_alias_domain : "localhost"}/api/v1/auth/google/callback"
  ]

  logout_urls = [
    "http://localhost:5173/",
    "https://${var.frontend_alias_domain != "" ? var.frontend_alias_domain : "localhost"}/"
  ]

  supported_identity_providers = var.google_client_id != "" && var.google_client_secret != "" ? ["COGNITO", "Google"] : ["COGNITO"]

  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  prevent_user_existence_errors = "ENABLED"

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]
}

resource "aws_cognito_identity_provider" "google" {
  count = var.google_client_id != "" && var.google_client_secret != "" ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id        = var.google_client_id
    client_secret    = var.google_client_secret
    authorize_scopes = "email openid profile"
  }

  attribute_mapping = {
    email    = "email"
    name     = "name"
    username = "sub"
  }
}

resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${var.project_name}-${var.env}-identity-pool"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.web_client.id
    provider_name           = aws_cognito_user_pool.main.endpoint
    server_side_token_check = false
  }

  supported_login_providers = var.google_client_id != "" ? {
    "accounts.google.com" = var.google_client_id
  } : {}

  tags = {
    Name        = "${var.project_name}-identity-pool"
    Project     = var.project_name
    Environment = var.env
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role" "authenticated" {
  name = "${var.project_name}-${var.env}-cognito-authenticated"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })
}

resource "aws_cognito_identity_pool_roles_attachment" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id

  roles = {
    authenticated = aws_iam_role.authenticated.arn
  }
}
