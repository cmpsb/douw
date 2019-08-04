import sys
import os
from douw import douw


def test_help():
    sys.argv = ['douw', 'help']
    douw.main()


def test_help_for_action():
    sys.argv = ['douw', 'help', 'add']
    douw.main()


def test_add_new(tmpdir):
    site_name = 'example.com'

    sys.argv = [
        'douw',
        '--basedir', str(tmpdir),
        '-y',
        'add',
        '--name', site_name,
        '--remote', 'https://github.com/Microsoft/project-html-website',
        '--env', 'P'
    ]
    douw.main()

    assert os.path.isdir(os.path.join(tmpdir, site_name))
    assert os.path.isfile(os.path.join(tmpdir, site_name, 'site.db'))


def test_add_and_deploy(tmpdir):
    site_name = 'example.com'
    test_add_new(tmpdir)

    sys.argv = [
        'douw',
        '--basedir', str(tmpdir),
        '-y',
        'deploy',
        site_name
    ]
    douw.main()

    assert os.path.islink(os.path.join(tmpdir, site_name, 'current'))
    assert os.path.isfile(os.path.join(tmpdir, site_name, 'current', 'index.html'))
