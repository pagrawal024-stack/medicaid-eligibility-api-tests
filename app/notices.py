"""Multilingual notice templates sent after a determination."""

SUPPORTED_LANGUAGES = ("en", "es", "hi", "zh")

SUBJECTS = {
    "APPROVAL_NOTICE": {
        "en": "Your Medicaid application has been approved",
        "es": "Su solicitud de Medicaid ha sido aprobada",
        "hi": "आपका मेडिकेड आवेदन स्वीकृत हो गया है",
        "zh": "您的医疗补助申请已获批准",
    },
    "DENIAL_NOTICE": {
        "en": "Your Medicaid application has been denied",
        "es": "Su solicitud de Medicaid ha sido denegada",
        "hi": "आपका मेडिकेड आवेदन अस्वीकार कर दिया गया है",
        "zh": "您的医疗补助申请未获批准",
    },
}


def build_notices(applicant: dict, decision_status: str) -> list[dict]:
    """One notice per contact channel the applicant gave us."""
    template = "APPROVAL_NOTICE" if decision_status == "APPROVED" else "DENIAL_NOTICE"
    language = applicant["preferred_language"]
    subject = SUBJECTS[template][language]

    notices = []
    if applicant.get("email"):
        notices.append({"channel": "EMAIL", "recipient": applicant["email"]})
    if applicant.get("phone"):
        notices.append({"channel": "SMS", "recipient": applicant["phone"]})
    for n in notices:
        n.update(template_code=template, language=language, subject=subject)
    return notices
