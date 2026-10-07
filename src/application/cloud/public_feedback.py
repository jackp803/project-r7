"""Strict version dispatch without reserving a previously valid strategy ID."""
from application.cloud.feedback import FeedbackError,validate_feedback_publication
from application.cloud.manifest import load_json

def validate_public_feedback_publication(logical_path,payloads):
    if set(payloads)!={'feedback.json','report.html'}:raise FeedbackError('PUBLIC_FEEDBACK_BUNDLE_INVALID')
    document=load_json(payloads['feedback.json'],256*1024)
    if isinstance(document,dict) and document.get('schema_version')=='r7-paper-feedback-v0.2':
        from application.cloud.paper_feedback import validate_paper_feedback_publication
        validate_paper_feedback_publication(logical_path,payloads)
    else:
        validate_feedback_publication(logical_path,payloads)
