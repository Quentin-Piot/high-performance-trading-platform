"""
Service de validation de mot de passe pour le backend.
Implémente les mêmes règles que le frontend pour assurer la cohérence.
"""
import re


class PasswordValidationRule:
    """Règle de validation de mot de passe."""
    def __init__(self, rule_id: str, test_func, message: str):
        self.id = rule_id
        self.test = test_func
        self.message = message
class PasswordValidationResult:
    """Résultat de la validation d'un mot de passe."""
    def __init__(self, is_valid: bool, failed_rules: list[str]):
        self.is_valid = is_valid
        self.failed_rules = failed_rules
class PasswordValidationService:
    """Service de validation de mot de passe côté backend."""
    RULES = [
        PasswordValidationRule(
            "min_length",
            lambda password: len(password) >= 8,
            "Le mot de passe doit contenir au moins 8 caractères"
        ),
        PasswordValidationRule(
            "has_uppercase",
            lambda password: re.search(r'[A-Z]', password) is not None,
            "Le mot de passe doit contenir au moins une lettre majuscule"
        ),
        PasswordValidationRule(
            "has_lowercase",
            lambda password: re.search(r'[a-z]', password) is not None,
            "Le mot de passe doit contenir au moins une lettre minuscule"
        ),
        PasswordValidationRule(
            "has_number",
            lambda password: re.search(r'\d', password) is not None,
            "Le mot de passe doit contenir au moins un chiffre"
        ),
        PasswordValidationRule(
            "has_symbol",
            lambda password: re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password) is not None,
            "Le mot de passe doit contenir au moins un symbole"
        )
    ]
    @classmethod
    def validate_password(cls, password: str) -> PasswordValidationResult:
        """
        Valide un mot de passe selon toutes les règles définies.
        Args:
            password: Le mot de passe à valider
        Returns:
            PasswordValidationResult: Résultat de la validation
        """
        failed_rules = []
        for rule in cls.RULES:
            if not rule.test(password):
                failed_rules.append(rule.message)
        is_valid = len(failed_rules) == 0
        return PasswordValidationResult(is_valid, failed_rules)
    @classmethod
    def is_password_valid(cls, password: str) -> bool:
        """
        Vérifie si le mot de passe respecte toutes les règles (validation simple).
        Args:
            password: Le mot de passe à valider
        Returns:
            bool: True si le mot de passe est valide, False sinon
        """
        return cls.validate_password(password).is_valid
    @classmethod
    def get_validation_errors(cls, password: str) -> list[str]:
        """
        Retourne la liste des erreurs de validation pour un mot de passe.
        Args:
            password: Le mot de passe à valider
        Returns:
            List[str]: Liste des messages d'erreur
        """
        return cls.validate_password(password).failed_rules