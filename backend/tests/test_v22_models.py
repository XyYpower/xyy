from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base
from app.models import ExtractionDraft, ImportJob, LearningPath


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


def test_learning_path_table_is_registered_with_jsonb_modules():
    learning_paths = Base.metadata.tables["learning_paths"]

    assert LearningPath.__tablename__ == "learning_paths"
    assert learning_paths.c.user_id.foreign_keys
    assert learning_paths.c.name.type.length == 100
    assert isinstance(learning_paths.c.modules.type, JSONB)
