import { createContext, useCallback, useContext, useEffect, useState } from "react";

const DICT = {
  en: {
    "nav.give": "Give a gift", "nav.dashboard": "Dashboard", "nav.admin": "Admin", "nav.login": "Sign in",
    "nav.logout": "Log out", "nav.menu": "Open menu", "nav.home": "Home", "nav.lang": "Language",
    "footer.privacy": "Privacy Policy", "footer.terms": "Terms of Use", "footer.contact": "Contact",
    "common.loading": "Loading…", "common.save": "Save", "common.cancel": "Cancel", "common.back": "Back",
    "common.copy": "Copy code", "common.copied": "Code copied", "common.reveal": "Show code", "common.hide": "Hide code",
    "common.demo": "DEMO", "common.optional": "optional",
    "login.title": "Sign in to giftaol.ca", "login.subtitle": "Sign in or create an account to give a gift.",
    "login.google": "Continue with Google", "login.or": "or",
    "login.tab_password": "Email and password", "login.tab_code": "Email me a code",
    "login.email": "Email address", "login.password": "Password", "login.submit": "Sign in",
    "login.no_password": "New here, or forgot your password? Use \"Email me a code\".",
    "login.code_intro": "We will email you a 6-digit code. Use it to create your account or set a new password.",
    "login.send_code": "Send me a code", "login.code_sent": "We sent a code to {email}. Check your inbox (and spam folder).",
    "login.code": "Verification code", "login.new_password": "Choose a password", "login.confirm_password": "Confirm password",
    "login.password_hint": "At least 8 characters.", "login.verify": "Verify and continue",
    "login.use_other_email": "Use a different email", "login.resend": "Send a new code",
    "login.mismatch": "The two passwords do not match.", "login.captcha_needed": "Please complete the security check first.",
    "login.welcome": "Welcome!",
    "turnstile.label": "Security check",
    "dash.title": "Your gifts", "dash.subtitle": "Every gift you have given, and how it has been used.",
    "dash.new": "New gift", "dash.tab_gifts": "My gifts", "dash.tab_account": "Account",
    "dash.empty_title": "You have not given a gift yet",
    "dash.empty_body": "Choose an amount, get a gift code by email, and pass it to a friend or family member who would like to try an Art of Living course.",
    "dash.total_given": "Total given", "dash.remaining": "Remaining balance", "dash.gifts_count": "Gifts",
    "dash.original": "Amount", "dash.balance": "Balance", "dash.for": "For", "dash.uses": "Uses",
    "dash.no_uses": "Not used yet", "dash.view": "View details", "dash.resend": "Resend email", "dash.resent": "Email sent again",
    "dash.email_failed": "Email not delivered", "dash.locked": "Locked",
    "status.active": "Active", "status.partly_used": "Partly used", "status.used_up": "Used up", "status.revoked": "Revoked",
    "acct.title": "Account", "acct.email": "Email", "acct.change_pw": "Change password", "acct.set_pw": "Set a password",
    "acct.set_pw_hint": "You signed in with Google. Set a password to also sign in with your email.",
    "acct.current": "Current password", "acct.new": "New password", "acct.confirm": "Confirm new password",
    "acct.updated": "Password updated", "acct.logout": "Log out",
    "new.title": "Give a gift", "new.subtitle": "Choose an amount and add a personal touch.",
    "new.amount": "Gift amount (CAD)", "new.range": "Allowed: {range}", "new.message": "Message for the recipient",
    "new.message_hint": "Included in your email so you can forward it with the code.",
    "new.recipient": "Recipient's first name", "new.recipient_hint": "Used only in the email greeting.",
    "new.how": "How this amount is used", "new.continue": "Continue to payment",
    "new.continue_next": "Continue to next step",
    "new.your_email": "Your email address",
    "new.your_email_note": "This is your own email (the person giving the gift), not the recipient's email. We will send the verification code and the gift code here.",
    "verify.title": "Verify your email",
    "verify.sent": "A verification code has been sent to your email. Please verify your code here before continuing to the payment.",
    "verify.btn": "Verify code", "verify.ok": "Email verified. You can now continue to payment.",
    "verify.change": "Change email or send a new code",
    "verify.registered": "This email already has an account. You can enter the code we sent, or sign in with your password instead.",
    "verify.choose": "Choose how to verify", "verify.use_code": "Verification code", "verify.use_password": "My password",
    "verify.pw_btn": "Sign in",
    "new.range_min": "at least {min}", "new.range_both": "between {min} and {max}",
    "new.out_of_range": "Please enter an amount {range}.",
    "pay.title": "Payment", "pay.demo_title": "Demo payment — no money will be charged",
    "pay.demo_body": "This is a demonstration. Clicking Pay marks the payment as processed and creates a real gift code for testing.",
    "pay.summary": "Gift amount", "pay.pay": "Pay {amount}", "pay.processing": "Processing…",
    "pay.unavailable": "Payment is not available yet",
    "pay.providers_note": "Integration can be done with Zeffy or other payment providers like Stripe, PayPal, etc.",
    "gift.ready": "Your gift is ready", "gift.ready_sub": "We also emailed these details to you.",
    "gift.detail": "Gift details", "gift.code": "Gift code", "gift.next": "Next steps",
    "gift.message": "Your message", "gift.uses": "Uses of this code", "gift.course": "Course",
    "gift.used": "Amount used", "gift.after": "Balance after", "gift.date": "Date", "gift.back": "Back to my gifts",
    "gift.email_status": "Email status", "gift.email_sent": "Sent", "gift.email_pending": "Sending…", "gift.email_failed": "Failed",
    "gift.demo_note": "Demo gift: created with a demo payment. No money was charged.",
    "gift.security_title": "Before you share",
    "admin.title": "Admin", "admin.tab_content": "Landing page", "admin.tab_config": "Configuration", "admin.tab_monitor": "Hack monitor",
    "landing.learn": "How it works", "landing.signin": "Get started",
    "legal.draft": "Draft — have counsel review before launch.",
    "notfound.title": "Page not found", "notfound.body": "The page you are looking for does not exist.",
  },
  fr: {
    "nav.give": "Offrir un cadeau", "nav.dashboard": "Tableau de bord", "nav.admin": "Admin", "nav.login": "Se connecter",
    "nav.logout": "Se déconnecter", "nav.menu": "Ouvrir le menu", "nav.home": "Accueil", "nav.lang": "Langue",
    "footer.privacy": "Politique de confidentialité", "footer.terms": "Conditions d'utilisation", "footer.contact": "Contact",
    "common.loading": "Chargement…", "common.save": "Enregistrer", "common.cancel": "Annuler", "common.back": "Retour",
    "common.copy": "Copier le code", "common.copied": "Code copié", "common.reveal": "Afficher le code", "common.hide": "Masquer le code",
    "common.demo": "DÉMO", "common.optional": "facultatif",
    "login.title": "Connexion à giftaol.ca", "login.subtitle": "Connectez-vous ou créez un compte pour offrir un cadeau.",
    "login.google": "Continuer avec Google", "login.or": "ou",
    "login.tab_password": "Courriel et mot de passe", "login.tab_code": "Recevoir un code par courriel",
    "login.email": "Adresse courriel", "login.password": "Mot de passe", "login.submit": "Se connecter",
    "login.no_password": "Nouveau ou mot de passe oublié? Utilisez « Recevoir un code par courriel ».",
    "login.code_intro": "Nous vous enverrons un code à 6 chiffres. Utilisez-le pour créer votre compte ou définir un nouveau mot de passe.",
    "login.send_code": "M'envoyer un code", "login.code_sent": "Nous avons envoyé un code à {email}. Vérifiez votre boîte de réception (et vos courriels indésirables).",
    "login.code": "Code de vérification", "login.new_password": "Choisissez un mot de passe", "login.confirm_password": "Confirmez le mot de passe",
    "login.password_hint": "Au moins 8 caractères.", "login.verify": "Vérifier et continuer",
    "login.use_other_email": "Utiliser une autre adresse", "login.resend": "Envoyer un nouveau code",
    "login.mismatch": "Les deux mots de passe ne correspondent pas.", "login.captcha_needed": "Veuillez d'abord compléter la vérification de sécurité.",
    "login.welcome": "Bienvenue!",
    "turnstile.label": "Vérification de sécurité",
    "dash.title": "Vos cadeaux", "dash.subtitle": "Tous les cadeaux que vous avez offerts et leur utilisation.",
    "dash.new": "Nouveau cadeau", "dash.tab_gifts": "Mes cadeaux", "dash.tab_account": "Compte",
    "dash.empty_title": "Vous n'avez pas encore offert de cadeau",
    "dash.empty_body": "Choisissez un montant, recevez un code-cadeau par courriel et remettez-le à un ami ou à un proche qui aimerait essayer un cours de l'Art de vivre.",
    "dash.total_given": "Total offert", "dash.remaining": "Solde restant", "dash.gifts_count": "Cadeaux",
    "dash.original": "Montant", "dash.balance": "Solde", "dash.for": "Pour", "dash.uses": "Utilisations",
    "dash.no_uses": "Pas encore utilisé", "dash.view": "Voir les détails", "dash.resend": "Renvoyer le courriel", "dash.resent": "Courriel renvoyé",
    "dash.email_failed": "Courriel non livré", "dash.locked": "Verrouillé",
    "status.active": "Actif", "status.partly_used": "Partiellement utilisé", "status.used_up": "Épuisé", "status.revoked": "Révoqué",
    "acct.title": "Compte", "acct.email": "Courriel", "acct.change_pw": "Changer le mot de passe", "acct.set_pw": "Définir un mot de passe",
    "acct.set_pw_hint": "Vous vous êtes connecté avec Google. Définissez un mot de passe pour aussi vous connecter avec votre courriel.",
    "acct.current": "Mot de passe actuel", "acct.new": "Nouveau mot de passe", "acct.confirm": "Confirmez le nouveau mot de passe",
    "acct.updated": "Mot de passe mis à jour", "acct.logout": "Se déconnecter",
    "new.title": "Offrir un cadeau", "new.subtitle": "Choisissez un montant et ajoutez une touche personnelle.",
    "new.amount": "Montant du cadeau ($ CA)", "new.range": "Permis : {range}", "new.message": "Message pour le destinataire",
    "new.message_hint": "Inclus dans votre courriel pour que vous puissiez le transférer avec le code.",
    "new.recipient": "Prénom du destinataire", "new.recipient_hint": "Utilisé seulement dans la salutation du courriel.",
    "new.how": "Comment ce montant est utilisé", "new.continue": "Passer au paiement",
    "new.continue_next": "Passer à l'étape suivante",
    "new.your_email": "Votre adresse courriel",
    "new.your_email_note": "Il s'agit de votre propre courriel (la personne qui offre le cadeau), et non de celui du destinataire. Nous y enverrons le code de vérification et le code-cadeau.",
    "verify.title": "Vérifiez votre courriel",
    "verify.sent": "Un code de vérification a été envoyé à votre courriel. Veuillez valider votre code ici avant de passer au paiement.",
    "verify.btn": "Valider le code", "verify.ok": "Courriel vérifié. Vous pouvez maintenant passer au paiement.",
    "verify.change": "Changer de courriel ou envoyer un nouveau code",
    "verify.registered": "Cette adresse a déjà un compte. Vous pouvez saisir le code envoyé ou vous connecter avec votre mot de passe.",
    "verify.choose": "Choisissez comment vérifier", "verify.use_code": "Code de vérification", "verify.use_password": "Mon mot de passe",
    "verify.pw_btn": "Se connecter",
    "new.range_min": "d'au moins {min}", "new.range_both": "entre {min} et {max}",
    "new.out_of_range": "Veuillez saisir un montant {range}.",
    "pay.title": "Paiement", "pay.demo_title": "Paiement de démonstration — aucun montant ne sera facturé",
    "pay.demo_body": "Ceci est une démonstration. En cliquant sur Payer, le paiement est marqué comme traité et un vrai code-cadeau est créé pour les essais.",
    "pay.summary": "Montant du cadeau", "pay.pay": "Payer {amount}", "pay.processing": "Traitement…",
    "pay.unavailable": "Le paiement n'est pas encore disponible",
    "pay.providers_note": "L'intégration peut se faire avec Zeffy ou d'autres fournisseurs de paiement comme Stripe, PayPal, etc.",
    "gift.ready": "Votre cadeau est prêt", "gift.ready_sub": "Nous vous avons aussi envoyé ces détails par courriel.",
    "gift.detail": "Détails du cadeau", "gift.code": "Code-cadeau", "gift.next": "Prochaines étapes",
    "gift.message": "Votre message", "gift.uses": "Utilisations de ce code", "gift.course": "Cours",
    "gift.used": "Montant utilisé", "gift.after": "Solde après", "gift.date": "Date", "gift.back": "Retour à mes cadeaux",
    "gift.email_status": "État du courriel", "gift.email_sent": "Envoyé", "gift.email_pending": "Envoi…", "gift.email_failed": "Échec",
    "gift.demo_note": "Cadeau de démonstration : créé avec un paiement de démo. Aucun montant n'a été facturé.",
    "gift.security_title": "Avant de partager",
    "admin.title": "Admin", "admin.tab_content": "Page d'accueil", "admin.tab_config": "Configuration", "admin.tab_monitor": "Moniteur d'intrusion",
    "landing.learn": "Comment ça marche", "landing.signin": "Commencer",
    "legal.draft": "Ébauche — à faire réviser par un conseiller juridique avant le lancement.",
    "notfound.title": "Page introuvable", "notfound.body": "La page que vous cherchez n'existe pas.",
  },
};

const LangCtx = createContext(null);

function initialLang() {
  const saved = localStorage.getItem("giftaol_lang");
  if (saved === "en" || saved === "fr") return saved;
  const l = (navigator.language || "en").slice(0, 2).toLowerCase() === "fr" ? "fr" : "en";
  localStorage.setItem("giftaol_lang", l);
  return l;
}

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(initialLang);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = useCallback((l) => {
    localStorage.setItem("giftaol_lang", l);
    setLangState(l);
  }, []);
  const t = useCallback((key, vars = {}) => {
    let s = DICT[lang][key] ?? DICT.en[key] ?? key;
    Object.entries(vars).forEach(([k, v]) => { s = s.replace(`{${k}}`, v); });
    return s;
  }, [lang]);
  return <LangCtx.Provider value={{ lang, setLang, t }}>{children}</LangCtx.Provider>;
}

export const useLang = () => useContext(LangCtx);
