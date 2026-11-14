HERO_IMG = "https://images.pexels.com/photos/14189966/pexels-photo-14189966.jpeg?auto=compress&cs=tinysrgb&w=1400"

NEXT_STEPS_EN = [
    "Contact the person personally, and tell them you are sending them an email with a gift code for an Art of Living course.",
    "Forward the email with the code to that person.",
    "If they are not interested in the gift, you may choose another person and send the gift to them instead.",
    "Once the email is sent, anyone with the code can use it. Keep it private until you have given it to the right person.",
    "The code can be used more than once until its full amount is used. Each time it is used, you will get an email with the course and the remaining balance.",
]
NEXT_STEPS_FR = [
    "Communiquez personnellement avec la personne et dites-lui que vous lui envoyez un courriel contenant un code-cadeau pour un cours de l'Art de vivre.",
    "Transférez le courriel contenant le code à cette personne.",
    "Si elle n'est pas intéressée par le cadeau, vous pouvez choisir une autre personne et le lui offrir.",
    "Une fois le courriel envoyé, toute personne qui possède le code peut l'utiliser. Gardez-le confidentiel jusqu'à ce que vous l'ayez remis à la bonne personne.",
    "Le code peut être utilisé plusieurs fois jusqu'à ce que son montant total soit épuisé. Chaque utilisation vous vaudra un courriel indiquant le cours et le solde restant.",
]

DEFAULT_CONFIG = {
    "min_amount": 100,
    "max_amount": None,
    "payment_mode": "placeholder",
    "email_from_name": "",
    "email_reply_to": "",
    "code_request_limit": 5,
    "wrong_entry_cap": 5,
    "features": {"google_login": True, "resend_email_button": True},
    "texts": {
        "explainer": {
            "en": "This amount is applied as a discount when the Recipient registers for an Art of Living course through Harmony. The Recipient pays the rest of the course fee. The code can be used for any AOL program on artofliving.org.",
            "fr": "Ce montant est appliqué comme rabais lorsque le destinataire s'inscrit à un cours de l'Art de vivre par l'entremise de Harmony. Le destinataire paie le reste des frais du cours. Le code peut être utilisé pour tout programme de l'Art de vivre sur artofliving.org.",
        },
        "banner": {
            "en": "This code has been registered with Art of Living and can be used during AOL course registration.",
            "fr": "Ce code a été enregistré auprès de l'Art de vivre et peut être utilisé lors de l'inscription à un cours de l'Art de vivre.",
        },
        "security": {
            "en": "Share this code securely with the person you are gifting it to. Art of Living and giftaol.ca are not responsible if the code is shared or leaked by anyone.",
            "fr": "Partagez ce code de façon sécurisée avec la personne à qui vous l'offrez. L'Art de vivre et giftaol.ca ne sont pas responsables si le code est partagé ou divulgué par quiconque.",
        },
        "next_steps": {"en": NEXT_STEPS_EN, "fr": NEXT_STEPS_FR},
        "payment_placeholder": {
            "en": "Online payment integration will be added later. For now, gifts can only be created in demo mode.",
            "fr": "L'intégration du paiement en ligne sera ajoutée plus tard. Pour l'instant, les cadeaux ne peuvent être créés qu'en mode démo.",
        },
    },
}

DEFAULT_CONTENT = {
    "en": {
        "hero_badge": "Art of Living Canada",
        "hero_title": "Give someone you love the gift of breath",
        "hero_subtitle": "Pay it forward. Choose an amount, receive a gift code by email, and pass it to a friend or family member. They use it as a discount when they register for their first Art of Living course.",
        "hero_image": HERO_IMG,
        "cta_label": "Give a gift",
        "secondary_cta_label": "Get started",
        "steps_title": "How gifting works",
        "steps": [
            {"title": "Choose an amount", "body": "Pick an amount in CAD and add a personal message if you like."},
            {"title": "Receive your code", "body": "After payment, we email you a 16-character gift code."},
            {"title": "Pass it on", "body": "Forward the code to a newcomer. They enter it when registering in Harmony and the amount comes off the course fee."},
        ],
        "highlights_title": "Programs your gift can open",
        "highlights": [
            {"title": "Breath and meditation", "body": "Courses built around powerful breathing techniques and guided meditation.", "image": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=900&q=70"},
            {"title": "Meditation programs", "body": "Learn simple, effortless meditation you can practise every day.", "image": "https://images.pexels.com/photos/4723100/pexels-photo-4723100.jpeg?auto=compress&cs=tinysrgb&w=900"},
            {"title": "Any AOL program", "body": "The code can be used for any Art of Living program listed on artofliving.org.", "image": "https://images.unsplash.com/photo-1522075782449-e45a34f1ddfb?w=900&q=70"},
        ],
        "sections": [
            {"title": "Why a gift?", "body": "Many people hear about Art of Living from a friend. A gift lowers the cost of a first course, so the people you care about can try it."},
        ],
        "faq_title": "Frequently asked questions",
        "faq": [
            {"q": "Who can use the gift code?", "a": "Anyone who has the code. Share it only with the person you are gifting it to."},
            {"q": "Can the code be used more than once?", "a": "Yes. Each use reduces the balance until the full amount is used."},
            {"q": "Does the code expire?", "a": "No. In this version, codes do not expire."},
            {"q": "Where is the code entered?", "a": "During Art of Living course registration in Harmony on artofliving.org."},
        ],
        "footer_text": "giftaol.ca is a word-of-mouth gift program for Art of Living.",
        "contact_email": "contact@giftaol.ca",
    },
    "fr": {
        "hero_badge": "L'Art de vivre Canada",
        "hero_title": "Offrez à vos proches le cadeau de la respiration",
        "hero_subtitle": "Faites passer le bien. Choisissez un montant, recevez un code-cadeau par courriel et remettez-le à un ami ou à un membre de votre famille. Il l'utilisera comme rabais lors de son inscription à un premier cours de l'Art de vivre.",
        "hero_image": HERO_IMG,
        "cta_label": "Offrir un cadeau",
        "secondary_cta_label": "Commencer",
        "steps_title": "Comment fonctionne le cadeau",
        "steps": [
            {"title": "Choisissez un montant", "body": "Choisissez un montant en dollars canadiens et ajoutez un message personnel si vous le souhaitez."},
            {"title": "Recevez votre code", "body": "Après le paiement, nous vous envoyons par courriel un code-cadeau de 16 caractères."},
            {"title": "Transmettez-le", "body": "Transférez le code à une nouvelle personne. Elle le saisit lors de son inscription dans Harmony et le montant est déduit des frais du cours."},
        ],
        "highlights_title": "Les programmes que votre cadeau peut ouvrir",
        "highlights": [
            {"title": "Respiration et méditation", "body": "Des cours fondés sur des techniques de respiration puissantes et la méditation guidée.", "image": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=900&q=70"},
            {"title": "Programmes de méditation", "body": "Apprenez une méditation simple et sans effort à pratiquer chaque jour.", "image": "https://images.pexels.com/photos/4723100/pexels-photo-4723100.jpeg?auto=compress&cs=tinysrgb&w=900"},
            {"title": "Tout programme de l'Art de vivre", "body": "Le code peut être utilisé pour tout programme de l'Art de vivre offert sur artofliving.org.", "image": "https://images.unsplash.com/photo-1522075782449-e45a34f1ddfb?w=900&q=70"},
        ],
        "sections": [
            {"title": "Pourquoi un cadeau?", "body": "Beaucoup de gens découvrent l'Art de vivre grâce à un ami. Un cadeau réduit le coût d'un premier cours pour que vos proches puissent l'essayer."},
        ],
        "faq_title": "Questions fréquentes",
        "faq": [
            {"q": "Qui peut utiliser le code-cadeau?", "a": "Toute personne qui possède le code. Ne le partagez qu'avec la personne à qui vous l'offrez."},
            {"q": "Le code peut-il être utilisé plus d'une fois?", "a": "Oui. Chaque utilisation réduit le solde jusqu'à ce que le montant total soit utilisé."},
            {"q": "Le code expire-t-il?", "a": "Non. Dans cette version, les codes n'expirent pas."},
            {"q": "Où saisir le code?", "a": "Lors de l'inscription à un cours de l'Art de vivre dans Harmony sur artofliving.org."},
        ],
        "footer_text": "giftaol.ca est un programme de cadeaux de bouche à oreille pour l'Art de vivre.",
        "contact_email": "contact@giftaol.ca",
    },
}
