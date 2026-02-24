export interface PasswordValidationRule {
	id: string;
	test: (password: string) => boolean;
	messageKey: string;
	isValid?: boolean;
}
export interface PasswordValidationResult {
	isValid: boolean;
	rules: PasswordValidationRule[];
	score: number;
}

const passwordValidationRules: PasswordValidationRule[] = [
	{
		id: "minLength",
		test: (password: string) => password.length >= 8,
		messageKey: "auth.password.validation.minLength",
	},
	{
		id: "hasUppercase",
		test: (password: string) => /[A-Z]/.test(password),
		messageKey: "auth.password.validation.hasUppercase",
	},
	{
		id: "hasLowercase",
		test: (password: string) => /[a-z]/.test(password),
		messageKey: "auth.password.validation.hasLowercase",
	},
	{
		id: "hasNumber",
		test: (password: string) => /\d/.test(password),
		messageKey: "auth.password.validation.hasNumber",
	},
	{
		id: "hasSymbol",
		test: (password: string) =>
			/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password),
		messageKey: "auth.password.validation.hasSymbol",
	},
];

function getPasswordStrength(
	score: number,
): "weak" | "fair" | "good" | "strong" {
	if (score < 40) return "weak";
	if (score < 60) return "fair";
	if (score < 80) return "good";
	return "strong";
}

export const PasswordValidationService = {
	validatePassword(password: string): PasswordValidationResult {
		const validatedRules = passwordValidationRules.map((rule) => ({
			...rule,
			isValid: rule.test(password),
		}));
		const validRulesCount = validatedRules.filter(
			(rule) => rule.isValid,
		).length;
		const isValid = validRulesCount === passwordValidationRules.length;
		const score = Math.round(
			(validRulesCount / passwordValidationRules.length) * 100,
		);
		return {
			isValid,
			rules: validatedRules,
			score,
		};
	},
	isPasswordValid(password: string): boolean {
		return PasswordValidationService.validatePassword(password).isValid;
	},
	getPasswordStrength,
	getPasswordStrengthColor(score: number): string {
		const strength = getPasswordStrength(score);
		switch (strength) {
			case "weak":
				return "text-red-600";
			case "fair":
				return "text-orange-500";
			case "good":
				return "text-yellow-500";
			case "strong":
				return "text-green-600";
			default:
				return "text-gray-500";
		}
	},
	getPasswordStrengthBgColor(score: number): string {
		const strength = getPasswordStrength(score);
		switch (strength) {
			case "weak":
				return "bg-red-500";
			case "fair":
				return "bg-orange-500";
			case "good":
				return "bg-yellow-500";
			case "strong":
				return "bg-green-500";
			default:
				return "bg-gray-300";
		}
	},
};
