# Configuration Google OAuth avec AWS Cognito

Ce guide explique comment configurer l'authentification Google OAuth avec AWS Cognito pour la plateforme de trading.

## Prérequis

1. Un compte Google Cloud Platform
2. Un projet Google Cloud configuré
3. L'infrastructure AWS Cognito déployée via Terraform

## Étapes de configuration

### 1. Configuration Google Cloud Console

1. Accédez à la [Google Cloud Console](https://console.cloud.google.com/)
2. Sélectionnez votre projet ou créez-en un nouveau
3. Activez l'API Google+ si ce n'est pas déjà fait
4. Allez dans "APIs & Services" > "Credentials"
5. Cliquez sur "Create Credentials" > "OAuth 2.0 Client IDs"
6. Sélectionnez "Web application" comme type d'application
7. Configurez les URIs de redirection autorisées :
   - `https://trading-platform-staging-c039edc1.auth.eu-west-3.amazoncognito.com/oauth2/idpresponse`
   - `http://localhost:5173/auth/callback` (pour le développement local)
8. Notez le Client ID et Client Secret générés

### 2. Configuration Terraform

1. Ajoutez les variables Google OAuth dans votre fichier `terraform.tfvars` :
   ```hcl
   google_client_id     = "your-google-client-id"
   google_client_secret = "your-google-client-secret"
   ```

2. Appliquez les changements Terraform :
   ```bash
   cd terraform
   terraform plan
   terraform apply
   ```

### 3. Vérification de la configuration

Après l'application Terraform, vérifiez que :
- Le fournisseur d'identité Google est créé dans Cognito
- Le client Cognito supporte maintenant "Google" dans `supported_identity_providers`
- L'Identity Pool Cognito inclut Google dans `supported_login_providers`

### 4. Test de l'intégration

1. Démarrez l'application frontend : `npm run dev`
2. Accédez à la page de connexion
3. Cliquez sur "Se connecter avec Google"
4. Vérifiez que la redirection vers Google fonctionne
5. Après authentification Google, vérifiez que l'utilisateur est bien connecté

## URLs importantes

- **Cognito Hosted UI** : `https://trading-platform-staging-c039edc1.auth.eu-west-3.amazoncognito.com`
- **Frontend local** : `http://localhost:5173`
- **Backend API** : `http://localhost:8000`

## Dépannage

### Erreur "redirect_uri_mismatch"
- Vérifiez que l'URI de redirection dans Google Cloud Console correspond exactement à celle utilisée par Cognito
- L'URI Cognito suit le format : `https://{cognito-domain}.auth.{region}.amazoncognito.com/oauth2/idpresponse`

### Erreur "invalid_client"
- Vérifiez que le Client ID et Client Secret sont correctement configurés dans Terraform
- Assurez-vous que les variables sont bien passées à la ressource `aws_cognito_identity_provider`

### L'utilisateur n'est pas synchronisé en base
- Vérifiez que l'endpoint `/auth/google/callback` du backend traite correctement les tokens Cognito
- Assurez-vous que l'attribut mapping dans Cognito est correct (email, name, username)