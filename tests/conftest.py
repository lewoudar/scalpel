import pytest


@pytest.fixture(scope='session')
def robots_content():
    return """
    User-agent: Googlebot
    Disallow: /videos/
    Disallow: /photos/

    User-agent: *
    Disallow: /admin/
    Allow: /admin/admin-ajax.php
    """
