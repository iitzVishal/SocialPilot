import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_email_tasks():
    with patch("app.tasks.email.send_invitation_email_task.delay") as mock_delay:
        yield mock_delay
