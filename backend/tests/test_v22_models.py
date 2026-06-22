from app.database import Base
from app.models import ExtractionDraft, ImportJob


def test_import_job_and_extraction_draft_tables_are_registered():
    import_jobs = Base.metadata.tables["import_jobs"]
    extraction_drafts = Base.metadata.tables["extraction_drafts"]

    assert ImportJob.__tablename__ == "import_jobs"
    assert ExtractionDraft.__tablename__ == "extraction_drafts"
    assert import_jobs.c.user_id.foreign_keys
    assert import_jobs.c.source_type.type.length == 20
    assert import_jobs.c.status.server_default.arg == "pending"
    assert extraction_drafts.c.import_job_id.foreign_keys
    assert extraction_drafts.c.note_id.foreign_keys
    assert extraction_drafts.c.is_selected.server_default.arg == "true"
