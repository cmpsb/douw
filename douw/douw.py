#!/usr/bin/env python3

import argparse
import time
import datetime
import os
import subprocess
import fnmatch
import shutil

import sqlite3

from douw.site import Site

currentTime = str(time.time())

assume_yes = False


def main():
    parser = argparse.ArgumentParser(
        description='Manage website deployments'
    )

    parser.add_argument('--basedir', metavar='PATH', default='/srv/www/sites',
                        help='the directories the sites are stored in')

    parser.add_argument('--force-useless', action='store_true', help='force operations even if they are useless')
    parser.add_argument('--force-dangerous', action='store_true', help='force operations even if they are dangerous')

    parser.add_argument('--assume-defaults', '-y', action='store_true',
                        help='assume defaults instead of prompting or abort if no sane default can be guessed')

    subparsers = parser.add_subparsers(title='action', dest='action', metavar='ACTION')

    listParser = subparsers.add_parser('list', help='list all known sites')
    listParser.set_defaults(action=list)

    listParser.add_argument('--site', metavar='*', default='*', help='a glob-style pattern to filter site names')
    listParser.add_argument('--remote', metavar='*', default='*', help='a glob-style pattern to filter remote URLs')

    depsParser = subparsers.add_parser('deployments', help='list all deployments')
    depsParser.set_defaults(action=deps)

    depsParser.add_argument('site', metavar='SITE', help='the site to get deployments for')
    depsParser.add_argument('--deleted', action='store_true', help='Also show deleted deployments')

    addParser = subparsers.add_parser('add', help='add a site',
                                      description='Missing properties are prompted from standard input.')
    addParser.set_defaults(action=add)

    addParser.add_argument('--name', metavar='NAME', help='the name of the site')
    addParser.add_argument('--remote', metavar='URL', help='the repository to pull changes from')
    addParser.add_argument('--branch', metavar='TREE-ISH', help='the branch (or tag or commit) to clone by default')
    addParser.add_argument('--env', metavar='ENV', help='the DTAP environment to deploy as')

    deployParser = subparsers.add_parser('deploy', help='deploy one or more sites')
    deployParser.set_defaults(action=deploy)

    deployParser.add_argument('site', metavar='SITE', help='the site to deploy')
    deployParser.add_argument('treeish', metavar='TREE-ISH', nargs='?', help='the branch, tag, or commit to deploy')

    deployParser.add_argument('--revert', action='store_true', help='revert if the revision already exists')

    revertParser = subparsers.add_parser('revert', help='revert to a previous revision')
    revertParser.set_defaults(action=revert)

    revertParser.add_argument('site', metavar='SITE', nargs='?', default=None)
    revertParser.add_argument('rev', metavar='REV', nargs='?', default=None)

    cleanParser = subparsers.add_parser('clean', help='remove old deployments')
    cleanParser.set_defaults(action=clean)

    cleanParser.add_argument('site', metavar='SITE', help='the site to clean')

    helpParser = subparsers.add_parser('help', help='show this help message and exit')
    helpParser.add_argument('haction', metavar='ACTION', help='the action to get help for')
    helpParser.set_defaults(action=lambda a:
        (parser if a.haction is None else subparsers.choices[a.haction]).print_help()
    )

    removeParser = subparsers.add_parser('remove', help='remove a site')
    removeParser.set_defaults(action=remove)
    removeParser.add_argument('site', metavar='SITE')

    args = parser.parse_args()

    global assume_yes
    assume_yes = args.assume_defaults

    if not os.path.isdir(args.basedir):
        raise FileNotFoundError(args.basedir)

    if args.action is None:
        parser.print_help()
        return

    args.action(args)


def init_db(db):
    """
    Initializes the given database for use.

    This creates the base schema and applies migrations if necessary.

    :param db: the database to initialize
    """

    db.executescript("""
CREATE TABLE IF NOT EXISTS site (
    name TEXT PRIMARY KEY NOT NULL,
    remote TEXT NOT NULL,
    env TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deployment (
    id INTEGER PRIMARY KEY NOT NULL,
    path TEXT NOT NULL,
    revision TEXT NOT NULL,
    date INTEGER NOT NULL,
    active INTEGER NOT NULL,
    present INTEGER NOT NULL DEFAULT 1
);
""")

    db.execute('PRAGMA user_version')
    ver = db.fetchone()[0]

    if ver < 1:
        db.execute('ALTER TABLE site ADD COLUMN default_treeish TEXT')

    db.execute('PRAGMA user_version = 1')


def get_site_db(basedir, name):
    """
    Returns the path to the database for the given site.

    :param basedir: the directory all sites are stored in
    :param name:  the name of the site
    :return: the path to the database
    """
    return os.path.join(basedir, name, 'site.db')


def open_site_db(basedir, name, must_exist=True):
    """
    Opens a connection to a site's database.

    The database is checked for existence and R/W rights if the database is assumed to exist.
    If the database is missing or cannot be modified, an error is raised (if must_exist is True) or the database is
    created and initialized (if must_exist is False).

    Upon successfully opening the database migrations are applied transparently.

    :param basedir: the directory all sites are stored in
    :param name: the name of the site
    :param must_exist: iff True, the file is checked for existence before attempting to open the database

    :return: a connection to the site's database
    """
    db_path = get_site_db(basedir, name)

    if must_exist and not os.access(db_path, os.F_OK):
        raise FileNotFoundError('The requested site could not be found at {}'.format(os.path.join(basedir, name)))

    if must_exist and not os.access(db_path, os.W_OK | os.R_OK):
        raise PermissionError('You do not have the permission to access {}'.format(os.path.join(basedir, name)))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()
    init_db(cur)
    cur.close()
    conn.commit()

    return conn


def get_site_info(db):
    db.execute('SELECT site.name, site.remote, site.env, site.default_treeish FROM site;')

    site_info = db.fetchone()

    return Site(site_info['name'], site_info['remote'], site_info['env'], site_info['default_treeish'])


def accessible_sites(basedir):
    """
    A generator yielding all sites accessible by the current user.

    :param basedir: the directory all sites are stored in
    """
    for ent in os.scandir(basedir):
        ent_db = get_site_db(basedir, ent.name)
        if os.access(ent_db, os.R_OK | os.W_OK):
            conn = sqlite3.connect(ent_db)
            conn.row_factory = sqlite3.Row
            db = conn.cursor()
            init_db(db)

            db.execute('SELECT name, remote, env, default_treeish FROM site;')

            yield db.fetchone()

            conn.close()


def list(args):
    sites = [*accessible_sites(args.basedir)]

    # For each column, find the longest string.
    lengths = {'env': 3, 'name': 4, 'remote': 6, 'default_treeish': max(len('(repo default)'), len('default branch'))}
    for site in sites:
        if not (fnmatch.fnmatch(site['name'], args.site)
                 and fnmatch.fnmatch(site['remote'], args.remote)):
            continue

        for column in site.keys():
            lengths[column] = max(lengths[column], len(site[column] or ''))

    print_site_listing(lengths, {'env': 'env', 'name': 'site', 'remote': 'remote', 'default_treeish': 'default branch'})

    for site in sites:
        if not (fnmatch.fnmatch(site['name'], args.site)
                 and fnmatch.fnmatch(site['remote'], args.remote)):
            continue

        print_site_listing(lengths, site)


def print_site_listing(lengths, site):
    print("{:<{env_width}} | {:<{name_width}} | {:<{remote_width}} | {:<{default_treeish_width}}".format(
        site['env'],
        site['name'],
        site['remote'],
        site['default_treeish'] or '\033[37m(repo default)\033[0m',
        env_width=lengths['env'],
        name_width=lengths['name'],
        remote_width=lengths['remote'],
        default_treeish_width=lengths['default_treeish']
    ))


def deps(args):
    conn = open_site_db(args.basedir, args.site)
    db = conn.cursor()

    db.execute("""
        SELECT deployment.path, deployment.date, deployment.active, deployment.revision, deployment.present
          FROM deployment 
          ORDER BY date;
    """)

    dbDeployments = db.fetchall()
    deployments = []

    # Translate each timestamp into a date and calculate the required column widths.
    lengths = {'active': 1, 'path': 4, 'date': 4, 'revision': 6, 'present': 0}
    for dbDep in dbDeployments:
        deployment = {}

        for column in dbDep.keys():
            deployment[column] = dbDep[column]

        deployment['date'] = datetime.datetime.utcfromtimestamp(int(dbDep['date'])).isoformat()

        for column in dbDep.keys():
            if column == 'active':
                continue

            lengths[column] = max(lengths[column], len(str(deployment[column])))

        deployments.append(deployment)

    print_dep_listing(lengths, {
        'active': True, 'path': 'path', 'date': 'date', 'revision': 'commit', 'present': True
    })

    for deployment in deployments:
        if deployment['present'] or args.deleted:
            print_dep_listing(lengths, deployment)

    conn.close()


def print_dep_listing(lengths, dep):
    print("{} | {:<{path_width}} | {:<{date_width}} | {:<{rev_width}}".format(
        ('*' if dep['active'] else 'D' if not dep['present'] else ' '),
        dep['path'],
        dep['date'],
        dep['revision'],
        path_width=lengths['path'],
        date_width=lengths['date'],
        rev_width=lengths['revision']
    ))


def add(args):
    site_name = args.name or prompt_nonempty('Site name')
    site_dir = os.path.join(args.basedir, site_name)

    if os.access(get_site_db(args.basedir, site_name), os.F_OK):
        print('\033[31;1mA site named {} already exists at {}\033[0m'.format(site_name, site_dir))
        if args.force_dangerous:
            setattr(args, 'site', site_name)
            remove(args)
            if os.access(get_site_db(args.basedir, site_name), os.F_OK):
                return
        else:
            return

    remote = args.remote or prompt_default('Remote', 'git.wukl.net:wukl/' + site_name)
    branch = args.branch or prompt_default('Branch (leave empty to use repository default)', None)
    env = args.env or prompt_default('DTAP Environment', 'P')

    os.makedirs(site_dir, mode=0o0775, exist_ok=True)

    conn = open_site_db(args.basedir, site_name, must_exist=False)
    db = conn.cursor()

    db.execute('INSERT INTO site (name, remote, env, default_treeish) VALUES (?, ?, ?, ?)',
               (site_name, remote, env, branch))

    conn.commit()
    conn.close()


def prompt_default(prompt, default):
    global assume_yes
    if assume_yes:
        return default

    value = input(prompt + ' [' + (default if default is not None else '') + ']: ')
    if not value:
        return default
    else:
        return value


def prompt_nonempty(prompt):
    global assume_yes
    if assume_yes:
        raise Exception('Missing required value "{}"'.format(prompt))

    value = input(prompt + ': ')
    if value:
        return value

    return prompt_nonempty(prompt)


def prompt_bool(prompt):
    global assume_yes
    if assume_yes:
        return True

    value = input(prompt + ' [N/y]: ')
    if not value:
        return False

    vlower = value.lower()

    return vlower == 'y' or vlower == 'yes'


def deploy(args):
    """
    Deploys a site.

    This function covers the entire deployment procedure:

    * clone the repository
    * check for matching deployments
    * register deployment (if new or previously deleted)
    * activate deployment

    :param args: the command line arguments
    :return: nothing
    """
    site = args.site

    conn = open_site_db(args.basedir, site)
    db = conn.cursor()

    site_info = get_site_info(db)
    site_dir = os.path.join(args.basedir, site)

    deploy_dir = os.path.join(site_dir, 'deployments', currentTime)

    print("\033[32;1mDeploying " + site + ".\033[0m")

    os.makedirs(deploy_dir, mode=0o755, exist_ok=True)

    subprocess.run(['git', 'clone', site_info.remote, deploy_dir + '/'], check=True)
    branch = args.treeish or site_info.default_treeish
    if branch is not None:
        subprocess.run(['git', '-C', deploy_dir, 'checkout', branch], check=True)
    result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                            stdout=subprocess.PIPE, check=True, cwd=deploy_dir)
    rev_id = result.stdout.decode('utf8').partition("\n")[0]

    db.execute('SELECT 1 FROM deployment WHERE revision = ? AND present = 1;', (rev_id,))
    existing_deployment = db.fetchone()
    if existing_deployment is not None and args.force_useless is False and args.force_dangerous is False:
        print('\033[31;1mThis revision ({}) was already deployed\033[0m'.format(rev_id))
        shutil.rmtree(deploy_dir)
        conn.close()

        if args.revert:
            print('\033[33;1mReverting to previous deployment\033[0m')
            activate(args, site, rev_id)

        return

    print("\033[32;1mFound revision " + rev_id + ".\033[0m")

    db.execute('INSERT INTO deployment (path, revision, date, active) VALUES (?, ?, ?, 0);',
               (deploy_dir, rev_id, int(time.time())))

    conn.commit()
    conn.close()

    activate(args, site, rev_id)

    clean(args)


def activate(args, site, revision):
    """
    Activates an existing deployment.

    If the deployment does not exist (either was never deployed or previously deleted), an exception is raised.
    Otherwise the symlink is updated and

    :param args: command line arguments containing global settings
    :param site: the site to activate the deployment for
    :param revision: the revision ID indicating the deployment to activate
    :return:
    """
    conn = open_site_db(args.basedir, site)
    db = conn.cursor()

    db.execute('UPDATE deployment SET active = 0;')

    site_dir = os.path.join(args.basedir, site)
    link_name = os.path.join(site_dir, 'current')
    new_link_name = link_name + '.new'

    # Find the directory the deployment is in
    db.execute('SELECT path FROM deployment WHERE revision = ? AND present = 1 ORDER BY date DESC LIMIT 1', (revision,))
    path_info = db.fetchone()
    if path_info is None:
        raise Exception('No available deployment for revision {} for site {}'.format(revision, site))

    path = path_info['path']
    if not os.path.exists(path):
        db.execute('UPDATE deployment SET present = 0 WHERE path = ?', (path,))
        conn.commit()
        conn.close()
        raise Exception('The selected revision ({}) has been removed'.format(revision))

    # Determine the location for the shared data
    shared_dir = os.path.join(site_dir, 'shared')
    shared_link_name = os.path.join(path, 'shared')
    new_shared_link_name = shared_link_name + '.new'

    # Switch the symlink to shared data, if the folder is present
    if os.path.exists(shared_dir):
        os.symlink(shared_dir, new_shared_link_name, target_is_directory=True)
        os.replace(new_shared_link_name, shared_link_name)

    # Switch the symlink
    os.symlink(path, new_link_name, target_is_directory=True)
    os.replace(new_link_name, link_name)

    # Register the new deployment
    db.execute("""
        UPDATE deployment 
          SET active = 1 
          WHERE rowid = (SELECT rowid FROM deployment WHERE revision = ? ORDER BY date DESC LIMIT 1);
    """, (revision,))

    conn.commit()
    conn.close()


def revert(args):
    site = args.site

    conn = open_site_db(args.basedir, site)
    db = conn.cursor()

    rev = args.rev
    if rev is None:
        db.execute('SELECT revision FROM deployment WHERE active <> 1 AND present = 1 ORDER BY date DESC LIMIT 1')

        rev_info = db.fetchone()
        if rev_info is None:
          raise Exception('No available previous deployment to revert to')

        rev = rev_info['rev']

    activate(args, site, rev)

    conn.commit()
    conn.close()


def clean(args):
    site_name = args.site

    conn = open_site_db(args.basedir, site_name)
    db = conn.cursor()

    db.connection.commit()
    db.execute("""
        SELECT deployment.id, deployment.path 
          FROM deployment 
          WHERE deployment.active <> 1 
            AND deployment.present = 1 
          ORDER BY deployment.date DESC
          LIMIT 1000000 OFFSET 4;
    """)

    results = db.fetchall()

    for result in results:
        print('\033[33;1mDeleting', result['path'], '\033[0m')

        try:
          shutil.rmtree(result['path'])
        except:
          pass

        db.execute('UPDATE deployment SET present = 0 WHERE id = ?', (result['id'],))

    conn.commit()
    conn.close()


def remove(args):
    site_name = args.site

    # Check for administrative access
    if not os.access(args.basedir, os.W_OK):
        raise PermissionError(
            'Administrative access (i.e., write access to the base directory) is required for deleting sites'
        )

    # Ensure that the database exists and is accessible
    conn = open_site_db(args.basedir, site_name)
    conn.close()

    site_dir = os.path.join(args.basedir, site_name)

    confirmed = prompt_bool('Are you sure you want to delete site {} at {}?'.format(site_name, site_dir))
    if not confirmed:
        print('\033[31;1mAborted\033[0m')
        return

    shutil.rmtree(site_dir)
